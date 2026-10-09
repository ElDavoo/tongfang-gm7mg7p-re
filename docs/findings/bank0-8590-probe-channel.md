# The probe-channel reader at `bank0:0x8590` (issue #1485)

**Nothing here was observed on hardware.** No register was read, written or read back, and no probe was tested or measured. This is a static reading of committed listings (`ec/decompiled/`) and committed disassembly, all derived from the committed firmware `ec/firmware/GMxMGxx_11.800`. **Arithmetic is not behaviour**: the byte sequences below say what the code computes or stages, never that a byte held that value or that the EC acted on the result.

## 1. The routine's signature and entry point

The routine at `bank0:0x8590` is reached from the ten-step probe sweep in AC84 (`ten_step_check_1aaa_889e` at `bank1:0xAC84`) through the trampoline at `bank1:0x1AAA`. The trampoline sets `DPTR = 0x8590` and ljmps to `bank0:0x1100` (the BL51 bank-select stub for bank 0), which pushes the caller's `DPL` and `DPH` and calls the routine at the address `DPTR` now points to.

**The caller's parameters:**
- `R3 = 0x16` (constant, AC84 line 8590+offset, passed unchanged across the bank switch)
- `R4` = one of ten channel constants: `0x08`, `0x0F`, `0x18`, `0x19`, `0x0D`, `0x09`, `0x3C`, `0x3D`, `0x3E`, `0x3F` (in that order across the ten steps)
- `R5 = 0x0C` (constant)

The return value is checked by carry flag at AC84 `0xAC97` / `0xACA8` / `0xACB9` / `0xACC A` / `0xACDB` / `0xACF0` / `0xAD11` / `0xAD22` / `0xAD33` / `0xAD44` (once per step). If carry is set, AC84 returns immediately without storing anything. If carry is clear, AC84 stores the return value to one of ten XDATA slots (`0x0502`, `0x0518`, `0x052A`, `0x052E`, `0x0514`, `0x0506`, `0x053A`, `0x053C`, `0x053E`, `0x0540` in that order).

## 2. The routine's body: byte-by-byte

The routine is 42 bytes long (0x8590-0x05A9 inclusive).

```asm
8590     eb - -   mov      A, R3           ; R3 = 0x16
8591     f5 67 -  mov      0x67, A         ; Stage R3 to direct RAM at 0x67
8593     ec - -   mov      A, R4           ; R4 = channel constant
8594     f5 68 -  mov      0x68, A         ; Stage R4 to direct RAM at 0x68
8596     ed - -   mov      A, R5           ; R5 = 0x0C
8597     f5 69 -  mov      0x69, A         ; Stage R5 to direct RAM at 0x69
8599     12 b9 ae lcall    0xb9ae          ; Call init_0a59_block_from_direct_68()
859C     ff - -   mov      R7, A           ; Save return value in R7
859D     12 44 5e lcall    0x445e          ; Call stage_and_commit_0a56_block(R7, ...)
85A0     12 be 52 lcall    0xbe52          ; Call copy_x00c0_pair_to_iram_67_68()
85A3     e5 67 -  mov      A, 0x67         ; Restore R3 from staged value
85A5     fb - -   mov      R3, A           ;
85A6     e5 68 -  mov      A, 0x68         ; Restore R4 from staged value
85A8     fc - -   mov      R4, A           ;
85A9     22 - -   ret                      ; Return with A = R4's original value
```

## 3. What the staging routines do

### 3.1 `init_0a59_block_from_direct_68` at `bank0:0xB9AE`

