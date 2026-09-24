# EC firmware — disassembly / recompilation scaffold

Target: `firmware/GMxMGxx_11.800`, an ITE-based embedded controller image
(`ITE EC-V14.6` string at file offset `0x50`), 256 KiB, 8051 core, dumped
by the `ecflash.nsh` tool inside `vendor/bios-1.09/BIOS_1.09.zip`
(`IFUX64.efi GMxMGxx_11.800 0 1` — ITE Firmware Update).

## Layout

Keil BL51-style banked 8051: a 32 KiB **common area** (`0x0000-0x7FFF`,
always mapped) plus a bank-switched window at `0x8000-0xFFFF`, selected via
port bits `P1.0-P1.2`. Bank-switch stubs live in the common area at
`0x1100/0x1114/0x1128/0x113C` (`find_banks.py`). Only banks 0 and 1 have any
callers in this build:

| bank | stub | file offset for 0x8000 window | callers | confidence |
|---|---|---|---|---|
| 0 | `0x1100` | `0x08000` | 350 | 51% (heuristic opcode-start scoring) |
| 1 | `0x1114` | `0x10000` | 53 | 92% |
| 2 | `0x1128` | — | 0 | unused on this SKU/build |
| 3 | `0x113C` | — | 0 | unused on this SKU/build |

File regions `0x18000-0x1FFFF`, `0x30000-0x3FFFF` are 100% `0xFF` — erased
flash / unused capacity, not code.

`0x20000-0x2FFFF` is **not** part of the EC firmware above. It is a second,
self-contained 8051 image identifying itself as `ITE8850-PD` (marker at file
`0x20040`, USB Power-Delivery protocol strings throughout), with its own
reset/interrupt vector table at its own offset 0, its own C startup stub, and
none of the bank-switch stubs. It therefore has its own 64 KiB address space
and its own XDATA map — a `MOV DPTR,#0x07E2` in there is not a reference to
the EC register at `0x07E2`. `annotations/lightbar-bat-flow.md` §2 has the
evidence, and §6 the registers it changes the reading of. Extract it with
`dd if=firmware/GMxMGxx_11.800 of=pd.bin bs=64k skip=2 count=1`; it loads flat
into `r2 -a 8051` with no stitching needed.

## Tools

- **`tools/scan_refs.py`** — counts direct `MOV DPTR,#addr` references to a
  given XDATA address. Fast way to check "does this EC firmware build
  implement register X". Every count comes out split `ec=`/`pd=` across the
  two programs in this dump, with the two-programs caveat in its own preamble,
  so a bare file-wide total can't be quoted out of it by a reader who skipped
  this README. Validated 20/20 against live-hardware ground truth (see
  `docs/findings.md`), but has a known blind spot for pointer/indirect
  addressing — treat "0 refs" as "not found by this method", not "absent".
- **`tools/trace_xdata_refs.py`** — same `MOV DPTR,#addr` sites and the same
  image split as `scan_refs.py`, but down to the individual site: which region
  each one is in (common area, a CODE bank, or the separate PD image above),
  its runtime address, and the access direction decoded from the opcodes that
  follow. Reach for it when *which sites* matters rather than how many. The
  mnemonics are a linear best-effort walk, not a disassembler —
  `--r2-commands` prints the seek lines to confirm anything load-bearing, and
  the indirect-addressing blind spot above applies here unchanged.
- **`tools/check_register_counts.py`** — recomputes every `static_refs`,
  `static_refs_main_ec` and `static_refs_pd_image` in
  `annotations/registers.yaml` from the image and exits non-zero on a mismatch
  or on an entry missing the split. Run by `.github/scripts/agent-gates.sh`;
  the numbers it guards are tabulated in `annotations/static-refs-audit.md`.
