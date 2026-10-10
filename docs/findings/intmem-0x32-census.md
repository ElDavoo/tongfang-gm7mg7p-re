# Internal RAM byte `0x32` is a state-machine value in the common-area dispatcher (issue #1701)

(2026-10-10. Static reading of decompiled C from `ec/firmware/GMxMGxx_11.800` via
`ec/tools/intmem_refs.py` and Ghidra, and visual census of committed exports in
`ec/decompiled/`. No capture, no EC, no hardware, and no `status:` other than
`present-untested`.)

Internal RAM byte `0x32` is a state value that controls dispatching in the
common-area dispatcher `FUN_CODE_2F85`. The byte is written by six explicit
producers, read by 26 sites across 24 decompiled exports, and is active in
multiple dispatch chains rather than a simple accumulator.

## 1. The write sites census

`ec/tools/intmem_refs.py` over `ec/firmware/GMxMGxx_11.800` reports 37 direct
references to `0x32` (36 EC main firmware, 1 PD image). The tool is unframed:
a hit may be a misframed read, a table entry, or actual code. The write/modify
sites are:

| File Offset | Runtime | Operation | Frame | Bank/Region |
|-------------|---------|-----------|-------|-------------|
| 0x00CD5 | 0x0CD5 | `clr 0x32` (clear) | 24/0 | common |
| 0x00E81 | 0x0E81 | `clr 0x32` | 22/2 | common |
| 0x03038 | 0x3038 | `mov 0x32,#imm` (set to immediate) | 24/0 | common |
| 0x03E61 | 0x3E61 | `mov 0x32,0xNN` (copy from another byte) | 24/0 | common |
| 0x0438D | 0x438D | `mov 0x32,a` (copy from accumulator) | 24/0 | common |
| 0x0DD31 | 0xDD31 | `mov 0x32,0xNN` | 22/2 | bank0 |
| 0x15FFF | 0xDFFF | `inc 0x32` (increment) | 1/23 | bank1 |
| 0x16B7C | 0xEB7C | `addc a,0x32` (accumulator += byte with carry) | 24/0 | bank1 |
| 0x22501 | 0x2501 | `add a,0x32` (accumulator += byte) | 24/0 | pd-image |

**Frame scores and calibration:** The frame column shows `onto/over` pairs from
`converges_from()`. The majority converge cleanly (24/0, 22/2), indicating
high-probability instruction boundaries. The `inc 0x32` at `bank1:0xDFFF` scores
`frame=1/23`, the documented low-score case. Per the tool's header and the
repository's calibration rule, this site is not filtered and its pair is read
rather than either half alone — the low score indicates a scanning blind spot or
a context mismatch, not proof of absence. The PD-image site at `0x22501` is in
a separate program's address space; refs there do not establish EC firmware
behavior, per `docs/findings/lightbar-bat-flow.md`.

Six of these are direct producers: two clears, one immediate write, two copies,
and one accumulator store. Two more are read-modify-writes in bank1. The
immediate write at `0x03038` and the accumulator write at `0x0438D` are the
highest-confidence producers; the copy sites at `0x03E61` and `0x0DD31` depend
on what writes to their source bytes. All six are EC main firmware (36 of 37 EC
refs total).

## 2. The dispatcher pattern

The byte is load-bearing in the common-area dispatcher `FUN_CODE_2F85`
(`common/2F85.c`). The function branches on `0x32`'s value across at least five
cases:

```c
if (DAT_INTMEM_32 == -0xe) {
    DAT_INTMEM_90 = 2;
    goto LAB_CODE_300d;
}
if (DAT_INTMEM_32 == -0xd) {
    puVar1 = &DAT_INTMEM_83;
} else {
    if (DAT_INTMEM_32 == -0xc) {
        _3_1 = 1;
        goto LAB_CODE_300d;
    }
    if (DAT_INTMEM_32 == -0xb) {
        _3_1 = 0;
        goto LAB_CODE_300d;
    }
    if (DAT_INTMEM_32 == -1) {
        _3_1 = 0;
        _2_3 = 0;
        // scan loop over 3 elements
        goto LAB_CODE_300d;
    }
    if (DAT_INTMEM_32 != -0x18) goto LAB_CODE_300d;
    puVar1 = &DAT_INTMEM_82;
}
*puVar1 = 0xff;
```

The dispatcher also seeds `DAT_INTMEM_82` and `DAT_INTMEM_83` from `0x32` under
certain conditions, establishing that the byte's value flows into multiple
downstream states. The dispatcher runs a second dispatch loop at `LAB_CODE_300d`
that again branches on `0x32`'s value:

```c
if (DAT_INTMEM_32 == -1) {
    uVar3 = 3;
} else if (DAT_INTMEM_32 == -0xe) {
    uVar3 = 2;
} else if (DAT_INTMEM_32 == -0x17) {
    uVar3 = 4;
} else {
    uVar3 = 1;
}
store_r7_to_upper_internal_ram_byte_3983(uVar3);
```

This establishes that `0x32` is not a simple accumulator or a read-only cursor,
but a state byte the common-area code switches on and uses to set secondary
states. The dispatch values are small signed integers: `-0x18` (-24), `-0x17`
(-23), `-0x10` (-16), `-0xe` (-14), `-0xd` (-13), `-0xc` (-12), `-0xb` (-11),
and `-1`.

## 3. The reader sites

`ec/tools/intmem_refs.py` identifies 26 pure-read sites in the EC firmware.
Visual census of the committed exports shows that 24 decompiled C files reference
`DAT_INTMEM_32` in read-only contexts: dispatchers, state checks, and value
flows to other bytes. Examples:

- `common/2F85.c`: dispatcher with six value comparisons
- `common/3042.c`: dispatcher with four value comparisons
- `common/3799.c`, `common/3E9A.c`, `common/3F68.c`: readers checking `0x32`
  against dispatch values
- `bank0/DD24.c`: passes `0x32` as an index to `read_xdata_0400_plus_r7()`
- `bank0/DD4A.c`: masks and ORs `0x32`'s low nibble into `XDATA_0x045A`:
  `XDATA_0x045A = (old & 0xF0) | (0x32 & 0x0F)`

The last example is the connection that surfaces from `docs/findings/class-b-access-cell-corrections.md`:
the function `or_intmem_32_low_nibble_into_045a` at `0xDD4A` establishes a
data dependency between `0x32` and the packed flag byte `XDATA_0x045A`, proving
that `0x32` is a producer feeding a named register entry.

## 4. Status and role

`0x32` is referenced in the EC main firmware (36 sites) and is active in a
state dispatcher — criteria for `present-untested`. The byte's value has not
been behaviorally verified on hardware, and its semantic role (what each
dispatch value means, when it is set, and what triggers the producer writes)
is outside the scope of this static analysis.

The evidence does not support stronger claims: no single writer dominates
the byte, and the six write sites suggest several unrelated producers,
consistent with a shared scratch byte that carries state across domain
boundaries. No analysis here constrains or refutes this — it is what the
decompiles show.

This byte is one of the three internal-RAM state bytes named in the dispatcher
alongside `DAT_INTMEM_82` and `DAT_INTMEM_83`, and its connection to
`XDATA_0x045A` establishes that understanding its role is a prerequisite for
understanding the packed flag byte the driver cares about.
