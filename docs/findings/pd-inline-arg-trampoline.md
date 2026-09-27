# The PD image's `lcall 0x104D` carries a 4-byte constant inline, deposits it in XDATA, and resumes four bytes on (issue #36)

**Read the headline before anything else.** Everything below is about the
`ITE8850-PD` image at file `0x20000` — a second, self-contained 8051 program
with its own XDATA map. It says **nothing** about the EC's `0x07D0`, which is
the register `ECSpec.cs` names as `ADDR_BATTERY_CHARGE_LIMIT_DOWN` and which
`ec/annotations/ec-0x07d0-sites.md` §6 already rules out of scope for that
reason. `registers.yaml` is untouched by this work and deliberately so: no
register status changed, `0x07D0` keeps `unknown-not-absent` and
`DO-NOT-WRITE-BLIND`, and nothing here is a reason to lift either. All of it
is static analysis of the committed `ec/firmware/GMxMGxx_11.800`. No register
was read back, no write was attempted, nothing ran on the machine.

The convention `ec-0x07d0-sites.md` §5 left open is now established, and the
decoder knows about it. In one line: **`lcall 0x104D` is a 4-byte inline
argument. The four bytes after the call are the argument, they are copied to
XDATA by the helper, and execution resumes at the instruction after them.** What
the constant *means* is a separate question, and §4 records it as far as the
bytes go without naming it.

## 1. Reproducing this

Every figure below comes from one of these, from the repository root:

```console
$ python3 ec/tools/disasm8051.py --self-test
...
self-test passed: both charge-profile-flow.md windows decode identically, all 4 relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode as transcribed

$ python3 ec/tools/pd_inline_arg_sites.py ec/firmware/GMxMGxx_11.800
0x104D is called 458 time(s) in the pd image and 0 time(s) in the main EC,
by a byte scan for `12 10 4d` over the whole dump.
...
$ python3 ec/tools/pd_inline_arg_sites.py ec/firmware/GMxMGxx_11.800 --check
ec/annotations/pd-inline-arg-sites.csv: this run reproduces it byte for byte (459 lines)

$ python3 -m unittest discover -s ec/tools -p test_disasm8051_inline_args.py
Ran 12 tests in 0.07s

OK
```

`--simulate` prints the register transcript §3 quotes and `--pop-order` the
two-orders table it settles the `pop` order with; `--csv` writes
`annotations/pd-inline-arg-sites.csv`, the 458-row census §4 is measured from.

## 2. The two routines

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2104D --runtime 0x104D -n 10
0x104d  a882     mov  r0,0x82
0x104f  8583f0   mov  0xf0,0x83
0x1052  d083     pop  0x83
0x1054  d082     pop  0x82
0x1056  121064   lcall 0x1064
0x1059  121064   lcall 0x1064
0x105c  121064   lcall 0x1064
0x105f  121064   lcall 0x1064
0x1062  e4       clr  a
0x1063  73       jmp  @a+dptr

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x21064 --runtime 0x1064 -n 18
0x1064  e4       clr  a
0x1065  93       movc a,@a+dptr
0x1066  a3       inc  dptr
0x1067  c583     xch  a,0x83
0x1069  c5f0     xch  a,0xf0
0x106b  c583     xch  a,0x83
0x106d  c8       xch  a,r0
0x106e  c582     xch  a,0x82
0x1070  c8       xch  a,r0
0x1071  f0       movx @dptr,a
0x1072  a3       inc  dptr
0x1073  c583     xch  a,0x83
0x1075  c5f0     xch  a,0xf0
0x1077  c583     xch  a,0x83
0x1079  c8       xch  a,r0
0x107a  c582     xch  a,0x82
0x107c  c8       xch  a,r0
0x107d  22       ret
```

`0x104D` saves one half of the caller's DPTR, takes its own return address off
the stack, calls `0x1064` four times, and tail-jumps. `0x1064` is one byte out
of the code stream (`movc a,@a+dptr`), an `xch` chain, and a `movx @dptr,a`.

**The first row is a trap, and it is the reason the decoder's own output is
quoted rather than trusted here.** `a8 82` is opcode `A8`, which is
`MOV Rn,#data8` — so the instruction is `MOV R0,#0x82`, loading a *constant*,
not `MOV R0,direct` copying the caller's DPL. `disasm8051` renders that family
without the `#` (its `0x78`-`0x7F` sibling does print one, so the two rows of
the same instruction disagree), which reads exactly like a register-to-register
move. §6 records this as an open question; the mechanism below does not depend
on fixing it, because the constant reading is the one the simulation bears out
and the register reading does not.

