#!/usr/bin/env python3
"""Build a flat 64 KiB memory image for one CODE bank, suitable for loading
into radare2 (-a 8051) or any other 8051 disassembler that expects a linear
address space.

0x0000-0x7FFF: common area, copied verbatim from the firmware file.
0x8000-0xFFFF: the requested bank, copied from its file offset (see
find_banks.py; bank 0 -> file 0x08000, bank 1 -> file 0x10000, per this
firmware dump -- re-run find_banks.py if you're working from a different
dump/version).

Usage:
    python3 make_bank_image.py ../firmware/GMxMGxx_11.800 0 0x08000 bank0.bin
    r2 -a 8051 -e scr.color=0 -c 's 0xb2e2; pd 20' bank0.bin
"""
import sys


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    fw_path, bank, file_off, out_path = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), sys.argv[4]
    d = open(fw_path, "rb").read()
    image = bytearray(d[0:0x8000])
    image += d[file_off:file_off + 0x8000]
    open(out_path, "wb").write(image)
    print(f"wrote {out_path}: common 0x0000-0x7FFF + bank {bank} (file 0x{file_off:05X}) at 0x8000-0xFFFF")


if __name__ == "__main__":
    main()
