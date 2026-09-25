# The call-graph tranche's twelve `unresolved` rows, retyped from their bytes (issue #456)

Issue #134's tranche left twelve of its 44 rows at `type=unresolved`, and
`../../ec/annotations/call-graph.md` said so and stopped. Five of the twelve
carried a specific reason — "the boundary is a hypothesis from the call-target
byte scan, so this may be the start of straight-line code" — one (`bank0 0x9C47`)
carried a question only its callers could answer, and six were declined as too
large for a first reading pass. This file is the reading of all twelve, the
decisions behind it, and the four places the previous text did not survive the
bytes.

**Every figure here is re-derivable from committed inputs with a command named
beside it.** Nothing is a behavioural claim. No register `status:` changed, no
`registers.yaml` row was added, `../../ec/ghidra/xdata-symbols.csv` is untouched,
and no live test ran: all twelve are static readings of committed bytes, and
where a row would need a machine to go further it says so.

**The result in one line: all twelve now have a `type:` their bytes support, and
the record count did not move — 1,877 before and 1,877 after, because none of
the five boundary addresses needed the new entry the issue anticipated.**

## The five boundary rows: all five are real entries, and the split is after the entry

The issue's premise was that a boundary that cuts through straight-line code
means the address is a fragment and the real entry is somewhere earlier. **The
committed image says otherwise for all five, and the way to see it is to ask what
`ec/decompiled/index.csv` records as each function's size and what sits in the
gap immediately after it.**

| address | index size | the next index row | that row's size |
|---|---|---|---|
| `bank0 0xD2BE` | 1 | — (the `ret` is the last byte) | — |
| `common 0x4A76` | 1 | `common 0x4A77` | 12 |
| `common 0x3B4E` | 3 | `common 0x3B51` | 15 |
| `common 0x7177` | 4 | `common 0x717B` | 2 |
| `common 0x0200` | 19 | `common 0x0213` | 136 |
| `bank0 0x9C47` | 1 | — (the `ret` is the last byte) | — |

So the hypothesis was right about the shape and wrong about the direction. In
each case **the transfer targets the annotated address, the routine runs on past
it, and Ghidra's function stops at the annotated address because a second
function begins there.** The entry is real; the export is a window. That is the
same situation `bank0 0x93FE` (`load_r7_into_a`) has always been in — "the
listing holds one instruction, `mov A, R7`, with no `ret`, so control falls
straight into 0x93FF, whose own listing continues the routine" — and the house
already handles it by saying so.

### What settles it is the caller side, not the boundary

A boundary is a hypothesis; a caller that treats the address as a function is
evidence. Three of the five have it outright.

**`common 0x4A76`.** Five `lcall` sites reach it, and at `0x485B`, `0x4868` and
`0x492D` each `lcall 0x4A76` is **immediately followed by a separate
`lcall 0x4A4D`** (`ec/decompiled/common/4825.asm:33,35`, `492D.asm:9`). That
pairing only makes sense if control comes back to the caller, so the routine
returns — and reading forward from the committed image,
`python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x4A76 -n 12`
gives the twelve bytes Ghidra assigned to `FUN_CODE_4a77`:

```
0x4a76  e9       mov  a,r1
0x4a77  75f00f   mov  0xf0,#0x0f
0x4a7a  a4       mul  ab
0x4a7b  24ce     add  a,#0xce
0x4a7d  f582     mov  0x82,a
0x4a7f  e4       clr  a
0x4a80  3449     addc a,#0x49
0x4a82  22       ret
```

**DPTR = 0x4900 + (R1 * 15 + 0xCE)**, truncated to the low byte — the `clr A`
clears the carry, so `DPH` is 0x49 whatever the low byte did. And the 0x4900
block is not XDATA: `0x4A4D` and `0x4A69` read it with `movc`, which is CODE. So
this is the first half of a **two-stage computed goto** — R1 picks a slot in a
code table, and `0x4A4D` loads that slot's 2-byte word into DPTR, which the
caller then jumps to. The sibling at `0x4A83` is the same shape with R6 and a
stride of 21 into the same page. Typed `math`.

