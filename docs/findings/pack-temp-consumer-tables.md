# The pack-temperature consumer tables at `0xAFF1`, `0xAFB1`, `0xB031`, `0xB071`, `0xAF91`, `0xB0B1`, `0xAFA1`, `0xB0C1` (issue #1484)

**Nothing here was observed on hardware.** No register was read, written or
read back, and no code path was seen run. This is a static reading of the
committed listing `ec/decompiled/bank1/B0D1.asm` and extraction from the
committed image `ec/firmware/GMxMGxx_11.800`. **Arithmetic is not behaviour**:
the dK values below say what a byte sequence represents, never that a byte
held that value, that a code path executes, or that the EC acted on the result.

The eight tables named in this document are the consumer side of the register
pair at `0x04A2`/`0x04A3` (PACK_TEMP_DK), documented in
[[pack-temp-producer-chain]], which holds the comparison constants and index
mappings that the `step_index_056b_update_0495_0493` routine at bank1:0xB0D1
uses to track a step counter through a temperature ladder.

## 1. The four main tables: structure and the selection rule

`B0D1.asm` loads `DPTR` with one of four addresses depending on three bytes:

| condition | DPTR | address |
|---|---|---|
| bit 0 of 0x0497 is clear | 0xAFF1 | B116 |
| bit 0 of 0x0497 is set AND 0x0398 equals 0xA5 | 0xB071 | B107 |
| bit 0 of 0x0497 is set AND 0x030D is 0x0F or 0x10 | 0xAFF1 | B10C |
| bit 0 of 0x0497 is set AND 0x030D is 0x11 | 0xB031 | B111 |
| bit 0 of 0x0497 is set AND 0x030D is anything else | 0xAFB1 | B102 |

(The first and third rows both select 0xAFF1, which is reachable by two
different paths through the gate.)

The routine indexes into the selected table with the low nibble of XDATA
0x056B left-shifted twice (lines B0D1-B0DA: `mov DPTR,#0x56b / movx A,@DPTR /
anl A,#0xf / clr CY / rlc A / rlc A`), yielding a byte offset into 16 entries
of 4 bytes each. Lines B119-B127 load all four bytes of an entry into R2:R1:R4:R3
and store bytes 3:2 to 0x056E/0x056F and bytes 1:0 to 0x056C/0x056D; the pair
0x04A2/0x04A3 is then loaded and compared against the entry's low word by the
helper at 0x8863.

**This is a static reading of instruction sequences and addresses. The selection
rule is derived from the byte-level conditions in B0D1.asm, not from
runtime state or a second source.**

## 2. The four main table contents as extracted from the firmware image

Each table occupies 16 entries of 4 bytes (64 bytes total), at file offsets
derived from their CODE addresses by the conversion 0x10000 + (address - 0x8000).

### 0xAFF1 (file 0x12FF1)

| Entry | Low word | High word | Bytes | Decimal (low) |
|---|---|---|---|---|
| 0 | 0xBE0A | 0x0000 | 0A BE 00 00 | 2926 |
| 1 | 0xBE0A | 0x820A | 0A BE 0A 82 | 2926 |
| 2 | 0xDC0A | 0x960A | 0A DC 0A 96 | 2780 |
| 3 | 0x4A0B | 0xAA0A | 0B 4A 0A AA | 2890 |
| 4 | 0x6C0C | 0x360B | 0C 6C 0B 36 | 3180 |
| 5 | 0x800C | 0x580C | 0C 80 0C 58 | 3200 |
| 6 | 0xE40C | 0x6C0C | 0C E4 0C 6C | 3300 |
| 7 | 0x020D | 0xD00C | 0D 02 0C D0 | 3330 |
| 8 | 0x160D | 0xEE0C | 0D 16 0C EE | 3350 |
| 9 | 0x910E | 0xEE0C | 0E 91 0C EE | 3601 |
| 10 | 0xED2A | 0x0C0D | 2A ED 0D 0C | 10989 |
| 11 | 0xED2A | 0x0C0D | 2A ED 0D 0C | 10989 |
| 12 | 0xED2A | 0x0C0D | 2A ED 0D 0C | 10989 |
| 13 | 0xED2A | 0x0C0D | 2A ED 0D 0C | 10989 |
| 14 | 0xED2A | 0x0C0D | 2A ED 0D 0C | 10989 |
| 15 | 0xED2A | 0x0C0D | 2A ED 0D 0C | 10989 |

### 0xAFB1 (file 0x12FB1)

| Entry | Low word | High word |
|---|---|---|
| 0 | 0xBE0A | 0x0000 |
| 1 | 0xBE0A | 0x820A |
| 2 | 0xDC0A | 0x960A |
| 3 | 0xDC0A | 0xAA0A |
| 4 | 0x6C0C | 0xBE0A |
| 5 | 0x800C | 0x580C |
| 6 | 0xE40C | 0x6C0C |
| 7 | 0x020D | 0xD00C |
| 8 | 0x160D | 0xEE0C |
| 9 | 0x910E | 0xEE0C |
| 10–15 | 0xED2A | 0x0C0D |

