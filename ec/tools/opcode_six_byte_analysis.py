#!/usr/bin/env python3
"""
Analyze byte lengths of six dual-encoding opcodes (0x25, 0x35, 0x45, 0x55, 0x65, 0x95)
from committed disassembly listings' byte columns.

These opcodes have a dual encoding in the Intel 8051 manual: a two-byte form
(direct,#data or direct,@DPTR) and a three-byte alternative. This tool counts
occurrences of each opcode by the actual byte length rendered in the listings,
establishing what the committed .asm files show for this EC firmware image.

Reads ec/decompiled/*/*.asm and extracts instruction byte lengths from the
byte columns (the three-column format: byte1 byte2 byte3, with '-' for unused slots).
Counts per region (directory) and per opcode to determine whether any three-byte
reads appear, or whether all instances are two bytes.
"""

import re
from pathlib import Path
from collections import defaultdict


def parse_asm_line(line):
    """
    Parse a disassembly line to extract address, byte column, and mnemonic.

    Format: ADDRESS BYTE1 BYTE2 BYTE3 MNEMONIC [OPERANDS]
    Example: D018     90 05 14 mov      DPTR, #0x514

    The byte column has exactly 3 slots, each being 2 hex digits or '-' for empty.

    Returns (address, bytes_list, mnemonic) or (None, None, None) if not a code line.
    """
    # Skip comment lines and empty lines
    if line.startswith(';') or not line.strip():
        return None, None, None

    parts = line.split()
    if len(parts) < 5:
        # Need at least: address, byte1, byte2, byte3, mnemonic
        return None, None, None

    address = parts[0]
    # Validate address is 4 hex digits
    if not re.match(r'^[0-9A-Fa-f]{4}$', address):
        return None, None, None

    # Next 3 parts should be the bytes (each 2 hex digits or '-' for empty)
    byte1, byte2, byte3 = parts[1], parts[2], parts[3]
    # Each byte is either 2 hex digits or a single dash
    if not all((re.match(r'^[0-9A-Fa-f]{2}$', b) or b == '-') for b in [byte1, byte2, byte3]):
        return None, None, None

    mnemonic = parts[4]

    # Collect non-empty bytes (filter out '-')
    byte_list = [b for b in [byte1, byte2, byte3] if b != '-']

    return address, byte_list, mnemonic


def count_opcode_bytes():
    """
    Scan all .asm files in ec/decompiled/*/ and count occurrences of the
    six dual-encoding opcodes by their rendered byte length.

    Returns a dict mapping (region, opcode) -> {byte_length -> [addresses]}
    """
    target_opcodes = {'25', '35', '45', '55', '65', '95'}
    results = defaultdict(lambda: defaultdict(list))

    decompiled_dir = Path('ec/decompiled')
    if not decompiled_dir.exists():
        raise FileNotFoundError(f"{decompiled_dir} not found")

    # Iterate over regions (bank0, bank1, etc.)
    for region_dir in sorted(decompiled_dir.iterdir()):
        if not region_dir.is_dir():
            continue

        region = region_dir.name

        # Iterate over .asm files in the region
        for asm_file in sorted(region_dir.glob('*.asm')):
            with open(asm_file, 'r') as f:
                for line in f:
                    address, byte_list, mnemonic = parse_asm_line(line)
                    if address is None:
                        continue

                    if not byte_list:
                        continue

                    # Check if first byte matches one of the six opcodes
                    opcode = byte_list[0].upper()
                    if opcode not in target_opcodes:
                        continue

                    byte_length = len(byte_list)
                    results[(region, opcode)][byte_length].append(address)

    return results


def print_results(results):
    """Format and print the analysis results in a readable format."""
    if not results:
        print("No target opcodes found in listings.")
        return

    target_opcodes = ['25', '35', '45', '55', '65', '95']
    regions = sorted(set(region for region, _ in results.keys()))

    print("=" * 70)
    print("OPCODE SIX-BYTE ANALYSIS: Committed Listing Byte Lengths")
    print("=" * 70)
    print()

    # Summary table: per-region and per-opcode counts
    print("Counts by region and opcode (byte length shown if not 2):")
    print()

    all_counts = defaultdict(lambda: defaultdict(int))
    all_lengths = defaultdict(lambda: defaultdict(set))

    for (region, opcode), lengths_dict in sorted(results.items()):
        for length, addresses in lengths_dict.items():
            count = len(addresses)
            all_counts[region][opcode] += count
            all_lengths[region][opcode].add(length)

    # Print per-region summary
    for region in regions:
        print(f"{region}:")
        total_for_region = 0
        for opcode in target_opcodes:
            if opcode in all_counts[region]:
                count = all_counts[region][opcode]
                total_for_region += count
                lengths = all_lengths[region][opcode]
                if lengths == {2}:
                    print(f"  0x{opcode}: {count} (all 2-byte)")
                else:
                    print(f"  0x{opcode}: {count} (lengths: {sorted(lengths)})")
        print(f"  → subtotal: {total_for_region}")
        print()

    # Print grand total
    grand_total = sum(len(addrs) for length_dict in results.values()
                      for addrs in length_dict.values())
    print(f"Grand total: {grand_total} occurrences across all regions")
    print()

    # Check for non-2-byte instances (the key finding)
    print("=" * 70)
    non_two_byte = []
    for (region, opcode), lengths_dict in sorted(results.items()):
        for length, addresses in sorted(lengths_dict.items()):
            if length != 2:
                for addr in sorted(addresses):
                    non_two_byte.append((region, f"0x{opcode}", addr, length))

    if non_two_byte:
        print("NON-2-BYTE INSTANCES (potential three-byte reads):")
        for region, opcode, addr, length in non_two_byte:
            print(f"  {region}:{addr}  {opcode}  {length} bytes")
    else:
        print("FINDING: All six opcodes rendered as 2-byte instructions in listings.")
        print("No 1-byte, 3-byte, or 4-byte instances found.")
    print()


if __name__ == '__main__':
    results = count_opcode_bytes()
    print_results(results)
