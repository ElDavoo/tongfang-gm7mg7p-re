#!/usr/bin/env python3
"""Capture the OC recovery marker buffer and related latches for grading.

Reads 0x0B00–0x0BFE (255 bytes of the marker buffer scanned by 0xCFC6),
plus 0x0816 (the latch) and 0x0741 (the request bit), through the ECMEM
window. Outputs the addresses and values in the format used by committed
captures, one address and value per line.

The procedure docs/hardware-tests/oc-recovery-marker-buffer.md explains
the context and what each read means. This tool turns the procedure into
a capture in the committed format so grading is mechanical.

Usage:
  sample-marker-buffer.py 0x0B 0xFF

Arguments are the page number (0x0B) and count (0xFF for 255 addresses,
which reads 0x0B00–0x0BFE). The tool reads count bytes starting at
0x0B00 and outputs the address–value pairs.

The output is compatible with grade-marker-buffer.py, which reads these
captures and reports whether the buffer holds non-zero bytes, and whether
it contains the 0x14/0x32 pattern at different offsets that would trigger
the OC recovery request.
"""
import sys
import os

# Add the current directory to path to import ecmem
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ecmem


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) < 2:
        sys.exit(__doc__)

    try:
        page = int(argv[0], 0)
        count = int(argv[1], 0)
    except ValueError:
        sys.exit(__doc__)

    # Build the address list: page (high byte) + offsets 0x00 to count-1
    base = (page << 8)
    addrs = [base + i for i in range(count)]

    # Read through ecmem
    try:
        values = ecmem.read(addrs)
    except Exception as e:
        print(f"Error reading ECMEM: {e}", file=sys.stderr)
        return 1

    # Output in the committed format: address=value per line
    for addr in addrs:
        if addr in values:
            print(f"0x{addr:04x}={values[addr]:#04x}")
        else:
            # This shouldn't happen, but handle it gracefully
            print(f"0x{addr:04x}=????", file=sys.stderr)

    # Also read and output the latch and request
    try:
        latch_val = ecmem.read([0x0816])[0x0816]
        print(f"0x0816={latch_val:#04x}")
    except Exception as e:
        print(f"Error reading latch 0x0816: {e}", file=sys.stderr)

    try:
        request_val = ecmem.read([0x0741])[0x0741]
        print(f"0x0741={request_val:#04x}")
    except Exception as e:
        print(f"Error reading request 0x0741: {e}", file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())