**A hand-trace of the `xch` chain gives the wrong answer, and that is worth
saying plainly.** The six `xch`s are a 4-cycle rotation: read as
`(A, DPH, DPL, B, R0)` in and `(A, B, DPL, R0, DPH)` out, so `A` comes back
unchanged and the other four have been permuted. Following them one instruction
at a time loses the thread — the first draft of this file claimed the chain
stores zero, which it does if and only if you read the `mov r0,#0x82` as a
register copy. Hence the simulation.

## 3. The simulation, which is what the claim rests on

`pd_inline_arg_sites.py --simulate` executes both routines over the committed
bytes with concrete register values. It is entered at PD runtime `0x3AA8`,
whose four bytes are `00 00 00 01` and whose resume point holds `90 07 d0`; the
caller's `A`, `R0` and `B` are given deliberately impossible values (`0x11`,
`0x22`, `0x33`) so the transcript shows they do not survive. The first call of
`0x1064` and the closing tail call, abridged:

```console
$ python3 ec/tools/pd_inline_arg_sites.py ec/firmware/GMxMGxx_11.800 --simulate
0x104D entered with the caller's DPTR = 0x0A98 (its `mov dptr,#0x0A98` at 0x3AA5) and a return address of 0x3AAB.

  0x104D  mov  r0,#0x82       A=0x11 R0=0x82 B=0x33 DPL=0x98 DPH=0x0A  DPTR=0x0A98
  0x104F  mov  0xf0,0x83      A=0x11 R0=0x82 B=0x0A DPL=0x98 DPH=0x0A  DPTR=0x0A98
  0x1052  pop  0x83           A=0x11 R0=0x82 B=0x0A DPL=0x98 DPH=0x3A  DPTR=0x3A98
  0x1054  pop  0x82           A=0x11 R0=0x82 B=0x0A DPL=0xAB DPH=0x3A  DPTR=0x3AAB
  0x1056  lcall 0x1064        A=0x11 R0=0x82 B=0x0A DPL=0xAB DPH=0x3A  DPTR=0x3AAB
    0x1064  clr  a            A=0x00 R0=0x82 B=0x0A DPL=0xAB DPH=0x3A  DPTR=0x3AAB
    0x1065  movc a,@a+dptr    A=0x00 R0=0x82 B=0x0A DPL=0xAB DPH=0x3A  DPTR=0x3AAB
    0x1066  inc  dptr         A=0x00 R0=0x82 B=0x0A DPL=0xAC DPH=0x3A  DPTR=0x3AAC
    0x1067  xch  a,0x83       A=0x3A R0=0x82 B=0x0A DPL=0xAC DPH=0x00  DPTR=0x00AC
    0x1069  xch  a,0xf0       A=0x0A R0=0x82 B=0x3A DPL=0xAC DPH=0x00  DPTR=0x00AC
    0x106B  xch  a,0x83       A=0x00 R0=0x82 B=0x3A DPL=0xAC DPH=0x0A  DPTR=0x0AAC
    0x106D  xch  a,r0         A=0x82 R0=0x00 B=0x3A DPL=0xAC DPH=0x0A  DPTR=0x0AAC
    0x106E  xch  a,0x82       A=0xAC R0=0x00 B=0x3A DPL=0x82 DPH=0x0A  DPTR=0x0A82
    0x1070  xch  a,r0         A=0x00 R0=0xAC B=0x3A DPL=0x82 DPH=0x0A  DPTR=0x0A82
    0x1071  movx @dptr,a      A=0x00 R0=0xAC B=0x3A DPL=0x82 DPH=0x0A  DPTR=0x0A82   <-- store
    ... the same three calls, each depositing one byte further up 0x0A8x ...
  0x1062  clr  a            A=0x00 R0=0x86 B=0x0A DPL=0xAF DPH=0x3A  DPTR=0x3AAF
  0x1063  jmp  @a+dptr      A=0x00 R0=0x86 B=0x0A DPL=0xAF DPH=0x3A  DPTR=0x3AAF

  XDATA written:
    0x0A82 <- 0x00
    0x0A83 <- 0x00
    0x0A84 <- 0x00
    0x0A85 <- 0x01
  `clr a ; jmp @a+dptr` then transfers to 0x3AAF, where the byte is 0x90
