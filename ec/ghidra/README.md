# Ghidra: towards a C codebase for the EC

**Goal (docs/MISSION.md):** a C codebase that mirrors the EC firmware
function for function: decompiled from `../firmware/GMxMGxx_11.800`,
symbolized from `../annotations/registers.yaml`, and with every function cited
back to its bank and address. The vendor's source isn't available, so this is
its reconstruction. Tracked as issue #20.

**Status: not started.** No Ghidra project or decompiled output exists in this
repository yet. As of 2026-09-19 the toolchain does exist:
`.github/actions/project-setup` installs Ghidra 12.1.3 (headless) plus a
JDK 21 on every agent run and every `@claude` run. After that action,
`analyzeHeadless` is on `PATH` and `GHIDRA_INSTALL_DIR` points at the install.

## How to start (the approach this README has always recommended)

Ghidra's SLEIGH processor spec for 8051 (`8051:BE:16:default`) has no native
concept of Keil BL51 bank switching. Don't model the bank switching in
Ghidra first:

1. Build one flat 64 KiB image per CODE bank with
   `../tools/make_bank_image.py`: common area `0x0000-0x7FFF` plus the bank
   at `0x8000-0xFFFF` (bank 0 = file `0x08000`, bank 1 = file `0x10000`, per
   `../tools/find_banks.py`).
2. Import each image as its own program (`-loader BinaryLoader
   -processor 8051:BE:16:default`) and let auto-analysis run from the
   reset/interrupt vectors.
3. Name XDATA (Ghidra's `EXTMEM` space) from `../annotations/registers.yaml`
   before decompiling, so the output reads `OEM_4_CHARGING_PROFILE` rather
   than `DAT_EXTMEM_07a6`.
4. Decompile every function and write one C file per function, named by bank
   and address. Common-area functions come out once per bank program;
   de-duplicate them.
5. Cross-link banks by hand through the BL51 trampolines
   (`../annotations/bank-call-audit.md`, `bank-call-targets.csv`).

The separate `ITE8850-PD` image at file `0x20000` is a different program
with its own XDATA map (`../annotations/lightbar-bat-flow.md`). If it gets
decompiled, it goes in its own tree.

## Worked target: the charge-target derating routine

`../annotations/charge-target-derating.md` hand-decodes one routine (bank 0,
`0xB1F0`-`0xB38D`) into pseudo-C. It's the first function whose Ghidra output
should be checked against a human reading, and a sanity test for the
pipeline above.