**`common 0x3B4E`.** Four `lcall` sites. The fifteen bytes after it belong to
`dptr_3a00_plus_13x_3b51`, **which was already an annotated row**, and which the
bytes here run straight into. So one call does two things: it leaves R6 holding
the XDATA byte the caller left in DPTR, and it leaves DPTR at
0x3A00 + (R7 * 13 + 0xFC). Typed `math`, to match its own tail.

**`common 0x7177`.** Four transfers reach it, and this one the callers explain
completely. `bank0/D029.asm:7-17` and `common/0556.asm:37-45` are the same
prologue — read a 2-byte word out of CODE with `movc`, `xch` it into R1:R2 —
and then either `ljmp 0x7177` or `lcall 0x7177`. The routine's last two
instructions are `clr A` and `jmp @A+DPTR`, so it is a **jump-table thunk, not a
function that returns by its own `ret`**. The two `lcall` sites are consistent
with that: the dispatched code returns to the pushed address, and at
`common 0x05A6` that address is `0x05A9` — the `pop PSW / pop DPL / pop DPH /
pop B / pop A / reti` run that follows — so 0x7177 is reached from inside an
interrupt epilogue and `0x05A9` is where that epilogue resumes. Typed `dispatch`.

**`common 0x0200`.** The row said "this is the entry, not the function", and the
19-byte index size says the opposite: the entry **is** the function, and the 136
bytes after it are a separate row. The other evidence is stronger than either —
**every transfer the export shows reaches it with `ljmp` and none with `lcall`**
(`common/0070.asm:22` at 0x0094, `bank0/D757.asm:139` at 0xD86E,
`bank0/E256.asm:101` at 0xE320, `bank0/FE0F.asm:111` at 0xFEE8), so a caller
hands control over rather than expecting a return. The `mov 0x81,#0xC0` is
SP = 0xC0, the same stack placement the reset entry at `common 0x0070` makes as
its **first** instruction, so here it re-asserts a placement rather than making
the first one. Typed `init`.

### And the two bare `ret`s are real, and complete

`ec/decompiled/index.csv` gives `bank0 0xD2BE` and `bank0 0x9C47` a size of **1**
each. The single `ret` is the whole function, not a window — so whatever
hypothesis one had about a boundary, it does not apply to these two, and both
are typed from what the callers do with them (next section).

**So no row was added, and `--mode rebuild-project` was not needed.** That was
the issue's escape hatch, and it is worth saying that it did not fire: the
discriminator is that an annotation row seeds a function entry, and these five
already had one that resolves. The build's per-row gate confirms it —
`bank0 --check` reports every one of the twelve as `seed_basis=annotation`,
`annotated=yes`, and the row count as 1,877 records with no duplicate
`(scope, addr)`.

## The caller-side question: 0x9C47, and 0xD2BE is the same device

The 0x9C47 row asked what each caller expected to have happened before reaching
it. **`ec/decompiled/bank0/9AAD.asm` answers it, and the answer is that all
seven sites mean the same thing.**

0x9AAD is a dispatch on XDATA 0x044B. The `dec`/`jz` chain at 0x9B37 gives cases
0, 1, 2, 3 and 4, and then:

```
9b40     14        dec  a            ; A = value - 4
9b41     70 03     jnz  0x9b46
9b43     02 9c 00  ljmp 0x9c00       ; value == 4
9b46     24 04     add  a,#0x4       ; A = value
9b48     60 03     jz   0x9b4d       ; value == 0
9b4a     02 9c 47  ljmp 0x9c47       ; default
```

**`0x9B4A` is the default arm** — every value outside {0, 1, 2, 3, 4} lands
there. The other six `ljmp` sites are bail-outs from inside a case whose own test
failed:

| site | the test that failed |
|---|---|
| `0x9B5E` | the counter at XDATA 0x08BF is still below 0xC8 |
| `0x9B6F` | bit 0 of XDATA 0x08AD is clear |
| `0x9B84`, `0x9BA8` | `0xBBC7` returned with the carry set |
| `0x9B8F` | `0xB9F5` returned with the carry set |
| `0x9BC1` | XDATA 0x0873 is not below 0x08C7 |