```

Four things fall out of that, and each is a claim about the mechanism rather
than about any one site:

- **The four bytes are the four code bytes at the return address**, in order.
  `CODE[ret+0..ret+3]` → `XDATA[…]` above, `00 00 00 01` in, `00 00 00 01`
  out.
- **The destination is the caller's DPTR *high* byte with the literal `0x82` as
  its low byte.** The caller loaded `0x0A98`; the store lands at `0x0A82`. The
  caller's own DPL (`0x98`) never reaches the store — `R0` is overwritten with
  the constant `0x82` at `0x104D` before anything reads it, and the `xch` chain
  puts `R0` into `DPL`. **This is the direct answer to "what the callee does
  with `R0`/`B` which `0x104D` saves on entry": `R0` is not used to save
  anything, and only the high half survives, in `B`, which is where the
  destination's high byte comes from.** On return `B` still holds it and `R0`
  holds `0x85`.
- **The tail call dispatches on nothing.** `clr a` immediately precedes
  `jmp @a+dptr`, so it jumps to `DPTR` alone — and `DPTR` is the return address
  plus 4, because each of the four `0x1064` calls leaves it one byte further
  on. It is a tail call back into the caller, four bytes past the `lcall`.
- **The caller's `A` does not survive**, which is what the `0x11` above shows
  and is worth knowing before anyone reads an `A`-bearing convention into this.

### Both readings of the two `pop`s are measured; which one this firmware
uses is inferred from that comparison, and it is the one place this image
contradicts the manual

The MCS-51 `lcall` pushes the return address high byte first, so the low byte
is on top of the stack and `pop 0x83` (DPH) at `0x1052` would take the **low**
byte — leaving `DPTR` holding the *byte-swapped* return address, `0xAB3A` for
this site. The image says otherwise, and the whole comparison is short enough
to put in the file:

```console
$ python3 ec/tools/pd_inline_arg_sites.py ec/firmware/GMxMGxx_11.800 --pop-order
Both readings of the two `pop`s at 0x1052/0x1054, over the 458 sites,
with nothing else changed.  The left-hand column is the one `census()`
and the committed `inline` column follow; adopting it over the other is
the write-up's inference from this table, not this tool's finding.

                                              return address    byte-swapped
distinct four-byte values over 458                        40             427
most common value                                00 00 00 00     ff ff ff ff
its multiplicity                                         186               9
0x07D0 rows a resume lands on, of 254                     68               4
call sites whose resume lands on one, of 458              68               4

The last two rows are one figure counted twice, over two populations that are
not the same size: no two calls resume at the same address under either
reading, so `68 of 254` and `68 of 458` agree, and the `4` is four of the 458
calls.  Reading it as four of the 254 `0x07D0` rows would be borrowing a
denominator that is not its own, which is why both are printed.

0 of 458 read outside the dump under one of the two readings, so
every figure above is over the whole population.  A non-zero count would
leave those sites out, which is 'not found by this method' and not 'there
is none'.
```

**What the scan measures is the comparison; adopting the left-hand column is
the inference.** The two readings differ in nothing but which address the four
bytes are read from, so every figure that moves between them is the order and
nothing else. A firmware that put a four-byte constant inline would have no
reason to make the byte-scrambled addresses it would then have to copy from hold
an enumerated set, and 427 distinct values led by `ff ff ff ff` is what
scrambled reads look like where 40 led by `00 00 00 00` ×186 is what an
enumerated set looks like. `--simulate` above runs the same two orders through
the two routines for one site, so both the mechanism and the comparison behind
this are things a reader can reproduce rather than claims about the manual.

The mechanism above — the destination, the four-byte width, and the +4 resume —
is **independent of the order**: none of `B`, the `0x82` constant or the four
`lcall`s touches the stack. Only *which* code bytes get copied depends on it,
and the evidence above is what fixes that. **Why this firmware behaves so is
not established here**, and a one-line note on a compiler's push order is the
obvious place to look next.

## 4. The four bytes: an enumerated set of 32-bit constants, not a per-site
packed immediate

`annotations/pd-inline-arg-sites.csv` is the whole population — 458 rows, one per
call, with the four bytes, the value they spell, the resume address, and the
destination. `pd_inline_arg_sites.py` summarises it:

```console
$ python3 ec/tools/pd_inline_arg_sites.py ec/firmware/GMxMGxx_11.800
The 40 distinct four-byte arguments, most common first; the value is
read big-endian, in the order the helper copies them:
32 of the 40 are zero in both high bytes.

   186  00 00 00 00   0x00000000 = 0
   152  00 00 00 01   0x00000001 = 1
    15  00 00 03 20   0x00000320 = 800
    13  00 00 07 01   0x00000701 = 1793
     9  00 00 00 18   0x00000018 = 24
     9  00 00 00 02   0x00000002 = 2
     7  00 00 13 88   0x00001388 = 5000
     7  ff ff ff ff   0xFFFFFFFF = 4294967295
     6  00 00 00 1e   0x0000001E = 30
     4  00 00 00 64   0x00000064 = 100
   ... 30 more, down to one site each ...
