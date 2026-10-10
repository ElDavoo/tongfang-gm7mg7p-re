# Register 0x0026: Host-Programmed Mask

## The population

Direct `MOV DPTR,#0x0026` sites in the EC firmware (bank0 + common area):

```
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x0026
0x0026  refs=6     ec=6     pd=0
```

The six offsets from a raw byte scan for `90 00 26`:

```
0x023BB, 0x0249A, 0x0259F, 0x025BA, 0x025EF, 0x02891
```

Access breakdown from `trace_xdata_refs.py`:

```
$ python3 ec/tools/trace_xdata_refs.py --csv ec/firmware/GMxMGxx_11.800 0x0026
```

- **Reads (5)**: 0x023BB, 0x0249A, 0x0259F, 0x025BA, 0x025EF
- **Writes (1)**: 0x02891

## The single writer

Offset 0x02891 is the complete body of `common/2890.c`:

```c
void FUN_CODE_2890(void)
{
  DAT_EXTMEM_0026 = 0;
  return;
}
```

An initialization to zero. No other `MOV DPTR,#0x0026` site in the image performs a write (`movx @dptr,a`).

## The five readers and their usage pattern

All five readers employ `0x0026` as a bit mask, in both complementary and direct forms.

**Negated mask (three overlapping exports in `common/258B`)**

`common/258B.c:23,28,42` reads the byte and applies it as a negated filter:

```c
param_4 = ~DAT_EXTMEM_0026 & param_4;  // line 23
param_2 = ~DAT_EXTMEM_0026 & (*(byte *)(param_3 + 0x6d) | param_4); // line 28
bVar4 = ~DAT_EXTMEM_0026 & *(byte *)(bVar3 + 0x6d); // line 42
```

The routine walks an 18-entry table at `param_3 + 0x6d`, clearing masked bits from each entry and comparing the remainder. The assembly at `common/258B.asm` confirms the mask read as `movx A,@DPTR` followed by `anl a,r6` / `orl a,r6` / `anl a,r7` / `anl a,r4`, establishing that the loaded value is immediately used in the masking operation.

**Direct mask (OR pattern in `common/2444`)**

`common/2444.c:28` OR-masks the byte into a flag byte:

```c
DAT_EXTMEM_0a48 = DAT_EXTMEM_0a48 & (DAT_EXTMEM_0026 | *(byte *)(DAT_EXTMEM_0a49 + 'm'));
```

**Shift-count mask (four overlapping exports)**

Four sites perform a shift-left followed by AND-mask:

- `common/223F.c:146` (offset 0x023BB, in `FUN_CODE_22ef` span 0x22EF-0x23C7)
- `common/22EF.c:79` (offset 0x023BB, directly in `FUN_CODE_22ef`)
- `common/2275.c:119`
- `common/2290.c`

All follow the same pattern:

```c
bVar5 = bVar5 << 1;  // shift left FUN_CODE_2a35() result
DAT_INTMEM_65 = bVar5 & DAT_EXTMEM_0026;
if (DAT_INTMEM_65 == 0) {
  DAT_INTMEM_4d = DAT_INTMEM_65;
  DAT_INTMEM_49 = DAT_INTMEM_65;
}
```

The shift-count references are logically duplicates: `common/223F`, `common/22EF`, `common/2275`, and `common/2290` form overlapping exports of the same code region (call-target boundaries as upper bounds per `ec/annotations/bank-call-audit.md`). All four reference the same runtime instruction at 0x023BB (confirmed by assembly offsets: `common/223F.asm` 0x223F-0x22EC, `common/22EF.asm` 0x22EF-0x23C7). The decompiler outputs separate functions for overlapping ranges, each reporting the same `movx` sites.

## Which explanation holds

The EC firmware initializes `0x0026` to zero in its initialization sequence, then uses it as a mask throughout multiple algorithms. The sole writer never changes it after initialization.

This pattern matches **explanation #1: `0x0026` is a mask the host programs**.

The fact that the EC's own image only initializes the byte to zero — rather than leaving it uninitialized or permanently setting a non-zero value — is the point of this design, not a contradiction to it. The EC expects the host (Windows userspace driver, BIOS, or earlier EC firmware stages) to program the actual mask values into this byte before the EC's usage sites are reached. The host-side writes are not visible in the EC firmware image — they are made by Windows or the BIOS — and the EC firmware only ever initializes `0x0026` to zero.

## Calibration notes

Nine textual occurrences of `DAT_EXTMEM_0026` appear in `ec/decompiled/`, against six direct sites in the image:

| File | Function | Offset | Type | Notes |
|------|----------|--------|------|-------|
| common/258B.c | FUN_CODE_258b | 0x0259F, 0x025BA, 0x025EF | read | Three distinct sites, all in negated-mask pattern |
| common/2444.c | FUN_CODE_2444 | 0x0249A | read | Direct OR-mask read at offset within FUN_CODE_2444 |
| common/2890.c | FUN_CODE_2890 | 0x02891 | write | Sole writer, initializes to zero |
| common/223F.c | FUN_CODE_223f | 0x023BB | read | Logically duplicate with 22EF/2275/2290 (overlapping exports) |
| common/22EF.c | FUN_CODE_22ef | 0x023BB | read | Same runtime location as 223F; it is the actual containing function |
| common/2275.c | FUN_CODE_2275 | 0x023BB | read | Logically duplicate (overlapping export) |
| common/2290.c | FUN_CODE_2290 | 0x023BB | read | Logically duplicate (overlapping export) |

The `scan_refs.py` blind spot on indirect addressing (`movx @Ri`) means six is a lower bound on direct sites; no address-taken or computed-DPTR sites for `0x0026` have been identified beyond these six.
