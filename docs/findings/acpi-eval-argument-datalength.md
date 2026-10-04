# The `0x00040000` in `ACPIDriver.sys`'s argument headers is `DataLength = 4`, and it survives

`windows/native/ACPIDriver.sys.analysis.md` and the generated
`windows/decompiled/native/ACPIDriver.c` disagree about how many bytes one
`mov` in `ACPIDriver.sys`'s `MMRD` handler occupies. The hand walk says two
adjacent dwords; the generated C emits a single `CONCAT` that swallows the
constant and the four address bytes into one value. Which is right decides
whether the field the constant occupies is the argument's length or something
else, and it is settled below from the `.asm` rather than from either rendering.

**Nothing here is evidence about the machine.** No driver was loaded, no IOCTL
was issued, no EC register was read. Everything is a static read of
`windows/decompiled/native/ACPIDriver.asm`, which is generated from the
committed vendor binary and not hand-edited. What `ACPI.sys` makes of the
length is *not* settled here, and the closing section says why.

`windows/tools/acpi_eval_arg_slots.py` prints the table this write-up embeds,
by parsing that listing; the sections below quote VAs so a reader can check any
line of it against the `.asm` without running anything.

## The slot arithmetic: two adjacent dwords, and the constant survives

`MMRD`'s handler (`FUN_1400015ec`) writes its argument header at
`0x140001619`. (The `-` fillers below are the listing's padding for an
instruction shorter than its byte column; every mnemonic, operand and VA is
the committed line.)

```
140001619 48 c7 44 24 60 00 00 04 00   mov      qword ptr [RSP + 0x60], 0x40000
```

That is an **eight-byte** store. It writes `0x60`-`0x67`: `0x00040000` into
`0x60`-`0x63` and zero into `0x64`-`0x67`. The four byte stores that follow put
the address into `0x64`-`0x67` —

```
140001652 88 44 24 64      mov      byte ptr [RSP + 0x64], AL
140001659 88 44 24 65      mov      byte ptr [RSP + 0x65], AL
140001660 88 44 24 66      mov      byte ptr [RSP + 0x66], AL
140001667 88 44 24 67      mov      byte ptr [RSP + 0x67], AL
```

— which is the **upper half of that same store**. Nothing after them writes
`0x60`-`0x63`, and no later instruction in the function does either. So:

- `0x60` and `0x64` are **two adjacent dwords**, not one.
- The `0x40000` **survives**; the byte stores land beside it, not over it.

The analysis file's hand walk was right and its listing comment — "the
argument's first dword" — describes what is there. The generated
`ACPIDriver.c`'s single `CONCAT17` is a decompiler rendering, not a competing
layout. Ghidra registered the split and then lost it in the expression: the
same function declares `uStack_424`-`uStack_421` as separate storage for the
four bytes at `0x64`-`0x67`, and writes the merged eight-byte object as
`_local_428` with the leading underscore Ghidra uses for a stack object it does
not consider fully defined.

The same shape appears in `FUN_140001508` (`MMRB`) and the other read handlers,
so this is the driver's idiom and not one routine's accident.

## The field: `Argument[i].DataLength`, value 4

The buffer base is `0x50(%rsp)` and its header fields are stored one at a time —
`0x50` Signature, `0x54` MethodName, `0x58` Size `0x28`, `0x5c` ArgumentCount —
so the argument array begins at `0x60`. Two independent things in the driver's
own code fix the per-argument layout.

**The stride is eight bytes.** `T1WR` (`FUN_140002614`) writes three arguments
at `0x60`, `0x68` and `0x70`, with `ArgumentCount = 3` at `0x140002664`. Three
slots in the space of three strides is an eight-byte argument.

**The two header fields are 16-bit at `+0` and `+2`.** That is the only parse
under which the analysis file's existing reading of `SMRW`'s
`mov dword ptr [RSP + 0x60], 0x800002` at `0x140001B41` as *Type = 2,
DataLength = 0x80* is self-consistent, and `SMRW` reads the field back at that
width on its own, well after storing it:

```
140001CB0 44 0f b7 4c 24 62   movzx    R9D, word ptr [RSP + 0x62]
140001CBB 44 89 4c 24 28      mov      dword ptr [RSP + 0x28], R9D
```