```

That is the issue's either/or answered with a denominator. **Constant? No —
40 distinct values. Per-site packed immediates? No — 338 of the 458 sites use
one of the two commonest. An enumerated set of 32-bit constants: yes, and
mostly small ones** (0, 1, 2, 4, 10, 24, 25, 30, 40, 50, 60, 64, 100, 110, 120,
125, 128, 400, 410, 480, 650, 800, 920, 1000, 1793, 2000, 2048, 4096, 4600,
5000, …), read big-endian because the first byte deposited is the first byte
of the number. Round decimal values are what an interval or a count looks like
and I am **not** naming one: nothing here says milliseconds, retries, or
anything else, and §4 of `ec-0x07d0-sites.md` is right to stop where it did.
Eight values have a non-zero second byte (`00 01 00 00`, `00 04 00 00`,
`00 08 00 00`, …) and one is `0xFFFF0000`; the set is not uniformly small and
this file does not pretend otherwise.

**Over the 68 sites the `0x07D0` table cares about, 8 distinct values:**

```console
    38  00 00 00 01   0x00000001 = 1
    21  00 00 00 00   0x00000000 = 0
     3  00 00 00 1e   0x0000001E = 30
     2  00 00 03 20   0x00000320 = 800
     1  00 00 00 28   0x00000028 = 40
     1  00 00 00 78   0x00000078 = 120
     1  00 00 07 01   0x00000701 = 1793
     1  00 00 00 0a   0x0000000A = 10
```

**A correction to the count this issue was filed with, and to the "unexplained
coincidence" it flagged.** The issue recorded that all eight tuples end in
`0x90`, that `0x90` is also the opcode of the `mov dptr,#imm16` that resumes
one byte later, and that the coincidence was unexplained. It is not a
coincidence in the image: **the quadruple had been read starting one byte too
late.** The recorded tuples, `00 00 01 90` (38) and `00 00 00 90` (21), are
these eight shifted right by one byte, and the `0x90` in last position is the
resume instruction's own opcode, swept into the sample. Shift them back and the
multiplicities are identical — 38 and 21 — which is how the misreading can be
seen to be a byte alignment rather than a disagreement about the data. The
unexplained coincidence is resolved: there was nothing in the image to explain.

`ec-0x07d1-sites.md`'s own table of four `0x07D1` sites and their inline bytes
was read correctly and is reproduced exactly by the census, which is an
independent check on this section.

### Sampled call sites, across pages

Three of the 68, one per 4 KiB page, all reproduced with
`disasm8051.py --at <file> --runtime <addr>`:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x250A6 --runtime 0x50A6 -n 7
0x50a6  12104d   lcall 0x104d
0x50a9  00000001 inline args: 00 00 00 01
0x50ad  9007d0   mov  dptr,#0x07d0
0x50b0  e0       movx a,@dptr
0x50b1  ff       mov  r7,a
0x50b2  802c     sjmp 0x50e0
0x50b4  900a98   mov  dptr,#0x0a98
0x50b7  12104d   lcall 0x104d
0x50ba  00000001 inline args: 00 00 00 01

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x283FD --runtime 0x83FD -n 7
0x83fd  12104d   lcall 0x104d
0x8400  00000000 inline args: 00 00 00 00
0x8404  9007d0   mov  dptr,#0x07d0
0x8407  12388d   lcall 0x388d
0x840a  127ce0   lcall 0x7ce0
0x840d  900a8f   mov  dptr,#0x0a8f
0x8410  12104d   lcall 0x104d
0x8413  00000000 inline args: 00 00 00 00
0x8417  9007d0   mov  dptr,#0x07d0
```

`0x934D` is worth one more look, because its `mov dptr` is *not* the
instruction immediately before the call — the `dptr_gap` column is 12 there,
against 3 for most sites, which is what a weak reading of that column looks
like and why the column exists:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2934D --runtime 0x934D -n 7
0x934d  12104d   lcall 0x104d
0x9350  00000000 inline args: 00 00 00 00
0x9354  9007d0   mov  dptr,#0x07d0
0x9357  e0       movx a,@dptr
0x9358  fa       mov  r2,a
0x9359  12351a   lcall 0x351a
0x935c  1210bc   lcall 0x10bc
0x935f  ea       mov  a,r2
```