Stages four bytes into XDATA `0x0A59`-`0x0A5C`:
- `0x0A59 ← 0x68` (R4's value, the channel constant)
- `0x0A5A ← 0x00`
- `0x0A5B ← 0xC0`
- `0x0A5C ← 0x00`

This is a fixed pattern: the channel constant goes into slot 0, then `0x00`, `0xC0`, `0x00`. The `0xC0` at offset 2 might be a configuration flag or opcode. Returns normally without affecting carry.

### 3.2 `stage_and_commit_0a56_block` at `bank0:0x445E`

Stages three values and a flag into XDATA starting at `0x0A56`:
- `0x0A56 ← R7` (result from 0xB9AE, which is always `A` on return, value unknown)
- `0x0A57 ← R5` (which is 0x0C from caller, always)
- `0x0A58 ← R3` (which is 0x16 from caller, always)
- Sets `0x0A5E ← 0xEE` (flag)
- Clears `0x0A60` and direct byte `0xAF`

Then it branches on bit 7 of `0x0A57` (which is 0x0C = `0b00001100`, so bit 7 is clear). Since bit 7 is clear, it falls through to further processing: it can call various routines depending on `0x0A5C` and `0x0A57`. The comment states "The listing stops at an sjmp to 0x4534 and the decompiled C continues far past that, so only the bytes here are described", meaning the rest of this routine is not fully analyzed. **This routine may be what sets or clears the carry flag, but the analysis stops before that point in the committed listing.**

### 3.3 `copy_x00c0_pair_to_iram_67_68` at `bank0:0xBE52`

Named from its decompiled C entry. Reads a pair from XDATA `0x00C0` and stores it into direct RAM at `0x67` and `0x68`, which overwrites the staged R3 and R4. The bytes it reads from `0x00C0` are not established here.

## 4. What the routine establishes

**From bytes alone:**
- The routine stages R4 (the channel constant) into XDATA `0x0A59`, combined with a `0xC0` flag at `0x0A5B`.
- It stages the constants R3=0x16 and R5=0x0C into XDATA.
- It calls routines that may access XDATA and modify carry.
- **It does not itself set or clear carry; one of the callees does.**

**Not established by bytes:**
- **What the carry flag signals.** The caller (AC84) checks it to decide whether to bail out, but 0x8590 itself does not set or clear it. It comes from 0xB9AE (unlikely, looks like a pure stager), 0x445E (likely, but the listing ends partway through), or 0xBE52 (possible).
- **Whether the ten R4 constants select ten channels, ten devices, or a mix.** The constant goes into XDATA as a byte value, and the name of the XDATA slot is unchanged across all ten calls (`0x0A59`). That is consistent with *indexed* access into a single structure (one set of slots for ten channels, or one for each of ten devices) rather than *branching* code. But the bytes do not establish which.
- **What `0x0A56`, `0x0A57`, `0x0A58`, `0x0A59`, `0x0A5A`, `0x0A5B`, `0x0A5C`, `0x0A5E`, `0x0A60` represent.** They are staged values and flags, but no register entry in `ec/annotations/registers.yaml` names any of them, and no consumer read in the committed tree accesses them directly by address. They are therefore present-untested in any formal census.

## 5. The relationship to issue #1351

Issue #1351 records that the `bank0:0x1100` stub (the bank-0 select stub that 0x1AAA calls) has a `ret` instruction at `0x110A` that appears to consume two of the four bytes it pushes (or does not consume them correctly), leaving uncertainty about what values remain in the register bank when the callee (0x8590) executes. **If a reading of 0x8590's behavior depended on what 0x1100 left in registers, that dependency would be recorded here, but the routine's own body (as committed) does not read from any register except those passed in explicitly (R3, R4, R5). It does not touch PSW, does not read R0, R1, R2, R6, R7 on entry, and does not assume any XDATA state except what it stages first.** So a resolved understanding of 0x1100 does not block a reading of 0x8590 at the level of this file.

## 6. Summary: what is established and what is open

| Claim | Established by | Still open |
|-------|---|---|
| R4 is a selector that goes into XDATA 0x0A59 | Bytes 8593-8594, 8599-859B | What it selects (channel, device, both, something else) |
| The routine stages specific constants (0x16, 0x0C) to XDATA | Bytes 8590-8597 | What those constants mean for the hardware |
| The routine calls 0xB9AE, 0x445E, 0xBE52 in that order | Bytes 8599-85A0 | What those callees do with the staged data and whether they set/clear carry |
| AC84 checks carry and bails out if set; otherwise stores to XDATA | AC84's assembly at 0xAC97+, not this routine | Whether the carry signals an error, a timeout, or something else |
| The ten XDATA slots (0x0502, 0x0518, ...) receive results | AC84's assembly, not this routine | What those slots represent (temperatures, statuses, something else) |

## Files and commands

- `ec/decompiled/bank0/8590.asm`: disassembly (committed after export)
- `ec/decompiled/bank0/8590.c`: decompilation (committed after export)
- `ec/decompiled/bank0/B9AE.c`: called routine (already committed)
- `ec/decompiled/bank0/445E.c`: called routine (already committed, listing incomplete)
- `ec/decompiled/bank0/BE52.c`: called routine (already committed)
- AC84's disassembly and decompile at `ec/decompiled/bank1/AC84.{asm,c}` with all ten calls enumerated

---

**Opened by:** issue #1485, a seeding task for `bank0:0x8590`.
