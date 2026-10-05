# What `0xA8`-`0xAF` is, and how the tree came to hold three answers

`0xA8`-`0xAF` is `MOV Rn,direct`, two bytes. This settles it, and the two
things that make it a finding rather than a table tidy-up are the operand byte
(an address, not a constant) and what that does to the PD trampoline's
published destination.

Every number here is read out of files already in this repository. No EC was
opened, no register was read back, no live test ran and none is claimed. The
firmware could still do something else with these bytes; a human at the machine
is what would settle that, and this write-up does not stand in for one.

## The three readings the tree held

Three, and they disagreed about the length and the operand both:

| reading | length | where the tree said so |
|---|---|---|
| `XCH A,Rn` | 1 | `opcode_coverage.MCS51_LEN`, and `opcode-table-coverage.md` |
| `MOV Rn,direct` | 2 | `disasm8051.OPCODE_LEN`, and what `disasm8051.mnemonic()` prints |
| `MOV direct,@Ri` | 2 | `walk_branch_arms._dptr_write()`'s docstring |

`MCS51_LEN` got the block wrong twice, in opposite directions, and both errors
are worth stating because the second is the one that nearly survived. It was
first transcribed with `2` across the block — a byte-for-byte copy of the `0x78`
row (`mov r0,#0x82` as `mov r0,#0x82` meaning a *constant*). That was corrected
to `1` on the reading that the block is `XCH A,Rn`. That instruction is at
`0xC8`-`0xCF`, where the same table still carries its 1 correctly. So the
correction moved the `XCH A,Rn` length onto the wrong row, and `--divergence`
then reported the block as eight rows where the manual contradicts every tool in
the repository.

It does not. `0xA8`-`0xAF` is `MOV Rn,direct` in the MCS-51 map, two bytes, and
the manual's length for it is 2. The disagreement was entirely inside a
hand-transcribed literal.

## Why a fourth decoder would not have settled it

`OPCODE_LEN` *is* a decoder's answer, `MCS51_LEN` is a transcription of a
table, and Ghidra's SLEIGH, r2 and `sdas8051` share a lineage already known to
depart from the manual at `0xA0`/`0xB0`. Their agreement on a row is one decoder
counted twice wherever the shared map departs — which is the whole reason
`opcode_coverage.py` exists, and the reason "all the decoders say two bytes"
would not have been evidence here.

What is left is the corpus, which was produced without reference to any of
these tables. That is what `a8af_operand_role.py` reads:

```
$ python3 ec/tools/a8af_operand_role.py
```

## 1. Framing: two bytes, and the control that shows the check can fail

The listings place the next instruction two bytes on at every instruction start
in the block, and one byte on at none:

```
  0x78-0x7F  MOV Rn,#data    starts=1618  at+1=0     at+2=1613
  0x88-0x8F  MOV direct,Rn   starts=332   at+1=0     at+2=329
  0xA8-0xAF  MOV Rn,direct   starts=416   at+1=0     at+2=416
  0xC8-0xCF  XCH A,Rn        starts=287   at+1=285   at+2=213
```

The `0xC8`-`0xCF` row is the control and it is what makes the other three mean
something: that block *is* one byte in every map, and there the listings do put
a row at `addr+1`. The check discriminates; it is not a check that reads two
bytes and calls it agreement.

A one-byte reading of this block would make its operand byte the next
instruction's opcode, and at 416 sites the listings say it is not.

## 2. The operand byte is an address

The operand bytes are dominated by the SFR addresses 8051 code reaches through
a `direct`, with small internal-RAM cells behind them. Read the operand as a
constant — which a one-byte `XCH A,Rn` forces, and which two tools in this tree
did — and `0x82` and `0x83` become the most frequent opcodes in the image. They
are the opposite:

```
  byte   as operand  as opcode   name
  0x82   91          4           DPL
  0x83   89          4           DPH
  0xf0   33          3810        B
```

`a8af_operand_role.py --self-test` runs this over a fixture built to be framed
one byte on and gets the other answer, so the measurement is known to be able to
fail rather than merely known to have passed.