— a **word** read at the slot's `+2`, handed to the eval call `FUN_140001e88`
at `0x140001CDA` as `R9`. Nothing between the `0x140001B41` store and that read
rewrites those two bytes: the `memcpy_s` at `0x140001B50` writes from `+4`
upward, not below it. So this is the handler reading back the value it just
stored, and it reads it as a word — a dword-wide field would be read as a
dword. `T3WR` has the same pair at `0x140002A40` and `0x140002A46`.

That the `+2` field is a *length* rather than some other 16-bit value is a
second thing, and a value comparison rather than a dataflow. `0x800002`
little-endian puts `0x0080` at `+2`, and the count `SMRW` passes to `memcpy_s`
is `lea EDX, [R15 + 0x7e]` at `0x140001B49` — `R15D` being `2` at
`0x140001B1B` — which is that same `0x80`. The two are computed separately and
nothing copies one into the other; their agreeing is what makes `DataLength`
the reading and not only the width.

`0x00040000` little-endian is the bytes `00 00 04 00`, so the field at `+0` is
`0` and the field at `+2` is **`DataLength = 4`**. The four address bytes land
in the payload at `+4`. That is the whole of it: the constant states the length
of the payload that follows it, and it matches what the handler goes on to
store.

**It is not the width of the access.** `MMWB`'s ASL is
`MMRW (Arg0, One, Zero, Arg1)` — a byte write — and it still states
`DataLength = 4` for that argument, because the payload is four bytes wide
whatever the EC access does with it. `IORD` is the converse case: its ASL
opens a 4-byte region and reads 32 bits, and its argument is also four bytes,
so the two are not separable from one example and both are stated here.

## The table

The constant appears once per argument whose `DataLength` the driver hardcodes
as 4. That is a count of **arguments**, not of handlers, which is what makes the
two asymmetries the issue asked about legible: `T1WR` and `T2WR` have three
arguments each and so three constants, while `MMWB` — arity 2 — has one,
because its second argument's header comes from a register rather than a
literal.

`python3 windows/tools/acpi_eval_arg_slots.py` prints this from the committed
listing:

| Handler | Method | `ArgumentCount` | Slots stating the length of 4 | Slots stating `Type = 2` | Slots zeroed |
| --- | --- | --- | --- | --- | --- |
| `FUN_140001334` | `IORD` | 1 | 1 | — | — |
| `FUN_140001508` | `MMRB` | 1 | 1 | — | — |
| `FUN_1400015ec` | `MMRD` | 1 | 1 | — | — |
| `FUN_1400016e4` | `PCRD` | 1 | 1 | — | — |
| `FUN_1400017dc` | `T1RD` | 1 | 1 | — | — |
| `FUN_1400018d4` | `T2RD` | 1 | 1 | — | — |
| `FUN_1400019cc` | `T3RD` | 1 | 1 | — | — |
| `FUN_140002118` | `IOWD` | 2 | 2 | — | — |
| `FUN_140002308` | `MMWB` | 2 | 1 | — | 1 |
| `FUN_1400023fc` | `MMWD` | 2 | 2 | — | — |
| `FUN_140002508` | `PCWD` | 2 | 2 | — | — |
| `FUN_140002614` | `T1WR` | 3 | 3 | — | — |
| `FUN_140002748` | `T2WR` | 3 | 3 | — | — |
| `FUN_140001ac4` | `SMRW` | 1 | — | 1 | — |
| `FUN_14000287c` | `T3WR` | 1 | — | 1 | — |
| `FUN_1400010f8` | `RCMS` | 2 | — | — | 2 |
| `FUN_14000125c` | `ECRR` | 1 | — | — | 1 |
| `FUN_14000142c` | `RIOP` | 2 | — | — | 2 |
| `FUN_140001f54` | `WCMS` | 3 | — | — | 3 |
| `FUN_140002038` | `ECRW` | 2 | — | — | 2 |
| `FUN_140002224` | `WIOP` | 3 | — | — | 3 |

The rule is one per argument with a **literal** 4, not one per argument. Three
of the shapes above are worth naming because the arithmetic alone does not
distinguish them.

**`MMWB` is the exception the issue did not flag.** ASL arity 2, and
`ArgumentCount = 2` at `0x140002359`, but one constant: its second argument's
header comes from a register —