- **`tools/check_cluster_citations.py`** — holds every `main-ec-NNN` in the
  committed prose to the membership it names in
  `annotations/xdata-clusters.csv`, and holds every hand-typed count beside one
  to the figures the same CSV gives. A cluster id in a sentence is a pointer,
  and pointers go stale: the ids are numbered by size, then references, then
  lowest address (`xdata_register_map.py:1027`), which holds them steady across
  a re-run and promises nothing once the classifier itself changes. Issue #253
  is four sentences whose pointer had drifted exactly that way. It walks the
  markdown under `ec/`, `docs/` and `evidence/`, and where a sentence names
  both a cluster and an XDATA address, the address has to be a member of the
  cluster that sentence pairs it with, or of one of the clusters it names where
  it pairs it with none — reporting file, line, id and address, and
  exiting non-zero. A **census row** is the other kind of claim: a markdown
  table row whose first cell is one cluster id, which is what all twelve rows
  of `annotations/xdata-register-map.md` §5 are. Four of them disagreed with
  the CSV beside them before issue #272 and nothing held them there, so a
  census row's size, reference count, address range and named count are now
  held to the same census. The two are separate gates over one walk and
  neither inherits the other: a §5 row carries a range and a title but never
  the word "member", so the membership rule skips every one of them and this
  is the only rule that reads it. Committed files only: no image, no Ghidra,
  no network. The limits it earns the right to state: a sentence that
  *denies* membership is skipped rather than checked, one that names a cluster
  without claiming membership is skipped (which is what keeps §5's *ranges*
  out of the membership results; its *numbers* are the count rule's), and a
  pairing the wording cannot be read for — the same split written with
  both ids first and the addresses in a trailing list — is back to being
  satisfied by either, so a two-cluster unit catches a wrong id there and a
  wrong pairing only where its own wording says which is which. The count
  rule reads a cell only when it is a bare number, thousands commas allowed,
  or one of `none`/an em dash/a hyphen, which is
  what leaves a listing like `` `0x0403` ``, a span like `` `0x030E`-`0x1809` ``
  and a free-text cell alone — as it also leaves alone any row naming two
  cluster ids, or any row whose id is not in its first cell. Passing means the
  checked sentences and the checked counts agree with the CSVs beside them; it
  says nothing about whether the prose is right about the firmware.
  `tools/test_check_cluster_citations.py` pins each of those skips and asserts
  the committed tree currently agrees. Not run by
  `.github/scripts/agent-gates.sh` — that file is not one this repo edits
  casually (`../../CLAUDE.md`), so the tool stands as something a human can
  wire up.
- **`tools/check_capture_claims.py`** — the capture-file sibling of that one:
  it holds the prose's claims about `evidence/ec-watch/*.csv` to the capture
  they name. `check_register_counts.py` recomputes `registers.yaml`'s numeric
  keys from the image and never opens a `note:`, so a note can attribute a
  movement to a committed capture and state a row count for it with nothing to
  disagree — which has been wrong twice in that file's history (issue #265, and
  the `0x07D4` clause issue #270 had to retract in place), both times caught by
  a re-reading rather than a check. An address a sentence attributes to a
  capture has to have a row in it, and a stated count has to equal the real one;
  a capture is a fixed committed artifact, so a disagreement is decidable rather
  than a race. It imports `check_cluster_citations.units` rather than writing a
  second sentence splitter, so a fix to the splitting logic (issue #273) lands
  once and both checkers get it. Committed files only: no image, no Ghidra, no
  network — `.csv` captures only, as the four `.txt` files in that directory are
  `ecrw.py dump` output with no row-per-change shape. The limits it earns the
  right to state are in its own docstring, in the sibling's style, and the two
  that matter most: a sentence that *denies* movement is skipped, which is what
  keeps #270's correction green and is exactly why a stale denial is not caught;
  and a table row is its own unit, so `annotations/xdata-0400-045f.md` §8's
  `changes` column — six true counts — is not read, because the capture is named
  in the paragraph above the table. The run prints how many claims it checked
  rather than only whether they agreed, because a run that checked nothing and a
  run that found nothing look the same from the exit code alone.
  `tools/test_check_capture_claims.py` pins each skip, reproduces the pre-#270
  `0x07D4` sentence as a negative fixture, and asserts the committed tree agrees.
  Also not run by the gate, for the same reason as its sibling — the arm is
  prepared at `docs/ci/agent-gates-capture-claims.patch` for a human to
  `git apply`, by cost and kind it belongs in the cheap tier, and
  `../../docs/agent-pipeline.md` carries it across a template re-copy.
- **`tools/register_ref_table.py`** — the whole `annotations/registers.yaml`
  table in one pass: per-image count split *and* what each site behind it does
  (`read`/`write`/`movc` CODE pointer/handed to a subroutine/…), as a markdown
  table or, with `--csv`, one row per site. Reconciles class buckets against
  the site count and main + PD against the file-wide total, and exits non-zero
  if either fails. The classification inherits the 8-instruction linear walk's
  limits — `annotations/static-refs-audit.md` §5 is the table it produced and
  the caveats that go with it.
- **`tools/xdata_register_map.py`** — every XDATA address the decompiled
  firmware touches, attributed to the functions that touch it and grouped into
  clusters: the per-address census in
  `annotations/xdata-registers.csv` and the worklist in
  `annotations/xdata-clusters.csv`, both regenerable, with `--check` and
  `--self-test` running on committed text alone (no image, no Ghidra, no
  network). Reach for it when the question is "which addresses exist, which
  routines share them, and is this number a read or a write" — the whole
  `registers.yaml` list is 153 addresses, and this census is 1,172. Two limits
  it earns the right to state: it splits the main EC from the separate
  `ITE8850-PD` program rather than mixing them, and a cluster is a
  co-occurrence in static code, not a purpose —
  `annotations/xdata-register-map.md` §6 is the boundary, and §7 reconciles
  its counts against `register_ref_table.py`'s. Its per-address columns are
  also an upper bound on *distinct* references wherever one routine is exported
  as several overlapping functions; `annotations/xdata-06c2-06db-timers.md`
  §2a measures that at 42× on the one cluster measured so far.
- **`tools/disasm8051.py`** — the opcode tables `trace_xdata_refs.py` decodes
  with, plus a CLI for reading a window of instructions at a file offset
  (`--at`) and for measuring how many nearby anchors a linear walk syncs onto
  it from (`--converge`). Not a disassembler: linear only, no branch
  following, no code/data separation. `python3 tools/disasm8051.py --self-test`
  re-decodes the two windows `annotations/charge-profile-flow.md` transcribed
  from `r2` by hand and diffs against them, resolves the four
  `bank-call-audit.md` §8 branch sites, and checks the bit-addressed carry
  forms against `BIT_SITES` — 11 sites transcribed from `r2 -a 8051` against the
  image, plus the `0xC1`/`0xC2` pair stated from the manual — run it after
  touching either table.
- **`tools/verify_gap_text.py`** — cross-decodes the 143 instructions
  `verify_reassembly.py` cannot re-encode, so none of the committed listing is
  read by no check. It recomputes the set from `to_sdas()` rather than carrying
  a list, decodes each instruction from the firmware image with
  `disasm8051.py`, and records both texts, both canonical forms, the reason it
  was excluded and the verdict in `ghidra/gap-text-check.csv` — 143 rows, all
  agreeing. `--check` and `--report` need no assembler; `--report` writes the
  CSV and nothing else does. `ghidra/README.md` has the method, what it folds
  and what it deliberately does not, and its blind spots.
- **`tools/find_banks.py`** — locates the bank-switch stubs and scores which
  file offset each bank maps to. Re-run this against any other firmware dump
  before trusting the offsets in the table above.
- **`tools/audit_call_targets.py`** — every direct `lcall`/`ljmp` in the common
  area and both banks, bucketed by where its target can be: common area, the
  caller's own bank (the assumption `trace_xdata_refs.offset_for_runtime()`
  rests on), or unresolvable. Prints a byte-scan upper bound *and* an
  anchored-decode count for each, because neither framing settles on its own.
  Also counts the 2-byte `ajmp`/`acall` family separately (`--paged-csv`),
  which is not a banking question at all: a paged target cannot leave the
  caller's own 2 KiB page. `--self-test` re-checks the four BL51 stub sites,
  the `offset_for_runtime`/`runtime_addr` round-trip and the page arithmetic
  against two hand decodes; `annotations/bank-call-audit.md` is the transcript
  and the verdict.
- **`tools/decode_index_table.py`** — decodes the inline `switch` tables the
  main EC image's one table-reading subroutine consumes, starting with the
  `bank0` `0x8038` one that `annotations/bank-call-audit.md` §8 met as a
  misframed rel8 escape and §9 corrects. Finds them by that reader's prologue
  and the `lcall` sites naming it, not by a DPTR scan — nothing in this image
  loads such a table's address as an immediate. `--all-tables` is the
  image-wide census, `--csv` regenerates
  `annotations/bank0-8038-dispatch-table.csv`, `--all-csv` and `--spans-csv`
  regenerate `annotations/index-table-entries.csv` and
  `annotations/index-table-spans.csv`, and `--self-test` re-checks the
  reader's bytes, the table's extent and stride, the whole 15-site census and
  the census rows each span accounts for against the committed image.
- **`tools/pd_index_geometry.py`** — the `ITE8850-PD` image's DPTR index
  helpers, the bases they are called against, and who calls the routines that
  do it. `--helpers` decodes each helper to its `ret` into a symbolic "what
  this adds to DPTR"; `--bases` reports every PD `MOV DPTR,#imm16` in the
  `0x0400`-`0x04A8` run with the chain of helper terms it runs and where that
  chain stopped; `--callers` bounds a site's caller set. It is not a
  disassembler and not a call graph: the term model is two byte templates, and
  anything outside it is reported `unmodelled` rather than fitted, while the
  caller scan over-counts on phantoms and under-counts on indirection at the
  same time. `--self-test` re-checks the helper bodies against the `r2`
  listings in `annotations/pd-xdata-overlap.md` §3, the four `0x04A6` site
  offsets against `trace_xdata_refs.py`, the per-base site counts against §1
  and §5.2 of the same file, and both CSVs below against a live regeneration.
- **`tools/make_bank_image.py`** — stitches common area + one bank into a
  flat 64 KiB image loadable by `r2 -a 8051` (or any other 8051 disassembler
  expecting linear addressing).
- **`tools/grade_0751_isolation.py`** — applies §4 of
  `../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` to a `0x0751`
  capture mechanically, so the sweep half of that procedure is read the same way
  twice; §4.4's PWM comparison is left as a number for a human. Its offline
  suite is `tools/test_grade_0751_isolation.py`, and `bash tools/run-tests.sh`
  from the repo root runs it with every other `test_*.py` in the repository
  (`../tools/README.md`). It runs against the committed `tools/testdata/`
  captures and is not evidence about the machine.

```console
$ python3 tools/make_bank_image.py firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -c 's 0xb2e2; pd 10' /tmp/bank0.bin
```

## Annotations

- **`annotations/registers.yaml`** — every EC register the `uniwill-laptop`
  driver or the Windows service touches, cross-referenced against static-scan
  results and live-hardware behaviour. This is the primary research output;
  start here. It is 144 addresses, and `annotations/xdata-register-map.md`
  covers 1,172 — the two corpora are nearly disjoint, and which of the two a
  question is about decides where the answer lives.
- **`annotations/static-refs-audit.md`** — the per-image reference count for
  every address in `registers.yaml`, the command that produced it, and the
  subset of it that backs the static-scan validation in `docs/findings.md`
  §4d. Read it before arguing from any reference count in this repo.
- **`annotations/charge-profile-flow.md`** — full traced control flow for the
  three charge profiles, including the manual-control gate that made the
  systemd per-boot reapply necessary.
- **`annotations/ec-0x07d0-sites.md`** — all 254 `0x07D0` reference sites
  enumerated and classified, with `annotations/ec-0x07d0-sites.csv` as the
  machine-readable table behind it. Answers what the sites *are*; deliberately
  does not answer what the EC does with the address of the same number.
- **`annotations/ec-07c4-07d5-sites.md`** — the 15 main-EC reference sites of
  `0x07C4`, `0x07D3`, `0x07D4` and `0x07D5`, against 102 in the PD image, with
  `annotations/ec-07c4-07d5-sites.csv` as the machine-readable table behind it.
  Answers what `CPUA` and `DBAP` are set from (`0x09EA` and `0x09EB`, in the
  routine entered at `0x83FF`) and which four GFID values the EC writes to
  `0x07D3`; deliberately stops short of naming the routine that wrote `0x07C4`
  on 2026-09-23, because its only caller's framing is unresolved, and of the
  102 PD-image sites, which are another program's variables.
- **`annotations/xdata-0400-045f.md`** — the `0x0400-0x045F` page the fan
  isolation run sweeps, site by site: which of its 96 bytes the EC firmware
  references at all, in which image, reading or writing or handing DPTR to one
  of six pair helpers, and from which routine. `xdata-0400-045f-sites.csv` is
  the per-site table behind it and reproduces every count in
  `annotations/registers.yaml` for the page. Answers what the EC side of the
  battery/temperature block does, and deliberately stops at naming: the 32
  bytes with no cited name are `XDATA_04XX` in the symbol table, and §9 of
  that file says where each name that *is* used came from.
- **`annotations/xdata-086x-dispatch.md`** — the `0x0860`-`0x086E` run: the
  two instructions that set `0x0860` and the early-outs that gate it, the
  twelve-entry case table at `0xD14B` and the correction it forces on the
  `0xD091` row, the three-block level computation at `0x9D9B`, and why the
  `0x1C39`/`0x1C3A` copy is neither a mirror nor a second buffer.
  `xdata-086x-dispatch-sites.csv` is the per-site table behind it. Every
  direction number there names the method that produced it, because the two
  methods have different denominators — the opcode sweep behind §8 and the
  C-level census behind §3 — and §3 is the one that says which is which for
  `0x0860`. The units of the block are not fixed, so nothing is named.
- **`annotations/lightbar-bat-flow.md`** — the `0x07E2`-`0x07E5` site map, the
  evidence that those sites belong to the PD image rather than the EC, and the
  live probe still needed to say what (if anything) the EC does with those
  bytes.
- **`annotations/xdata-06c2-06db-timers.md`** — the `main-ec-003` cluster read
  as the block the issue asked about: 37 of its 43 addresses are countdowns one
  393-byte routine walks over, and the other 6 are what four of them do at zero.
  It also measures why the cluster's headline census numbers are inflated 42×,
  what gates the block (`0x0440`, and two predicate calls of which one target
  has no exported function), and what the reload search did and did not find.
  The read-only procedure for settling `0x06D6`'s period on real hardware is
  §7, written down and not run.
- **`annotations/bank-call-audit.md`** — the call-target census behind every
  EC-side handoff this repo resolves: how many direct calls stay in the common
  area, how many assume the caller's own bank, how many are unresolvable, and
  why the same-bank assumption cannot be verified from these bytes however the
  counts come out — plus §7, the paged `ajmp`/`acall` family, and §8, the
  PC-relative branches, neither of which the assumption ever has to carry.
  `annotations/bank-call-targets.csv`,
  `annotations/bank-paged-call-targets.csv` and
  `annotations/bank-relative-branch-targets.csv` are the per-site tables.
- **`annotations/bank0-8038-dispatch-table.csv`** — the per-entry table behind
  `annotations/bank-call-audit.md` §9: the eight entries of the `bank0`
  `0x8038` inline `switch` table, each with the XDATA addresses its handler's
  window names. Produced by `tools/decode_index_table.py --csv`, and written
  without a comment header so a later region map can read it with
  `csv.DictReader` and fold it in or supersede it.
- **`annotations/index-table-entries.csv`** — the same per-entry decode for all
  15 tables of that family, with a leading `site` column naming the `lcall`
  each table follows. Produced by `tools/decode_index_table.py --all-csv`;
  `annotations/bank-call-audit.md` §10 is the reading. It carries the `0x8038`
  table's eight entries too, so a consumer of the span list below needs no
  special case for it — `annotations/bank0-8038-dispatch-table.csv` stays the
  file §9 cites.
- **`annotations/pd-index-geometry.md`** — the PD image's index-helper family
  decoded, the `0x0400`-`0x04A8` base run's stride and field layout, and the
  callers of the four `0x04A6` sites, plus §7's whole-image widening: the
  `0x5E`/`0x77` arrays `annotations/ec-0x07d0-sites.md` §4 names, decoded, and
  the finding that none of them carries the `0x200 × Rn` page term — so `0x260`
  is that run's shape and not the image's. Answers the address *arithmetic*
  `annotations/ec-0x07d0-sites.md` §4 and `annotations/pd-xdata-overlap.md`
  §3-§6 stop at, and deliberately stops where they do: no record count, no name
  for the contents, no claim that the caller list is complete.
  `annotations/pd-index-helpers.csv` and `annotations/pd-index-callers.csv` are
  the per-helper and per-caller tables, produced by
  `tools/pd_index_geometry.py --helpers-csv` / `--callers-csv`.
- **`annotations/pd-base-strides.csv`** — the whole-image stride census behind
  that §7: one row per stride constant the term decode resolves, with the site
  count, how many of those sites also apply the `0x200 ×` page term, and every
  effective base that produced it. The `unresolved` row is the sites that
  resolve no stride, kept in the file rather than filtered out, because "not
  resolved by this method" is a result too. Produced by
  `tools/pd_index_geometry.py --strides-csv` and checked by its `--self-test`.
- **`tools/build_ec_decompile.py`** — builds the Ghidra project and the
  decompiled C. Imports the three programs, seeds them, applies
  `annotations/ghidra-functions.csv` and the generated XDATA names, and
  exports one C file per function to `decompiled/`. Two modes: the default
  re-exports from the committed project without touching it, and
  `--mode rebuild-project` rewrites the project. `--check` and `--self-test`
  run with no Ghidra and no network and are what CI calls — 0.19 s and 0.13 s.
  `--self-test --cross-decoder` adds the advisory comparison against
  `disasm8051.py`; it is 0.13 s, it prints rather than fails, and the deep gate
  tier is what passes the flag. `--self-test --oracle` additionally rebuilds
  and checks the output against the hand reading in
  `annotations/charge-target-derating.md`. Method, measured coverage and
  limits: `ghidra/README.md`.
- **`tools/gen_xdata_symbols.py`** — turns `annotations/registers.yaml` into
  the XDATA symbol table Ghidra applies, so the decompile reads `PROJECT_ID`
  rather than `DAT_EXTMEM_0740`. It reads `registers.yaml` and never writes
  it. Addresses it cannot name are reported, not dropped; the escape hatch is
  `ghidra/xdata-overrides.csv`.
- **`annotations/xdata-registers.csv`** — one row per XDATA address the
  decompiled firmware touches: which program touches it, whether the export
  spelled it as a `DAT_EXTMEM_` token or as its symbol, the five direction
  buckets, how many distinct functions read and write it, its cluster, its
  `span_group`, and every touching function with the name and type
  `ghidra-functions.csv` gives it. Produced by
  `tools/xdata_register_map.py`, which also writes
  `annotations/xdata-clusters.csv` and checks both; `spelled_as` and `name`
  are separate columns because the PD image is written with `DAT_EXTMEM_`
  tokens for addresses the symbol table names for the EC, and reading those
  rows as the PD firmware using the EC's vocabulary is
  `pd-xdata-overlap.md`'s mistake in a new place.
- **`annotations/xdata-clusters.csv`** — one row per cluster: the addresses,
  the functions that touch two or more of them, the routines most of those
  functions call, and the already-named addresses inside. The worklist, in
  `annotations/xdata-register-map.md` §5's order; the clustering method, its
  threshold and the sensitivity sweep behind it are §4 of that file, and the
  gap this census cannot close (two addresses, both inside
  `bank0:0x94D0`) is §7.
- **`annotations/index-table-spans.csv`** — one row per candidate call site:
  the table's span, its case range, and the site's own `frame_onto`/
  `frame_over`. It is the census, not a filtered view of it, so a site whose
  bytes do not decode keeps a `well_formed=no` row rather than disappearing.
  Produced by `tools/decode_index_table.py --spans-csv`.

## Recompilation — status: toolchain proven, not attempted

**What's confirmed:** `sdcc`/`sdas8051`/`sdld` (packaged in nixpkgs) correctly
assemble/link every 8051 opcode observed in this image, including the
Keil-specific bank-switch idiom — see the round-trip test referenced in
`docs/findings.md`. That means a from-scratch reassembly pipeline is
mechanically possible.

**What's not done, and why it's a real project, not a script:** producing a
*complete, correct, symbolized* disassembly of 256 KiB of banked 8051 —
enough to reassemble byte-identical output, let alone modify and reflash it —
needs:

1. Full recursive disassembly of both live banks with a resolved symbol table
   (register names from `annotations/registers.yaml`, function boundaries,
   the multiply/divide runtime helpers the compiler calls into, e.g. `0x707d`
   seen in the charge-profile flow).
2. A verified understanding of every bank-switch call site (only common-area
   callers are covered by `find_banks.py`; in-bank-to-in-bank calls, if any,
   are not yet enumerated).
3. A test harness — this is a live EC that runs the keyboard, battery gauge,
   thermal management and USB-PD negotiation. A bad reflash is a bricked
   laptop; issue #7 in upstream `uniwill-laptop` documents a case where a
   *register write* alone required a 30s power-button EC reset to recover.

Treat this as the honest state: the Ghidra project now exists
(`ghidra/project/`, with 2,710 decompiled functions under `decompiled/`), so
items 1 and 2 above have a real starting point rather than a plan — but a
*correct, complete* reassembly is still a project, not a script, and nothing
here has been reassembled or reflashed. `ghidra/README.md` has the method, the
measured coverage, and the limits.

**Where to start reading it.** `decompiled/<program>/<ADDR>.c` is the
decompilation and `decompiled/<program>/<ADDR>.asm` is the machine code it was
read from, at the same address; `decompiled/index.csv` has one row per function
and `decompiled/listing-index.csv` points at the listings. A function named
rather than called `FUN_CODE_…` carries a plate comment saying what it does and
where the reading came from — those names come from
`annotations/ghidra-functions.csv`, which is the editable surface. And the
committed disassembly re-encodes to the firmware bytes: 45,481 of 45,624
instructions, measured by `tools/verify_reassembly.py` and recorded in
`ghidra/reassembly.csv`. The other 143 use five forms `sdas8051` cannot
express, so no assembler reaches them; they are covered instead by
`tools/verify_gap_text.py`, which cross-decodes each one with
`tools/disasm8051.py` and records the verdict per instruction in
`ghidra/gap-text-check.csv` — all 143 agreeing. That does **not** make the
claim 100%: the re-encode figure stays 45,481 of 45,624, and the two are
different kinds of evidence. Both are claims about the machine code, not about
the C, and `ghidra/README.md` says at length what it is not. See the repo's GitHub issues for the
concrete next steps, several of which are independently useful (e.g. the 254
call sites referencing `0x07D0`, which `trace_xdata_refs.py` places in the PD
image rather than the EC and `annotations/ec-0x07d0-sites.md` now maps one by
one) without requiring full coverage.