`0x10BC` is the Keil index helper `ec-0x07d0-sites.md` §4 decoded, so the byte
read at `0x07D0` goes on to scale an index. The deposit at `0x0782` is a
*separate* thing, one instruction block away, and nothing here claims the two
are connected.

## 5. Where the bytes are deposited, and how firmly that is known

`annotations/pd-inline-arg-sites.csv`'s `dest` column is **derived, not
measured**, and the column next to it says how firmly. `dptr_load` is the
nearest preceding `90 xx xx` **byte pattern** within 32 bytes, found by scanning
backwards; it cannot tell a `mov dptr,#imm16` from the same three bytes inside
another instruction. `dptr_gap` is the distance, so a gap of 3 — the minimum
possible, the `mov dptr` being the instruction immediately before the call — is
a strong reading and a gap of 20 is a weak one. 64 of the 458 have no such
pattern in range and read **empty, which is "not found by this scan" and not
"there is none"**.

The distribution is small and page-shaped, which is what the §3 mechanism
predicts: `0x0A82` (174), `0x0782` (107), `0x0882` (92), `0x0482` (7),
`0xFF82` (7), `0x0082` (3). Every one of them is `??82` with the high byte
taken from the caller's `DPH` — so the destination is one scratch cell per XDATA
page the callers' DPTRs fall in. **What reads those cells was not traced**, and
this file does not claim the `0x82` offset is a per-page scratch cell rather
than part of a wider structure; it is a fixed literal in the instruction, and
that is as far as the decode goes.

## 6. What changed in the tools, and the counts

`disasm8051.INLINE_ARG_CALLS` is a one-entry named table, `{0x104D: 4}`,
consulted by `decode()`, by `converges_from()`, and by
`trace_xdata_refs.walk_why()`. It is keyed on the **decoded instruction** —
opcode `0x12` with that target — not on a runtime-address range, so the same
test works in all three and `converges_from()`, which is handed a bare file
offset with no region knowledge, needs no plumbing. It is a named entry and
**not** a general "inline arguments" heuristic: a heuristic guessing at argument
blocks would be unfalsifiable, and this is a byte-exact claim about one address.

The idiom occurs **458 times in the PD image and 0 times in the main EC**, and
that zero is the safety argument for keying on the call rather than on a range —
it is what makes the special case inert for every committed main-EC listing the
decompile pipeline exports. `test_disasm8051_inline_args.py` pins it against the
committed image, so a different dump turns the argument red rather than
silently re-framing the other program. `--self-test` still passes, and it
decodes **EC** bank-0, so it is also the gate that would catch a special case
leaking across programs.

The transcript `ec-0x07d0-sites.md` §5 shows as a failure, corrected:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x23AA8 --runtime 0x3AA8 -n 4
0x3aa8  12104d   lcall 0x104d
0x3aab  00000001 inline args: 00 00 00 01
0x3aaf  9007d0   mov  dptr,#0x07d0
0x3ab2  e0       movx a,@dptr
0x3ab3  ff       mov  r7,a
```

Three `nop`s become the argument block, and the walk resumes on the
`mov dptr,#0x07d0` the site actually is.

### The framing counts

| table | rows moved | `frame_onto == 0` before | after |
|---|---|---|---|
| `ec-0x07d0-sites.csv` | 46 of 254 | 45 | **3** |
| `ec-07d6-07d7-sites.csv` | 9 of 213 | 9 | **0** |
| `ec-0x07d1-sites.csv` | 4 of 76 | 4 | **0** |

