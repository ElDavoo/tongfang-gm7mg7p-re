#!/usr/bin/env python3
"""Build a flat 64 KiB memory image for one CODE bank, suitable for loading
into radare2 (-a 8051), Ghidra, or any other 8051 disassembler that expects a
linear address space.

0x0000-0x7FFF: common area, copied verbatim from the firmware file.
0x8000-0xFFFF: the requested bank, copied from its file offset (see
find_banks.py; bank 0 -> file 0x08000, bank 1 -> file 0x10000, per this
firmware dump -- re-run find_banks.py if you're working from a different
dump/version).

--pd builds the ITE8850-PD image at file 0x20000 instead. It is a separate
64 KiB 8051 program with its own vectors and its own XDATA map, NOT a third
bank of the EC above, so it gets no common area grafted on the front --
ec/README.md and ec/annotations/lightbar-bat-flow.md §2 are the evidence, and
grafting one on is the mistake this mode exists to make impossible.

Usage:
    python3 make_bank_image.py ../firmware/GMxMGxx_11.800 0 0x08000 bank0.bin
    python3 make_bank_image.py --pd ../firmware/GMxMGxx_11.800 pd.bin
    python3 make_bank_image.py --self-test ../firmware/GMxMGxx_11.800
    r2 -a 8051 -e scr.color=0 -c 's 0xb2e2; pd 20' bank0.bin
"""
import sys

PD_FILE_OFFSET = 0x20000
PD_SIZE = 0x10000
PD_MARKER = b"ITE8850-PD"   # at file 0x20040; ec/README.md cites it


def build_bank(fw, bank, file_off, out_path):
    d = open(fw, "rb").read()
    image = bytearray(d[0:0x8000])
    image += d[file_off:file_off + 0x8000]
    open(out_path, "wb").write(image)
    print(f"wrote {out_path}: common 0x0000-0x7FFF + bank {bank} (file 0x{file_off:05X}) at 0x8000-0xFFFF")


def build_pd(fw, out_path):
    d = open(fw, "rb").read()
    image = d[PD_FILE_OFFSET:PD_FILE_OFFSET + PD_SIZE]
    if len(image) != PD_SIZE:
        raise SystemExit(f"error: PD image at 0x{PD_FILE_OFFSET:05X} is short "
                         f"({len(image)} of {PD_SIZE} bytes)")
    open(out_path, "wb").write(image)
    print(f"wrote {out_path}: ITE8850-PD image, file 0x{PD_FILE_OFFSET:05X}, "
          f"{PD_SIZE} bytes, own address space (no common area)")


def self_test(fw):
    """Known-answer run against the committed firmware. Every assertion here
    is re-derivable from ec/firmware/GMxMGxx_11.800 alone."""
    d = open(fw, "rb").read()
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        if not cond:
            ok = False

    print("make_bank_image.py --self-test")
    # The two layouts, rebuilt in memory rather than on disk.
    bank0 = d[0:0x8000] + d[0x08000:0x10000]
    bank1 = d[0:0x8000] + d[0x10000:0x18000]
    check("bank0 image is 64 KiB", len(bank0) == 0x10000)
    check("bank0 common area is the firmware's own first 32 KiB",
          bank0[:0x8000] == d[:0x8000])
    check("bank0 window is firmware file 0x08000-0x0FFFF",
          bank0[0x8000:] == d[0x08000:0x10000])
    check("bank1 common area is byte-identical to bank0's",
          bank1[:0x8000] == bank0[:0x8000])
    check("bank0 and bank1 windows differ (these are different banks)",
          bank0[0x8000:] != bank1[0x8000:])
    # The reset vector is common-area, so it must read the same in both.
    check("reset vector LJMP is in the common area and identical in both banks",
          bank0[:3] == bank1[:3] == bytes([0x02, 0x00, 0x70]))
    pd = d[PD_FILE_OFFSET:PD_FILE_OFFSET + PD_SIZE]
    check("PD image is 64 KiB", len(pd) == PD_SIZE)
    check(f"PD marker {PD_MARKER.decode()} at file 0x{PD_FILE_OFFSET + 0x40:05X}",
          pd[0x40:0x40 + len(PD_MARKER)] == PD_MARKER)
    check("PD image is not the EC's common area", pd[:0x8000] != d[:0x8000])
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if args and args[0] == "--self-test":
        if len(args) != 2:
            print(__doc__)
            return 1
        return self_test(args[1])
    if args and args[0] == "--pd":
        if len(args) != 3:
            print(__doc__)
            return 1
        build_pd(args[1], args[2])
        return 0
    if len(args) != 4:
        print(__doc__)
        return 1
    fw_path, bank, file_off, out_path = args[0], args[1], int(args[2], 0), args[3]
    build_bank(fw_path, bank, file_off, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
