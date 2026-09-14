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

## Tools

- **`tools/scan_refs.py`** — counts direct `MOV DPTR,#addr` references to a
  given XDATA address. Fast way to check "does this EC firmware build
  implement register X". Validated 20/20 against live-hardware ground truth
  (see `docs/findings.md`), but has a known blind spot for pointer/indirect
  addressing — treat "0 refs" as "not found by this method", not "absent".
- **`tools/find_banks.py`** — locates the bank-switch stubs and scores which
  file offset each bank maps to. Re-run this against any other firmware dump
  before trusting the offsets in the table above.
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
- **`annotations/charge-profile-flow.md`** — full traced control flow for the
  three charge profiles, including the manual-control gate that made the
  systemd per-boot reapply necessary.

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
concrete next steps, several of which are independently useful (e.g. mapping
the 254 call sites referencing `0x07D0`) without requiring full coverage.