```
14000238D 89 7c 24 68      mov      dword ptr [RSP + 0x68], EDI
```

— the `EDI` that `xor EDI, EDI` at `0x140002335` cleared, so it declares a
length of 0 over a single payload byte at `0x140002395`. `MMWB` is in the
constant set and the zeroed set at once, and that overlap is the finding rather
than an inconsistency in either column.

**`MMWD`, the 32-bit write, does share the constant** — at `0x14000242A` and
`0x14000247F`, one per argument. So the constant is not the access width, as
`MMWB` above also shows, and it is not confined to reads.

**`T3WR`'s absence is not an outlier.** `FUN_14000287c` stores
`mov dword ptr [RSP + 0x60], 0x800002` at `0x1400028DD`, zeros the payload
with `and dword ptr [RSP + 0x64], 0x0` at `0x1400028B2`, and `memcpy`s `0x80`
bytes into `lea RCX, [RSP + 0x64]` at `0x1400028B7`. It is a **buffer** handler
with `ArgumentCount = 1`, the same shape as `SMRW`, so it has no four-byte
scalar argument to declare a length for. The constant's absence there is a
consequence of the argument kind, not an omission — and that is a reading of
these two routines' code, not a claim about anything the listing does not show.

## The `ECRR` contrast

`ECRR` zeroes the whole eight bytes —
`mov qword ptr [RSP + 0x60], RSI` at `0x14000128A`, on the register `xor ESI,
ESI` cleared at `0x140001288` — so it declares `DataLength = 0` and then
supplies two payload bytes at `0x1400012BB` and `0x1400012C2`. `ECRW`
(`FUN_140002038`) is the same in both its slots. Where `MMRD` declares a length
of 4 and supplies four bytes, `ECRR` declares zero and supplies two.

That is a real structural difference between the two families, and it is now
recorded beside the IOCTL table in `windows/native/ACPIDriver.sys.analysis.md`
rather than left in a paragraph about `MMRD`.

## Why `ecrw.py` does not change

The issue asks which reading decides whether `Ec.read_dword` puts
`EC_BASE + addr` on the wire intact. **Neither does.** Under both readings the
four byte stores copy `SystemBuffer[0..3]` to `0x64`-`0x67` in order, so
`Ec.read_dword`'s little-endian `EC_BASE + addr` is intact either way, and
issue #147's central claim stands unaltered. Saying so is the point of this
section: it is what stops the next reader from "correcting" a tool that was
never wrong.

## What is not settled here

**What `ACPI.sys` requires of the field.** The identification above is made
from the driver's own code — its own read-back at `0x140001CB0`, its own
argument stride, its own payload widths. It says what the driver *states*, not
what the operating system does with the statement, and nothing here says the
constant is required, nor that `ECRR`'s zero is wrong.
`docs/findings/acpi-interpreter-region-access.md` records that the struct
itself, Microsoft's `ACPI_METHOD_ARGUMENT_V1`, is not committed to this tree;
settling the far side of the boundary would mean going to it, which is not a
question this binary can answer.

**Whether `T3WR`'s argument kind is a defect.** Its handler sends
`ArgumentCount = 1` with a `0x80`-byte buffer, while the committed ASL declares
`Method (T3WR, 3, NotSerialized)` (`evidence/acpi/dsdt.dsl`) whose body uses
only `Arg0`. That is an argument-kind mismatch worth a look, and it is recorded
here as an observation with the question named — not as a defect, and not
settled by this change. `SMRW` is the other buffer handler and does *not* share
it: its declared arity of 1 matches the single argument its handler sends, so
`T3WR` is the odd one of the pair rather than the shape they both have.

**The census is over this listing.** Every handler named above is one the
committed `.asm` contains. A handler the exporter did not emit would be
invisible to both this write-up and the tool, which is the same blind spot
`ec/tools/scan_refs.py` documents for its own scan.

## What this unblocks

Nothing in the EC or the BIOS. What it settles is the marshalling contract
`windows/tools/ecrw.py` marshals against — the layer between a user's IOCTL and
`\Driver\ACPI` — and it removes a reading of `MMRD` under which that tool's
byte order would have had to be re-derived. `MMRD`/`MMWD` having no
`ACPIDriverDll.dll` export is still the open question the analysis file names,
and a caller for them, if one exists, marshals against the layout settled here.