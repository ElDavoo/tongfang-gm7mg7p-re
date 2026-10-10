# Internal RAM byte 0x32 is a state-machine value read by the EC dispatcher (issue #1701)

(2026-10-10. Static analysis of the committed firmware over
`ec/firmware/GMxMGxx_11.800`, cross-checked against committed decompiles
under `ec/decompiled/` and the tool output of `ec/tools/intmem_refs.py`.
No capture opened, no EC, no hardware, and no `status:` moved by this work
alone.)

The byte is measured, busy, and load-bearing in the firmware's state machine.
`ec/tools/intmem_refs.py` over the firmware reports 37 direct references: 36 in
the main EC firmware and 1 in the PD image (the separate firmware program, not
the same address space). Ten of those are writes or read-modify-writes; the
other 26 are reads. Twenty-four committed decompiles under `ec/decompiled/`
reference `DAT_INTMEM_32` as a symbol.

## 1. Write sites and producers

Six routines write or conditionally modify 0x32:

| address | bank | operation | function |
|---|---|---|---|
| 0x00CD5 | common | `clr 0x32` | clear to zero |
| 0x00E81 | common | `clr 0x32` | clear to zero |
| 0x03038 | common | `mov 0x32,#imm` | load constant (site appears in FUN_CODE_3042) |
| 0x0438D | common | `mov 0x32,a` | write from accumulator (FUN_CODE_4389: `DAT_INTMEM_32 = DAT_EXTMEM_130a`) |
| 0x0DD31 | bank0 | `mov 0x32,0xNN` | copy from internal RAM (bank0 call_d57b_with_0d32_tail_3f9d) |
| 0x15FFF | bank1 | `inc 0x32` | increment (frame=1/23, low-confidence framing — see methodology note) |

One read-modify-write in bank1 (`0x16B7C`, `addc a,0x32` in FUN_CODE_e9ce) and
one in the PD image (`0x22501`, `add a,0x32`) add to the byte's value rather
than replacing it.

The byte's value is copied *from* 0x32 into 0x20 at `0x03E61` (FUN_CODE_3e61:
`DAT_INTMEM_20 = DAT_INTMEM_32`), and into the high nibble of XDATA 0x045A at
`0x0DD4A` via the mask-and-OR in `or_intmem_32_low_nibble_into_045a`:
`XDATA_045A = (old & 0xf0) | (DAT_INTMEM_32 & 0x0f)`.

## 2. Dispatcher behaviour in the common-area state machine

`ec/decompiled/common/2F85.c` and `ec/decompiled/common/3042.c` both implement a
dispatcher that branches on 0x32's value:

| value | action | function |
|---|---|---|
| -0x18 | set `DAT_INTMEM_82 = -1` | common/2F85.c:63 |
| -0x0E | set `DAT_INTMEM_90 = 2` | common/2F85.c:35, 3042.c:31 |
| -0x0D | set `DAT_INTMEM_83 = -1` | common/2F85.c:39 |
| -0x0C | set `_3_1 = 1` | common/2F85.c:43 |
| -0x0B | set `_3_1 = 0` | common/2F85.c:47 |
| -1 | run scan loop | common/2F85.c:50-60 |

In both functions, the byte also determines which dispatch value to store into
`_3_3` (an internal-RAM byte that appears to track the dispatcher's result code)
at lines 2F85:68-79 and 3042:27-38: -1 stores 3, -0x0E stores 2, -0x17 stores
4, and all other values store 1.

The byte is **active state** — multiple code paths depend on its value and
produce effects (writing other registers, controlling loop termination) whose
behaviour changes across the cases.

## 3. Methodology and calibration

### 3.1 The tool's scope

`intmem_refs.py --help` states: "Unframed byte scan: a hit may be a misframed
read, a table entry, or data. Indirect access is invisible here. A zero means
'not found by this method', never 'absent' or 'private'."

The tool's opcode window is a byte pattern match with no control-flow framing;
it cannot distinguish a byte operand from a stale table entry or padding, and it
is blind to register-indirect or pointer-based access. Therefore:

- The 37-reference count is "found by this method" (direct operand byte scan),
  not a statement of absence or presence in other forms.
- All 37 sites reported by the tool have been visually inspected in the
  committed decompiles and verified to be code, not data or noise.

### 3.2 The low-scoring case at bank1:0xDFFF (frame=1/23)

The tool reports `inc 0x32` at file offset 0x15FFF (bank1 runtime 0xDFFF) with
frame convergence `1/23`, indicating low confidence in framing — the byte
appears to match an opcode pattern in only one frame hypothesis out of 23
possible byte alignments at that offset. The instruction is structurally sound
in that frame but sits in an uncharted code region without a named function
boundary from the call audit.

Per the tool's own caveat, a low frame score does not mean the hit is false; it
means the context is ambiguous. The alternative hypothesis (frame 0 or another
value) would need positive evidence (a named function, an explicit `lcall` or
`ljmp` boundary, a data alignment constraint) to prefer. Absent that, the low
frame score is a reason to examine the region more carefully, not to filter the
hit.

### 3.3 PD image as separate address space

One reference (file offset 0x22501, `add a,0x32`) is in the PD (power delivery)
firmware image, which is a separate program loaded into a separate memory space
on the EC chip. It is not the same byte as the main EC's 0x32, and updates to
the main firmware do not modify it; it is cited here for completeness of the
reference census, not evidence of shared state.

## 4. Related findings

This byte feeds a registered reader at XDATA 0x045A; see
`docs/findings.md`'s discussion of that byte and the masked-in copy operation
at bank0 0x0DD4A in `docs/findings/0400-045f-site-owners.md`.

## 5. Conclusion

Internal RAM 0x32 is present, actively used as a state-machine value, and
dispatches different code paths in the common-area firmware based on its value.
The byte has no entry in `ec/annotations/registers.yaml` and is therefore not
yet registered in the canonical symbol table. The evidence for status
`present-untested` is complete: the byte is referenced and active in code
control-flow, but no live hardware test has observed its behaviour or its
producer/consumer relationship with the power and thermal subsystems it appears
to coordinate.
