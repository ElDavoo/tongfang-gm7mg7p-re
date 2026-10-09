# 28 base-8051 opcodes that disasm8051.mnemonic() now renders by name

(2026-10-09, issue #1390. Static reading of committed Ghidra listings in `ec/decompiled/*/*.asm` against `disasm8051.mnemonic()`. No EC, no hardware, no Windows, no registers.yaml row touched.)

`disasm8051.mnemonic()` renders 28 base-8051 opcodes by their instruction names rather than as `db 0xNN` fallbacks. The work was completed in issue #1153, and this write-up cites each opcode against the committed listings that first named it.

## The 28 opcodes

| opcode | instruction | sources |
|---|---|---|
| `0x06` | `inc @r0` | bank0/B065.asm |
| `0x07` | `inc @r1` | bank0/8048.asm |
| `0x16` | `dec @r0` | bank0/2BD5.asm |
| `0x17` | `dec @r1` | bank0/D091.asm |
| `0x26` | `add a,@r0` | bank1/E9CE.asm |
| `0x27` | `add a,@r1` | bank1/E9CE.asm |
| `0x36` | `addc a,@r0` | bank0/D091.asm |
| `0x37` | `addc a,@r1` | bank0/D091.asm |
| `0x46` | `orl a,@r0` | bank1/EAC3.asm |
| `0x47` | `orl a,@r1` | common/5A66.asm |
| `0x56` | `anl a,@r0` | bank1/EAC3.asm |
| `0x57` | `anl a,@r1` | bank1/8504.asm |
| `0x66` | `xrl a,@r0` | bank0/A312.asm |
| `0x67` | `xrl a,@r1` | bank0/A312.asm |
| `0x72` | `orl c,bit` | pd/A890.asm |
| `0x76` | `mov @r0,#data` | bank0/2BD5.asm |
| `0x77` | `mov @r1,#data` | common/6A02.asm |
| `0x82` | `anl c,bit` | bank0/8048.asm |
| `0x86` | `mov direct,@r0` | bank0/8653.asm |
| `0x87` | `mov direct,@r1` | bank0/A312.asm |
| `0x96` | `subb a,@r0` | bank0/D434.asm |
| `0x97` | `subb a,@r1` | common/6A02.asm |
| `0xA6` | `mov @r0,direct` | bank0/A663.asm |
| `0xA7` | `mov @r1,direct` | bank1/E722.asm |
| `0xB6` | `cjne @r0,#data,rel` | bank1/E9CE.asm |
| `0xB7` | `cjne @r1,#data,rel` | bank1/EAC3.asm |
| `0xD4` | `da a` | bank0/D434.asm |
| `0xF4` | `cpl a` | bank0/D091.asm |

## Verification

Every row above was settled against the committed Ghidra listings: the file names a location in `ec/decompiled/*/` that decodes at that opcode, and the committed listing names it. The only opcode the manual assigns and the listings do not use is `0xA5` (undefined), which `mnemonic()` still renders as `db 0xa5`.

## Relation to #1294

Issue #1294 addresses six separate opcodes (`0x42`/`0x43`/`0x52`/`0x53`/`0x62`/`0x63`), the `direct,A` and `direct,#data` forms of the same logical instruction group. Those six are distinct from the 28 base-8051 opcodes above. Both sets fall through to the same `db` fallback in `disasm8051.mnemonic()`, but issue #1294 owns the six and this issue owns the 28. See [`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md) §7, which coordinates the byte keying between them.

## Test

`ec/tools/test_disasm8051_db_fallthrough.py::NamedAgainstTheListings` asserts that `disasm8051.mnemonic()` returns the instruction name (not `db 0xNN`) for each opcode above, by reading the committed listings at runtime and checking agreement with `mnemonic()`'s output.