Four further conditional branches reach the same address **without a transfer** —
`0x9BCE`, `0x9BD6`, `0x9BEF`, `0x9BFB`, all carry or below tests — which is why
the row's "seven transfer sites" undercounts the paths in. So every path into
0x9C47 means *the condition for this case's work did not hold*, and returning with
A, R7 and the carry as the caller left them is the whole of what the caller
expected. What the cases do when their test *does* hold is not decoded.

**`bank0 0xD2BE` turns out to be the same device, which the issue did not
anticipate.** All five `ljmp` sites are in `dispatch_on_0860` (0xD091) and each
is a guard on the way in:

| site | the test that failed |
|---|---|
| `0xD097` | XDATA 0x0860 reads zero |
| `0xD09E` | XDATA 0x0860 reads 0xFF |
| `0xD0A8` | bit 0 of XDATA 0x1C00 is set |
| `0xD0B2` | bit 0 of XDATA 0x1C11 is set |
| `0xD0BC` | bit 0 of XDATA 0x1C29 is set |

Past all five the caller copies six bytes out of that 0x1Cxx block into XDATA
0x0866-0x086B and picks 0x0865 from a compare chain on 0x0860. So the guard
validates the request before any of the work, and the do-nothing return is the
answer to each of the five failing.

Both are typed **`forwarder`** and named for the caller, which is the shape
`bank1 0xA9B3` ("the target of five `ljmp` instructions inside 0xA916, where it
serves as that function's common exit"), `bank0 0x849C` and
`bank1 0xEFBC` already set. **The `ret_only_*` name is a placeholder by the
grader's own definition** — `PLACEHOLDER` in `../../ec/tools/grade_name_basis.py`
matches `ret(_[0-9a-z]+)*` — so retyping off `unresolved` while leaving it would
have graded the row `unresolved` still, against its own new type.

## The six large bodies, and five readings that did not survive

Each was read to its end and typed from what the entry does. **Five of the six
carried a claim the bytes refute**, and the corrections are in place.

**`bank0 0xD757` → `state`.** The old text called it "a dispatcher on the direct
bits 0xE1 and 0xE3", branching on "bit 0 of 0xE1 and bit 1 of 0xE3". **0xE1 and
0xE3 are bit addresses, not data operands**: 0xE1 is bit 1 of A and 0xE3 is bit 3
of A, and A at both points holds the byte just read from XDATA 0x1500. So the
dispatch is on **bits 1 and 3 of XDATA 0x1500**, which is one byte with two
fields, not two ports. The head is also re-entered from **nine** `ljmp 0xD757`
sites, so this is a loop and not a straight cascade — a state machine whose
state is 0x1500, 0x1504, 0x1510 and 0x1514. And the old text joined two separate
cases: the 0x0F/0xFF/0xFE/0x00 run into 0x103B-0x103F is written on
0x1514 == 1 alone — 2 writes 0xFD to 0x103C and 5 zeroes 0x103E and 0x103D, so
the three touch the block without sharing an effect — while the tail-jump to
0x0200 happens **only** on
0x1514 == 0xFC, after writing 0x55/0xAA/0x00/0x33 to 0x07FE/0x07FF/0x07FD/0x0045.
That tail-jump is the only way out of the loop. **Two writes in it are dead, and
the second is the one the old text read as an effect**: 0x130A is loaded into A
at 0xD7D5 and overwritten at 0xD7D9 without a store, and the `mov 0xE4, CY` at
0xD783 sets bit 4 of an A that 0xD785 re-reads and 0xD786 replaces outright — so
the old "writes the masked value of 0x1500 back through 0xE4 and 0xE5" is wrong
on the 0xE4 half. The `clr 0xE5` at 0xD795 is the contrast that makes the pair
worth recording: 0xD797 stores A back to 0x1500, so that one does land.

**`bank0 0x8931` → `gate`.** The old text said the head "masks 0x48 and skips the
whole body when the result is zero". **It skips nine bytes, and those nine are
another function.** The `jz 0x8942` at 0x8937 lands on the very next instruction
in this listing, and the nine bytes in between are `bank0 0x8939`
(`store_200_via_dptr_then_8f09`, already annotated): when XDATA 0x08EB has bit 3
or bit 6 set, the routine stages 0xC8 into 0x08EB and tail-jumps to 0x8F09,
which copies it to XDATA 0x075C. When both are clear, five independently-enabled
blocks run and the routine ends in a tail-jump to 0x8C46. The blocks are gated on
bits 6 and 7 of MANUAL_FAN_CTRL (0x0751), and bit 0 of AP_OEM (0x0741) with bit 1
of AP_OEM_6 (0x07C6) — which `registers.yaml` already carries decoded, so the
name grades **`ec-register`** rather than `code-shape`, the only one of the
twelve that does. Block one's cascade requires XDATA 0x086C below 0x50,
**CPU_TEMP (0x043E) below 0x46 and GPU_TEMP (0x044F) below 0x46** — the two
temperatures are named in `registers.yaml` and this is the first row to say so
for this address. What the thresholds and the 0x0460 ramp *govern* is still not
decoded; naming the register is not naming the policy.

**`bank0 0xDE83` → `init`.** The old text said "the 0x3000 block is outside the
EC's own XDATA map". **It is not.**
`ec/annotations/xdata-registers.csv` carries 0x3000-0x3008 as `program=main-ec`,
`spelled_as=DAT_EXTMEM`, span group `0x3000-0x3008`, cluster `main-ec-006`,
written here and by `bank1 0x9B3C` and `bank1 0x9C53`. The routine stages a
descriptor across the block and then probes it, **returning the result in the
carry** — a `setb CY; ret` at 0xDF14 and a `clr CY; ret` at 0xDF1C, and the old
text described only the second. Two further facts the listing settles: 0x3006 is
written eight times in a row (zero, R5, then 0x0A4A, 0x0A49, 0x09C0, 0x09C1,
0x09C2, 0x09C3) — eight `movx @DPTR,A` stores at 0xDEAE, 0xDEB0, 0xDEB8, 0xDEC0,
0xDEC8, 0xDED0, 0xDED8 and 0xDEE0, over seven `mov DPTR,#0x3006`, the first two
sharing the one at 0xDEAB — so the byte that survives is XDATA 0x09C3, and the
0x3E written to 0x3001 at 0xDE8B is overwritten by 0x1F at 0xDEE7. **And the carry-set return
is not reachable from this entry's own bytes**: the two masks admit only 0x3000
in 0x00, 0x01, 0x10 or 0x11 (the `anl #0xEC` test is subsumed by the `anl #0xEE`
one before it, 0xEE carrying every bit 0xEC has and one more), the entry writes
0xFE at 0xDEE1, and nothing between that write and
the read at 0xDEF9 can change the byte. Something outside this entry would have
to supply the value, and **what that is is not established here** — it is a
question this row now asks rather than one it papers over.

**`bank1 0xBD45` → `dispatch`.** The routine forces XDATA 0x0491 to
`(0x0491 & 0xC0) | 0x21`, picks a base from XDATA 0x030D, probes 0x0438
(BAT_VOLTAGE_MV) through 0x8892 and one of 0x300C/0x2008/0x4010 through 0x885B,
and tail-jumps to 0xBF3A with the base in R6:R5. **The three-way consultation
with 0x0497, 0x0403 and 0x0539 has no effect on the outgoing register pair**:
both of its outcomes load the same DPTR, the base the arm already chose, so the
only thing the test changes is which of two identical stores runs. That is worth
recording because the shape of the code invites the opposite conclusion.

**`bank1 0xE656` → `math`.** Selects one of three CODE bases (0xEE32, 0xED32,
0xEC32) from 0x0491's top two bits, walks a table at a 14-byte stride reading a
CODE word and an XDATA byte per entry, and ends in a tail-jump-shaped return.
Two details the old text did not reach, and the bytes settle both: the `jnb 0xF3`
that picks each base's 0x…B2 variant tests **bit 3 of the B register** — `0xF3` is
no PSW bit address at all (PSW is `0xD0`-`0xD7`, and the carry is `psw.7` at
`0xD7`) — so what is tested is bit 3 of the byte `0xE65D` loaded into B from XDATA
`0x031C`, and what that bit represents is not decoded; and **R7 is a fixed trip
count of eight**, because the only back edge is the `sjmp` to the loop head at
`0xE6A1`, which reloads R7 from the exit test's `R7-2` and so counts it down by 2
from the `0x0E` set at `0xE69F`, while `lcall 0x888C` writes only A and DPTR and
cannot change it.

**`bank1 0xCD80` → `state`.** The old text said the step in R2 is "at least 3",
and **the bytes give that bound; what they settle is the condition the
substitution fires under, not the size of the step**. `anl A, #0xfc` / `jnz 0xCD90`
replaces R2 with 3 only when `0x0397 & 0xFC == 0` — 0x0397 is 0, 1, 2 or 3 — and any
larger value has a bit set above the mask and passes through untouched, so
`0x0397 = 0x05` stays a step of 5 and no value of 0x0397 gives a step below 3. The
comparison is the other way round from how it reads: `jz` and `jc` both lead to
0xCD98, so the body runs when the step is **at or below** the limit, and the `ret`
at 0xCD97 — taken with nothing touched — is the case where the step is above it.

## One in-place correction outside the twelve

`common 0x3B51` (`dptr_3a00_plus_13x_3b51`) said the high byte "is added through
the carry". **Its own listing rules that out**: `clr A` at 0x3B59 clears the
carry before `addc A,#0x3A` at 0x3B5A, so DPH is 0x3A unconditionally and the
index is truncated to one byte. The clause is corrected in place, in the file's
correction form, because 0x3B4E's new comment depends on it and leaving the two
contradicting would have been the worse outcome. No other row outside the twelve
was edited.

## What moved, and what did not

- **The record count did not move: 1,877 before and 1,877 after.** The pin in
  `../../ec/tools/build_ec_decompile.py` keeps its value and its history comment
  records that #456 added no rows, because a pin that moves only on purpose has
  to say when a change deliberately did not move it.
- **`ec/decompiled/` was re-exported** (73 files against `main`: 12 `.asm`, 58
  `.c`, and the two indexes plus the digest file). The `.asm` files differ only
  in their header line — the name and the plate comment — and **no instruction
  line changed** in any listing. The check is
  `git diff -U0 origin/main -- 'ec/decompiled/*.asm' | grep -E '^[-+]' | grep -vE '^[-+][-+][-+]|^[-+];'`
  returning nothing: `-U0` and the first `grep` leave only added and removed
  content, the second drops the `---`/`+++` file headers and the `;` comment
  lines, so a surviving line would be an instruction that moved. The 58 `.c`
  files split two ways, and only the first is this change's: **57 differ
  because the decompiler emits one of the twelve new names** in them, and
  **one, `common/3B51.c`, carries the 0x3B51 correction above**. A third file,
  `bank0/D9FE.c`, was in this tranche's re-export and is not in the diff here:
  it lost a clause its own CSV row on `main` had already dropped, and `main`
  carries that fix already, so the re-export reproduces it rather than
  restating it.
- **A reader cannot predict the 57 from the twelve names alone**, and the reason
  is already written down elsewhere: `../../ec/tools/export_ownership.py`'s
  docstring records that the exporter cut `bank1:0x8001`-`0x8189` into 42
  exports whose `.c` files **all decompile the same routine**, so a rename that
  reaches one of them reaches all 42. That is a property of the exporter's
  ownership boundary, not a claim about what any one diff carries.
- **`ec/ghidra/c-digests.csv` and `ec/ghidra/cross-decoder.csv` were
  regenerated** with the tool's own `--write-digests` and `--report`.
- **The citation ranking moved, because the new comments cite more addresses.**
  `ec/annotations/call-graph-callees.csv` was regenerated with
  `../../ec/tools/call_graph.py` over the same 1,841 rows: **four gained their first
  citation** — `common` 0x4A77, 0x492D, 0x0FE6 and 0x150A, all named in the new
  comments — **none lost one**, and the twelve rows carry their new names. The
  four citation figures and the frame-gate partition in `call-graph.md`'s census
  table are re-measured accordingly.
- **Three more committed CSVs name the twelve**, and all three are regenerated by
  their own tool rather than edited: `xdata-registers.csv` and
  `xdata-clusters.csv` with `../../ec/tools/xdata_register_map.py`, and
  `xdata-export-ownership.csv` with `../../ec/tools/export_ownership.py`. The first
  two are held by `agent-gates.sh`, so a rename that left them stale turns the
  gate red; the third is not, and would have drifted quietly. `xdata-registers.csv`
  is also the evidence `bank0 0xDE83`'s new comment cites for the 0x3000 block
  being inside the EC's XDATA map rather than outside it.
- **`subsystems.md`'s census moved twice**, because twelve rows left
  `type=unresolved` and two of them were also `ret_only_*`: 169 → 157 and
  269 → 267. Both are recorded in that file's own correction form.
- **`call-graph.md` has three figures that were already wrong before this
  change** and are left as they were, with a `†` and a correction paragraph
  beside them rather than a quiet fix. They are the `FUN_*` and unreached counts;
  the tool measures 789/320/797 against the table's 807/337/815 on this tree,
  and measured 790/320/798 on the tree before this change too. That is
  pre-existing drift in a hand-transcribed table, and it belongs to its own
  correction.

## What this does not establish

Stated as a list, because the limit is the point:

1. **No subsystem is identified.** The retyping is about the mechanism each entry
   performs — a table index, a state machine, a gate cascade, a shared
   bail-out — and not about what the XDATA bytes belong to. Where a row's
   comment names CPU_TEMP, GPU_TEMP, MANUAL_FAN_CTRL or BAT_VOLTAGE_MV, that is
   `registers.yaml` repeating an existing decode, not a new one.
2. **No register `status:` changed**, and no `registers.yaml` row was added.
   Naming a helper is not a finding about a register, and this change adds no
   register claims to check.
3. **Nothing was observed on hardware.** Confirming that 0x043E below 0x46 is a
   70 °C gate, that 0xDE83's probe has a live far side, or what 0x1514's
   dispatch is counting needs the physical machine. Every row stops at what the
   bytes support.
4. **The Ghidra project's committed form was not written.** The default
   export-only build copied the committed project to scratch and exported from
   the copy; `ec/ghidra/project/` is byte-identical to `main`. No
   `--mode rebuild-project` ran, so no branch has rebuilt the 7 MB `.rep` and two
   such branches cannot merge.
5. **A `unresolved` row is still a result, and there are 157 of them.** This
   change took twelve out; it did not make the remaining 157 any easier. Three
   figures in §"What is left" of `call-graph.md` were re-measured against
   `../../ec/tools/call_graph.py` rather than carried over, because the new
   comments cite more addresses.
6. **Nothing upstream.** The mission's eventual `Wer-Wolf/uniwill-laptop` /
   `tuxedo-drivers` PR (issue #10) is not this issue's deliverable, and no stage
   may open one.

## One environment note, for whoever runs this next

`ec/ghidra/project/ec.rep/project.prp` records
`<STATE NAME="OWNER" ... VALUE="dave" />`, and a Ghidra project can only be
opened by the user that owns it. **On a fresh GitHub-hosted runner the committed
project therefore cannot be opened at all**: `python3 ec/tools/build_ec_decompile.py
--work /tmp/ec` fails with `ghidra.util.NotOwnerException: Project is owned by
dave` on the very first `analyzeHeadless`, before it reads a single annotation.
This is not a fault in the change and not something to fix by editing the
committed `.rep` — CLAUDE.md forbids that, and a rebuild writes the 7 MB binary
two branches cannot merge. The workaround used here was to copy the committed
project to scratch, change the OWNER string **in the copy only**, and point the
build at that copy by overriding `build_ec_decompile.PROJECT` in a driver
script; the committed project was never opened. If the export has to be
regenerated on a fresh runner, that is the route, and it leaves the repository
untouched.
