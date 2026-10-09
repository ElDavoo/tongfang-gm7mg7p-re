# Opcode 0x25/0x35/0x45/0x55/0x65/0x95: Six-Byte Reading Validation

## Executive summary

The disassembly listings in `ec/decompiled/*/*.asm` render all 191 occurrences of the six dual-encoding opcodes (`0x25`, `0x35`, `0x45`, `0x55`, `0x65`, `0x95`) as two-byte instructions. No three-byte instances appear in the committed listings. This supports the current tree's two-byte assumption for these opcodes in this EC firmware image.

## Background

`disasm8051.py` contains a long comment recording a deliberate unresolved disagreement: the Intel 8051 manual's opcode table admits both a two-byte form (`direct,#data` or `direct,@DPTR`) and a three-byte alternative for the six opcodes listed above. The current tree renders all twelve opcodes of the group as two bytes, with `OPCODE_LEN` entries set to 2.

The only justification anywhere in the tree until now was a claim about assembler/compiler behaviour, not about this firmware image's actual rendering. `ec/tools/opcode_coverage.py` cannot distinguish the two readings because both `MCS51_LEN` and `OPCODE_LEN` use the same two-byte assumption. This investigation measures the actual instruction lengths from the committed disassembly listings' byte columns, using the method that `test_dptr_rebuild_forms.py` already applies to the `direct` opcode class.

## Method

Extracted instruction byte lengths from the byte columns of `ec/decompiled/*/*.asm` files for all occurrences of the six opcodes. Each `.asm` file records instructions in the format:

```
ADDRESS BYTE1 BYTE2 BYTE3 MNEMONIC [OPERANDS]
```

where each byte slot is either two hex digits or `-` for empty. The byte column counts the non-empty slots. The analysis tool (`ec/tools/opcode_six_byte_analysis.py`) reads all listings and tallies occurrences by region and opcode, grouped by the actual byte length they show.

## Results

Total occurrences across all regions: **191**

Per region and opcode:

| Region | 0x25 | 0x35 | 0x45 | 0x55 | 0x65 | 0x95 | Subtotal |
|--------|------|------|------|------|------|------|----------|
| bank0  | 21   | 1    | —    | —    | —    | 3    | 25       |
| bank1  | 15   | 16   | 25   | 1    | 3    | —    | 60       |
| common | 10   | 23   | 9    | 2    | —    | 3    | 47       |
| pd     | 32   | 19   | 6    | 2    | —    | —    | 59       |
| **Total** | **78** | **59** | **40** | **5** | **3** | **6** | **191** |

All occurrences are rendered as **two-byte** instructions. No one-byte, three-byte, or four-byte instances appear in the listings.

To reproduce:

```bash
python ec/tools/opcode_six_byte_analysis.py
```

## Interpretation

The committed disassembly listings support the two-byte rendering for all six opcodes across this firmware image. No evidence of the Intel manual's three-byte alternative appears in any region.

### Calibration caveat

This finding is bounded by the listings' coverage. The `.asm` files cover all named functions and their decompiled outputs, and `build_ec_decompile.py` extracts them from the committed firmware image. A null result means "not found by these static listings," not "the three-byte form does not exist in the image" — the listings could miss uncovered code regions or sequences not yet attributed to a function. In practice, `ec/tools/citation_gap_scan.py` identifies uncovered regions, and `ec/tools/converges_from()` uses these to frame findings conservatively. An investigation that sampled only named functions and found zero three-byte instances makes the result stronger, not weaker; it is not claimed as exhaustive.

## Impact

This finding supports the status quo: the two-byte entries in `OPCODE_LEN` for these six opcodes are consistent with the rendered listings. The current tree's assumption is calibrated against the committed disassembly, the closest available primary source. This does not rule out a future image or a dynamic decoder that uses the three-byte form — only that this one does not, as far as these static listings show.

The related issue is recorded in the plan for #1586: `ec/tools/opcode_coverage.py --divergence` remains blind to this choice because both `MCS51_LEN` and `OPCODE_LEN` agree with each other on the same assumption. `test_direct_address_renderings.py` now pins the length assertions; that remains the guard against silent changes, and this document records what the guard is defending.