The control for the same claim: instructions *outside* the block use those exact
addresses as `direct` operands in the forms a compiler emits thousands of times
— `mov 0x82,a`, `mov 0xf0,#imm`, `push 0x83`, `pop 0x82`. So they are addresses
in this firmware's own idiom, not values that happen to sit in an operand column.
The tool restricts that control to opcodes whose operand byte really is a
`direct`, so a `lcall` whose *target* low byte is `0xf0` is not counted as code
addressing `B`.

## 3. Which way the load goes

Two candidates are two bytes; what separates them is whether the direct byte is
a source or a destination. A block instruction whose operand is `0x82`
immediately followed by one whose operand is `0x83`, in consecutive registers,
is the shape of code saving DPTR into a register pair — which is what
`MOV Rn,direct` does and what `MOV direct,@Ri` does not, since the latter stores
*into* an address through a pointer register and produces no such pairing. Both
orders occur, and in both the register numbers step by one;
`a8af_operand_role.py` counts both because the direction is not something the
reading predicts:

```
  bank1   0x8C09  ac 83 (mov r4,DPH)  then  ab 82 (mov r3,DPL)
  bank1   0x8C17  ac 83 (mov r4,DPH)  then  ab 82 (mov r3,DPL)
```

86 sites are of that shape, printed by the same run as the table above. This is
a shape the two candidates predict differently, so it is the part of the case
that distinguishes them; the framing alone does not, since both are two bytes.

## 4. What moved because of it

Correcting the reading is not local to the opcode table. Four consumers named
the block wrongly, and each was carrying a consequence:

**`walk_branch_arms._dptr_write()`** had `0xA8`-`0xAF` in its list of
instructions that *store into* DPL or DPH. Under `MOV Rn,direct` the direct byte
is a source and DPTR is left alone, so every block instruction naming `0x82` or
`0x83` was attributed as a DPTR write it does not perform. That is the issue's
"propagates into DPL/DPH attribution" claim and it was real.

**`pd_inline_arg_sites.py`** rendered the helper's `mov r0,0x82` as
`mov r0,#0x82` and its simulator assigned the operand byte to R0 as a
constant. The tool's own `DEST_LOW = 0x82` says what that constant was *for*: the
published destination was `(caller's DPTR & 0xFF00) | 0x82`, one cell per XDATA
page, the low byte of the caller's own pointer thrown away.

Read as `mov r0,DPL` the helper saves the caller's DPTR into R0 and B and the
`xch` chain puts it back before the store, so the deposit lands on the caller's
own pointer. `--simulate` executes it:

```
  0x104D  mov  r0,0x82        A=0x11 R0=0x98 B=0x33 DPL=0x98 DPH=0x0A  DPTR=0x0A98
  ...
  0x1071  movx @dptr,a        A=0x00 R0=0xAC B=0x3A DPL=0x98 DPH=0x0A  DPTR=0x0A98   <-- store
```

The caller's `mov dptr,#0x0A98` now deposits at `0x0A98` rather than `0x0A82`.
`DEST_LOW` is gone; `pd_inline_arg_dest.py`, which decodes the destination by a
backward walk as an independent check, no longer masks the low byte and agrees.

**The published destination was load-bearing.** It is the `dest` column of
`ec/annotations/pd-inline-arg-sites.csv` and the subject of
`pd-inline-arg-readers.md`, whose written answer was that *nothing reads the
cells the helper fills* — one per page, low byte always `0x82`, nothing
referencing them. That answer was an artifact of the masked address. The cells
are the callers' own DPTRs, they are ordinary registers, and several of them
*are* read by the PD image. `ec/annotations/pd-inline-arg-readers.csv`,
`pd-inline-arg-dest.csv` and the four write-ups that quote them are corrected in
place, with the `??82` figures left visible beside the correction.

**`disasm8051.mnemonic()`** already printed the right length and the right
shape — `mov r0,0x82`, no `#` — and needed only the reasoning beside it.
`OPCODE_LEN` was never wrong about this block and is unchanged.

## What this is not

Static reading of committed files, throughout. The framing half is a
measurement the corpus settles; the name is an inference from it, and the
inference is labelled as one. No hardware was involved and no claim here rests
on behaviour that was observed rather than read.

The one thing the corpus cannot say is what the EC does with these bytes. That
is a question for a human at the machine, and this write-up does not answer it.