Differs from 0xAFF1 at entry 3 (0xDC0A vs 0x4A0B) and entry 4 (0xBE0A vs 0x360B).

### 0xB031 (file 0x13031)

| Entry | Low word | High word |
|---|---|---|
| 0 | 0xBE0A | 0x0000 |
| 1 | 0xBE0A | 0x820A |
| 2 | 0xDC0A | 0x960A |
| 3 | 0x4A0B | 0xAA0A |
| 4 | 0x6C0C | 0x360B |
| 5 | 0x800C | 0x580C |
| 6 | 0xE40C | 0x6C0C |
| 7 | 0x340D | 0xD00C |
| 8 | 0x480D | 0x200D |
| 9 | 0x910E | 0x200D |
| 10–15 | 0xED2A | 0x3E0D |

Differs from 0xAFF1 at entries 7, 8, 9 (low words: 0x340D vs 0x020D, 0x480D vs 0x160D),
and at entries 10–15 (high word 0x3E0D vs 0x0C0D).

### 0xB071 (file 0x13071)

| Entry | Low word | High word |
|---|---|---|
| 0 | 0xBE0A | 0x0000 |
| 1 | 0xBE0A | 0x820A |
| 2 | 0xDC0A | 0x960A |
| 3 | 0xDC0A | 0xAA0A |
| 4 | 0x9E0C | 0xA00A |
| 5 | 0x9E0C | 0x6C0C |
| 6 | 0x480D | 0x6C0C |
| 7 | 0x660D | 0x020D |
| 8 | 0x7A0D | 0x520D |
| 9 | 0x910E | 0x520D |
| 10–15 | 0xED2A | 0x700D |

Differs from 0xAFF1 at entries 3–9 and at entries 10–15 (high word 0x700D vs 0x0C0D).

## 3. The low-word ladder: rises then saturates

All four main tables share the same low-word structure across the first ten
entries, with differences at scattered entries:

- Entry 0: 0xBE0A (2926 dK)
- Entries 1–9: form a rising sequence (values do not decrease)
- Entries 10–15: saturate at 0xED2A (10989 in decimal)

The rise spans from 2926 dK to 3601 dK over nine steps. The saturation value
0xED2A is at least `0xED2A - 0x0CE4 = 0xA46 = 2630` units above the consumer's
comparison constant 0x0CE4 documented in [[pack-temp-producer-chain]], §3.

**Whether this is a dK ladder, a step table, or a mapping of some other kind
is not established by arithmetic alone.** The fact that the sequence rises and
saturates is a pattern in the bytes, not evidence of physical behaviour. The
consumer reads a table entry every time 0xB0D1 executes and compares the low
word against 0x04A2/0x04A3; what relationship that comparison bears to the
pack temperature is a hardware question and is not answered here.

## 4. The four index tables: byte mappings for flags

### 0xAF91 and 0xB0B1 (file 0x12F91 and 0x130B1, identical)

```
0C 08 00 00 00 00 00 10 30 B0 B0 B0 B0 B0 B0 B0
```

All 16 bytes. Used by B0D1 at lines B176-B193 to index into a byte value that
is ORed into 0x0495 while preserving bits 0x43:

```
DAT_EXTMEM_0495 = puVar3[DAT_EXTMEM_056b & 0xf] | DAT_EXTMEM_0495 & 0x43
```

### 0xAFA1 and 0xB0C1 (file 0x12FA1 and 0x130C1, identical)

```
20 20 20 40 00 80 80 80 80 80 80 80 80 80 80 80
```

All 16 bytes. Used by B0D1 at lines B194-B1B1 to index into a byte value that
is ORed into 0x0493 while preserving bits 0x1F:

```
DAT_EXTMEM_0493 = puVar3[DAT_EXTMEM_056b & 0xf] | DAT_EXTMEM_0493 & 0x1f
```

Both pairs (AF91/B0B1 and AFA1/B0C1) are selected by bit 0 of 0x0497
(lines B173-B1A3), the same byte that gates the main table selection.

## 5. Limitations and hardware questions

- **Not "absent".** These tables are extracted from the committed firmware
  image and their addresses are derived from committed disassembly. The search
  is exhaustive for these eight addresses; a ninth table with related purpose is
  outside this search.
- **Not behaviour.** The low words form a rising-then-saturating pattern in
  bytes. The byte facts (address, count, value) are certain; what the EC does
  when it reads them is not.
- **Not a unit.** The decimal conversions assume dK (decikelvin) based on prior
  findings, but this file does not establish what the low words measure. No
  conversion to °C is attempted here and is not established here.
- **The gate selection is untested.** The rule from B0D1.asm is what the bytes
  say. Whether the EC actually branches to each table, and under what runtime
  conditions, would need execution traces.

## 6. Related findings

[[pack-temp-producer-chain]] documents the producer side (0x04A2/0x04A3,
PACK_TEMP_DK) and names these tables as the next hop not walked. Issue #1425
tracked that producer chain; this issue extracts the consumer side.
