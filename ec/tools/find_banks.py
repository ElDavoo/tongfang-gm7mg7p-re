#!/usr/bin/env python3
"""Locate and validate Keil BL51 bank-switch trampolines in the ITE EC image,
and figure out which file offset each CODE bank maps to at runtime address
0x8000-0xFFFF.

Background: this is a banked 8051 (256 KiB image, 8051 only addresses 64 KiB
directly). Keil's BL51 linker emits a small set of "bank switch" stubs in the
common area (reachable from every bank) that push return context, set the
bank-select port bits (P1.0-P1.2 here), and return. Every far call/jump into
a banked function actually goes through one of these stubs.

This script:
  1. Finds the stub prologues (`push 08h; mov a,#bank_hi; push acc; push dph;
     push dpl; mov r0,#restore_off; <bit ops>; ret`) in the common area.
  2. Counts how many places in the *common* area (0x0000-0x7FFF, always
     mapped) reference each stub via `MOV DPTR,#target ; LJMP/LCALL stub`.
  3. For each stub with trampoline callers, tries mapping the runtime window
     0x8000-0xFFFF against each 0x8000-sized slice of the file and scores how
     many trampoline targets land on a plausible 8051 instruction opcode
     (heuristic; see START_OPCODES) vs land on 0xFF padding.

Usage:
    python3 find_banks.py ../firmware/GMxMGxx_11.800
"""
import sys
import collections

# First-byte opcodes that plausibly start a Keil C51-generated function.
# Not exhaustive -- this is a scoring heuristic, not a disassembler.
START_OPCODES = {
    0xC0, 0x90, 0xE4, 0x7F, 0x7E, 0x7D, 0x7C, 0x7B, 0xEF, 0xEE,
    0x8F, 0x8E, 0x8D, 0x12, 0x75, 0xE5, 0xA2, 0x30, 0x20, 0x78,
    0x79, 0xD3, 0xC3, 0x02, 0x80, 0x74, 0x85, 0xAF, 0xAE, 0xAD,
}

STUB_PROLOGUE = bytes([0xC0, 0x08, 0x74])  # push 08h ; mov a,#<bank_hi>


def find_stubs(d: bytes):
    stubs = []
    a = 0x1100  # observed start on this image; adjust if a different dump is used
    while d[a:a + 3] == STUB_PROLOGUE and d[a + 4] == 0xC0:
        bits = [1 if d[a + 13 + 2 * k] == 0xD2 else 0 for k in range(3)]  # setb vs clr on P1.0/1/2
        bank = bits[0] | (bits[1] << 1) | (bits[2] << 2)
        stubs.append((a, bank))
        a += 20
    return stubs


def trampoline_targets(d: bytes, stub_addr: int, limit: int = 0x8000):
    """Find `MOV DPTR,#target ; LJMP/LCALL stub_addr` in the common area."""
    out = []
    for i in range(0, limit - 6):
        if d[i] == 0x90 and d[i + 3] in (0x02, 0x12):
            t = (d[i + 4] << 8) | d[i + 5]
            if t == stub_addr:
                out.append((d[i + 1] << 8) | d[i + 2])
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../firmware/GMxMGxx_11.800"
    d = open(path, "rb").read()

    stubs = find_stubs(d)
    print(f"Found {len(stubs)} bank-switch stubs in common area:")
    for addr, bank in stubs:
        print(f"  0x{addr:04X} -> selects bank {bank}")
    print()

    for addr, bank in stubs:
        targets = [t for t in trampoline_targets(d, addr) if t >= 0x8000]
        print(f"bank {bank} (stub 0x{addr:04X}): {len(targets)} trampoline call sites")
        if not targets:
            print("    no callers found -- bank likely unused on this SKU/firmware build")
            continue
        best = None
        for file_off in range(0x08000, len(d), 0x8000):
            ok = sum(1 for t in targets if d[file_off + (t - 0x8000)] in START_OPCODES)
            ff = sum(1 for t in targets if d[file_off + (t - 0x8000)] == 0xFF)
            score = ok / len(targets)
            print(f"    window 0x8000<-file 0x{file_off:05X}: plausible-entry {ok}/{len(targets)} ({score:.0%}), 0xFF={ff}")
            if best is None or score > best[1]:
                best = (file_off, score)
        print(f"  => best guess: bank {bank} lives at file offset 0x{best[0]:05X} (confidence {best[1]:.0%})")
        print()


if __name__ == "__main__":
    main()