**The three that remain unsynced in the `0x07D0` table are named, not rounded
away: `0x3A81`, `0x4869` and `0x83E2`.** They are the address-table case
`ec-0x07d0-sites.md` §5 already identified — four-byte entries whose first
halves are code addresses, the last of them the site's own runtime address — a
different mechanism, and fixing them is not this issue's work.

Only `frame_onto`/`frame_over` moved. No `access`, `window` or `terminator` cell
in any of the three changed, which is what the plan required and what confirms
the forward walk was not disturbed: `walk_why()` stops at the first flow opcode
and this call *is* one, so no window crosses an argument block. The
`inline_arg_len()` call in `walk_why()` is a latent guard, not a live fix, and
is commented as such — the same way `verify_reassembly.BIT_UNSUPPORTED` calls
its `0xC1` hole. Every other committed `frame_onto` table was swept by the same
measurement and **none** of them moves: 0 changed rows across `bank-call-targets`,
`bank-paged-call-targets`, `bank-relative-branch-targets`, `ec-07c4-07d5-sites`,
`ec-09e9-09eb-sites`, `manual-fan-ctrl-0751-sites`, `xdata-0400-045f-sites`,
`xdata-086x-dispatch-sites`, `xdata-1c3x-consumers-sites`, `index-table-spans`,
`pd-index-accesses` and `pd-index-callers` — about 20,000 rows, all inert, and
not all of them EC-side: `ec-07c4-07d5-sites` carries 102 `pd-image` rows,
`xdata-0400-045f-sites` 100, `xdata-086x-dispatch-sites` 12, and the two
`pd-index-` tables are PD-side by construction. The 0 is what was measured; the
region is not what makes it, and the earlier "all EC-side" is dropped for that
reason.

## 7. What this does not establish

- **Nothing about the EC's `0x07D0`.** See the header. The 68 sites are a
  different program's variable.
- **Nothing observed on hardware.** No register was read back, no write was
  attempted, nothing was run on the machine. Static analysis of a committed
  image, and that is all it is.
- **Not what the constant means.** §4 stops at the enumeration. A round decimal
  value is not a named unit, and this file does not supply one.
- **Not why the two `pop`s deliver high byte first.** §3 measures the order and
  leaves the cause open.
- **Not who reads the deposited cells.** §5 has the destinations and the
  strength of each reading, and no consumer.
- **No control-flow recovery.** `disasm8051.py` decodes linearly and stops at
  the first branch; the census counts *static* sites and says nothing about
  which execute, how often, or in what order. Whether some of the 458 sit in
  the same function is not determined — that needs a recursive disassembly the
  repository has deliberately not attempted (`ec/README.md`, "toolchain proven,
  not attempted"). This file does not drift into implying otherwise.
- **The census does not generalise from 68 to 458.** It covers every
  `lcall 0x104D` in the PD image and nothing else; the 390 sites not adjacent
  to a `0x07D0` reference are in the table and are uncharacterised.
- **A zero is "not found by this method".** The EC count is zero by byte scan
  for `12 10 4d`; a call to the same helper spelled some other way would not be
  found, exactly as `docs/findings.md` §4c requires this repository to say.

## 8. Open questions, for whoever picks these up

1. **The `MOV Rn,#data8` rendering.** `disasm8051` prints `mov r0,0x82` for
   `a8 82`, with no `#`, while its `0x78`-`0x7F` sibling prints one — so the
   same instruction is rendered two ways in one table, and the missing `#` is
   what makes `MOV R0,#0x82` read as a register copy. Fixing it means editing
   two committed transcripts (`docs/findings/reset-vector-dptr-targets.md:73`,
   and the `0x104D` listing in `ec-0x07d0-sites.md` §5), which is why it was
   not done inside this issue.
2. **The same table's `0x91`-`0x9F` range.** `0x91`-`0x9F` is `MOV Rn,direct`
   and is not in the mnemonic table; `0x91` currently falls through to `acall`
   and `0x98`-`0x9F` to `subb a,rn`. Noted here because it was found while
   reading the `90 xx xx` scan's neighbourhood and not acted on — a separate
   issue, with its own oracle work.
3. **Why the two `pop`s deliver high byte first** (§3).
4. **The consumer of the `??82` cells** (§5), and whether the 32-byte
   `dptr_load` scan can be replaced by a real backward decode for the 64 sites
   it misses.
5. **The three remaining `0x07D0` sites** (`0x3A81`, `0x4869`, `0x83E2`) — the
   address-table idiom, named and not fixed.
