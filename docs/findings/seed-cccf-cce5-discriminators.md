# Seeding `0xCCCF` and `0xCCE5`: the 1 and 3 discriminator writers for `0x06E6`

## Summary

Two additional functions in the `0x06E6` discriminator-writer family have been identified and seeded into `ec/annotations/ghidra-functions.csv`. Both are reached via far-call stubs in the common area, exactly as `0xCC64` and `0xCCFC` are. The work is pure static analysis of the committed EC firmware image.

- **`0xCCCF`** (`init_06e6_1_ccf`): Writes `1` to `0x06E6`. Sits immediately after `0xCC64`'s body; whether it is distinct or a tail is an open question the decompile will settle.
- **`0xCCE5`** (`init_06e6_3`): Writes `3` to `0x06E6`.

## Reachability

Both entries are reached through the same trampoline story that `ec-07c4-07d5-sites.md` §4.3 established for `0xCC64`:

1. Far-call stubs in the common area (`0x1100` bank-select window) load DPTR with the bank-0 address
2. Jump to the bank-0 select stub at `0x1100` with `ljmp`
3. No direct `lcall` or `ljmp` references to either address are found in the task-call-table, confirming they are reached only through the far-call stubs documented below

The task-call-table stubs are:

```
$ grep -E "0x1864|0x1882" ec/annotations/task-call-table.csv
far-call-stub,0x1150,302,0x1864,ljmp,0xCCE5,0x1100,bank0
far-call-stub,0x1150,307,0x1882,ljmp,0xCCCF,0x1100,bank0
```

## Function definitions

### `0xCCCF` (`init_06e6_1_ccf`)

Opens with:
```
lcall 0x2896
mov dptr,#0x06e6
mov a,#0x01
movx @dptr,a
```

Writes the discriminator value `1` to `0x06E6`.

**Boundary question:** This entry sits immediately after `0xCC64`'s 107-byte body. The recorded `size` for `0xCC64` ends exactly at `0xCCCE`, and `0xCCCF` begins at the next instruction. A `ret` opcode at `0xCCCE` signals a function boundary, but the question whether that means `0xCCCF` is a distinct entry or shares control flow with `0xCC64` as a tail will be settled by examining the decompiled `.asm` and `.c`. The annotation has been seeded to force the Ghidra decompile and make the question observable.

### `0xCCE5` (`init_06e6_3`)

Writes the discriminator value `3` to `0x06E6`.

## The `0x06E6` discriminator

Four entries in the firmware write to `0x06E6`:

| Address | Name | Value |
|---------|------|-------|
| `0xCC64` | `init_06e6_1_clear_0743_07c5_and_07d5_ff` | `1` |
| `0xCCCF` | `init_06e6_1_ccf` | `1` |
| `0xCCE5` | `init_06e6_3` | `3` |
| `0xCCFC` | `power_on_init_and_two_hang_paths` | `5` |

What these values select is **not known**. The `0x06E6` register has no entry in `ec/annotations/registers.yaml`, and cross-references to other parts of the firmware that *read* `0x06E6` to dispatch on these values have not been found. This may be because they are absent, or because they use computed-DPH addressing or indirect `movx @Ri`, which are invisible to a direct `MOV DPTR` scan.

## Evidence

All information is derived from:
- The committed EC firmware image `ec/firmware/GMxMGxx_11.800`
- The far-call stubs in `ec/annotations/task-call-table.csv`
- The disassembly and decompilation produced by Ghidra on the annotated entries

This is static analysis. No register is read back and no claim of observed behaviour belongs here.
