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
- **`tools/register_ref_table.py`** — the whole `annotations/registers.yaml`
  table in one pass: per-image count split *and* what each site behind it does
  (`read`/`write`/`movc` CODE pointer/handed to a subroutine/…), as a markdown
  table or, with `--csv`, one row per site. Reconciles class buckets against
  the site count and main + PD against the file-wide total, and exits non-zero
  if either fails. The classification inherits the 8-instruction linear walk's
  limits — `annotations/static-refs-audit.md` §5 is the table it produced and
  the caveats that go with it.
- **`tools/disasm8051.py`** — the opcode tables `trace_xdata_refs.py` decodes
  with, plus a CLI for reading a window of instructions at a file offset
  (`--at`) and for measuring how many nearby anchors a linear walk syncs onto
  it from (`--converge`). Not a disassembler: linear only, no branch
  following, no code/data separation. `python3 tools/disasm8051.py --self-test`
  re-decodes the two windows `annotations/charge-profile-flow.md` transcribed
  from `r2` by hand and diffs against them — run it after touching either
  table.
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
- **`tools/make_bank_image.py`** — stitches common area + one bank into a
  flat 64 KiB image loadable by `r2 -a 8051` (or any other 8051 disassembler
  expecting linear addressing).

```console
$ python3 tools/make_bank_image.py firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -c 's 0xb2e2; pd 10' /tmp/bank0.bin
```

## Annotations

- **`annotations/registers.yaml`** — every EC register the `uniwill-laptop`
  driver or the Windows service touches, cross-referenced against static-scan
  results and live-hardware behaviour. This is the primary research output;
  start here.
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
- **`annotations/lightbar-bat-flow.md`** — the `0x07E2`-`0x07E5` site map, the
  evidence that those sites belong to the PD image rather than the EC, and the
  live probe still needed to say what (if anything) the EC does with those
  bytes.
- **`annotations/bank-call-audit.md`** — the call-target census behind every
  EC-side handoff this repo resolves: how many direct calls stay in the common
  area, how many assume the caller's own bank, how many are unresolvable, and
  why the same-bank assumption cannot be verified from these bytes however the
  counts come out — plus §7, the paged `ajmp`/`acall` family, and §8, the
  PC-relative branches, neither of which the assumption ever has to carry.
  `annotations/bank-call-targets.csv`,
  `annotations/bank-paged-call-targets.csv` and
  `annotations/bank-relative-branch-targets.csv` are the per-site tables.

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

Treat this as the honest state: a documented, reproducible starting point
for a Ghidra 8051-processor-module project (`ghidra/` is a placeholder for
that), not a finished decompiler. See the repo's GitHub issues for the
concrete next steps, several of which are independently useful (e.g. the 254
call sites referencing `0x07D0`, which `trace_xdata_refs.py` places in the PD
image rather than the EC and `annotations/ec-0x07d0-sites.md` now maps one by
one) without requiring full coverage.
