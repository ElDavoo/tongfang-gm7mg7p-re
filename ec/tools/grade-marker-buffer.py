#!/usr/bin/env python3
"""Interpret a marker buffer capture and report whether the OC recovery
pattern is present.

Input is what docs/hardware-tests/oc-recovery-marker-buffer.md produces:
the sample-marker-buffer.py capture with addresses 0x0B00–0x0BFE, 0x0816,
and 0x0741. This tool reads the capture and reports:

  1. Whether the 0x0B00–0x0BFC region holds any non-zero bytes (Q1).
  2. If non-zero, whether 0x14 and 0x32 appear at different offsets (Q2).
  3. The latch and request bit values for context.

The procedure in docs/hardware-tests/oc-recovery-marker-buffer.md explains
what each result means and what it does not settle.

Nothing here touches hardware; it reads a file only.

Usage:
    python3 ec/tools/grade-marker-buffer.py <capture.txt>
"""
import argparse
import sys


def read_capture(path):
    """Parse a capture file and return a dict of {address: value}.

    The capture format is one address–value pair per line:
      0xABCD=0x12
    """
    values = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse address=value
            if '=' in line:
                addr_str, val_str = line.split('=', 1)
                try:
                    addr = int(addr_str, 0)
                    val = int(val_str, 0)
                    values[addr] = val
                except ValueError:
                    # Skip malformed lines
                    continue
    return values


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture", help="capture file from sample-marker-buffer.py")
    args = ap.parse_args(argv)

    try:
        values = read_capture(args.capture)
    except Exception as e:
        print(f"Error reading capture: {e}", file=sys.stderr)
        return 1

    # Extract the scan region (where the pattern is searched) and the latch/request.
    # The scan region is 253 bytes (0x0B00-0x0BFC); the neighbours 0x0BFD-0x0BFE
    # are captured for context (to see if the page was touched) but not searched.
    buffer_addrs = range(0x0B00, 0x0BFD)  # 0x0B00 to 0x0BFC inclusive (253 bytes)
    buffer_values = {addr: values.get(addr, 0) for addr in buffer_addrs}
    latch = values.get(0x0816)
    request = values.get(0x0741)

    # Q1: Does the buffer contain any non-zero bytes?
    has_nonzero = any(v != 0 for v in buffer_values.values())

    print(f"Buffer status (0x0B00–0x0BFC):")
    if has_nonzero:
        nonzero_count = sum(1 for v in buffer_values.values() if v != 0)
        print(f"  {nonzero_count} of {len(buffer_values)} bytes are non-zero")
    else:
        print(f"  all {len(buffer_values)} bytes are 0x00")

    # Q2: If non-zero, look for the 0x14/0x32 pattern at different offsets
    addr_0x14 = None
    addr_0x32 = None
    for addr, val in buffer_values.items():
        if val == 0x14 and addr_0x14 is None:
            addr_0x14 = addr
        if val == 0x32 and addr_0x32 is None:
            addr_0x32 = addr

    print(f"\nMarker pattern check:")
    if addr_0x14 is not None and addr_0x32 is not None:
        if addr_0x14 != addr_0x32:
            print(f"  0x14 found at offset 0x{addr_0x14 - 0x0B00:02x}")
            print(f"  0x32 found at offset 0x{addr_0x32 - 0x0B00:02x}")
            print(f"  → Pattern PRESENT (different offsets)")
        else:
            print(f"  0x14 and 0x32 at same offset 0x{addr_0x14 - 0x0B00:02x}")
            print(f"  → Pattern INCOMPLETE (same byte cannot be both)")
    elif addr_0x14 is not None:
        print(f"  0x14 found at offset 0x{addr_0x14 - 0x0B00:02x}")
        print(f"  0x32 not found")
        print(f"  → Pattern INCOMPLETE (0x32 missing)")
    elif addr_0x32 is not None:
        print(f"  0x32 found at offset 0x{addr_0x32 - 0x0B00:02x}")
        print(f"  0x14 not found")
        print(f"  → Pattern INCOMPLETE (0x14 missing)")
    else:
        print(f"  0x14 not found")
        print(f"  0x32 not found")
        print(f"  → Pattern ABSENT")

    # Context: latch and request
    print(f"\nLatch and request state:")
    if latch is not None:
        print(f"  0x0816 (latch) = 0x{latch:02x}")
        if latch == 0x03:
            print(f"    → both markers have been seen (latch == 3)")
        else:
            print(f"    → not the recovery-triggering state (latch != 3)")
    else:
        print(f"  0x0816 (latch) = not found in capture")

    if request is not None:
        bit7 = (request >> 7) & 1
        print(f"  0x0741 = 0x{request:02x}, bit 7 = {bit7}")
        if bit7:
            print(f"    → request bit is SET (recovery armed)")
        else:
            print(f"    → request bit is CLEAR")
    else:
        print(f"  0x0741 (request) = not found in capture")

    print(f"\nWhat this does NOT settle:")
    print(f"  * A buffer reading all zero does NOT prove there is no writer.")
    print(f"    The write could be rare, happen between samples, or fire only")
    print(f"    during an event not captured. docs/findings/0741-bit7-oc-recovery.md")
    print(f"    §7 is explicit: the region's writer is not found by any static")
    print(f"    method, so something unknown writes it through a path the")
    print(f"    analysis tools cannot see.")
    print(f"  * The absence of the pattern does NOT prove the recovery path")
    print(f"    never fires. Other writers with other marker bytes could exist.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
