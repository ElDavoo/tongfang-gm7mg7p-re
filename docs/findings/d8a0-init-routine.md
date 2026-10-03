# `bank0,0xD8A0`: the routine the reset operand lands one byte short of, and the four `0x20xx` bytes it alone touches (issue #575)

`docs/findings/reset-vector-dptr-targets.md` (#559) read the two bank-0
addresses the reset vector names through `mov DPTR,#imm16` and left `0xD8A0`
unread as a follow-up. This is that follow-up. `0xD8A0` is a **0x87-byte,
60-instruction routine with no `ret`** that tail-jumps to `0xEADA`, it has its
own bank-switch trampoline at `common,0x1504` with exactly one caller, and it
holds the only direct reference in the image to four bytes of the `0x20xx`
page that carried no `registers.yaml` row before this change.

Two of the issue's expectations do not survive contact with the bytes, and both
are corrected here rather than dropped: there is no `ret` to decode to, and
the register set is four addresses rather than the two it listed. One reading
in the issue is corrected as well — **the `R7` the gate tests is not the `1`
written eleven instructions earlier**, which is what makes the gate harder to
name than the issue's "power-on/settling" guess.

Everything below re-derives from the committed image and the committed
decoder. Nothing was observed on hardware, and no live test is claimed.

---

## The decode, and where it stops

```
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D8A0 --runtime 0xD8A0 -n 61
0xd8a0  e4       clr  a
0xd8a1  ff       mov  r7,a
0xd8a2  125597   lcall 0x5597
0xd8a5  12d722   lcall 0xd722
0xd8a8  7f01     mov  r7,#0x01
0xd8aa  125597   lcall 0x5597
0xd8ad  12d72b   lcall 0xd72b
0xd8b0  12de65   lcall 0xde65
0xd8b3  12d927   lcall 0xd927
0xd8b6  12193c   lcall 0x193c
0xd8b9  12d946   lcall 0xd946
0xd8bc  12bfde   lcall 0xbfde
0xd8bf  900983   mov  dptr,#0x0983
0xd8c2  e0       movx a,@dptr
0xd8c3  54fe     anl  a,#0xfe
0xd8c5  f0       movx @dptr,a
0xd8c6  12c295   lcall 0xc295
0xd8c9  ef       mov  a,r7
0xd8ca  600e     jz   0xd8da
0xd8cc  90201c   mov  dptr,#0x201c
0xd8cf  e0       movx a,@dptr
0xd8d0  20e107   jb   acc.1,0xd8da
0xd8d3  900983   mov  dptr,#0x0983
0xd8d6  e0       movx a,@dptr
0xd8d7  4401     orl  a,#0x01
0xd8d9  f0       movx @dptr,a
0xd8da  7f32     mov  r7,#0x32
0xd8dc  120ea2   lcall 0x0ea2
0xd8df  12c174   lcall 0xc174
0xd8e2  7f64     mov  r7,#0x64
0xd8e4  120ea2   lcall 0x0ea2
0xd8e7  90161b   mov  dptr,#0x161b
0xd8ea  7404     mov  a,#0x04
0xd8ec  f0       movx @dptr,a
0xd8ed  90161c   mov  dptr,#0x161c
0xd8f0  f0       movx @dptr,a
0xd8f1  12d9d2   lcall 0xd9d2
0xd8f4  12d9db   lcall 0xd9db
0xd8f7  12db96   lcall 0xdb96
0xd8fa  12d9dc   lcall 0xd9dc
0xd8fd  900081   mov  dptr,#0x0081
0xd900  e0       movx a,@dptr
0xd901  ff       mov  r7,a
0xd902  128000   lcall 0x8000
0xd905  12d9fe   lcall 0xd9fe
0xd908  121942   lcall 0x1942
0xd90b  12284d   lcall 0x284d
0xd90e  902012   mov  dptr,#0x2012
0xd911  e0       movx a,@dptr
0xd912  4401     orl  a,#0x01
0xd914  f0       movx @dptr,a
0xd915  902014   mov  dptr,#0x2014
0xd918  7406     mov  a,#0x06
0xd91a  f0       movx @dptr,a
0xd91b  902015   mov  dptr,#0x2015
0xd91e  7480     mov  a,#0x80
0xd920  f0       movx @dptr,a
0xd921  ff       mov  r7,a
0xd922  7e00     mov  r6,#0x00
0xd924  02eada   ljmp 0xeada
0xd927  e4       clr  a
```

**The issue asks for the routine "to its `ret`", and there is no `ret`.** The
last instruction is `ljmp 0xEADA` — a tail jump — so this routine never returns
to whoever reached it. Its 60 instructions span `0xD8A0`–`0xD926`, and `grep -c
' ret '` over the decode is zero. Everything below about "the end" means that
tail jump.

**The boundary is committed evidence, not judgement.** The instruction after
the tail jump is not a continuation of this routine; `0xD927` is its own entry
in `ec/decompiled/index.csv` (`bank0,D927,FUN_CODE_d927,31,call-target`) with
its own committed listing `ec/decompiled/bank0/D927.asm`, a 31-byte loop that
ends `ret` at `0xD945`. That routine is called *from* this one (`lcall 0xD927`
at `0xD8B3`), which is the ordinary caller/callee relation and not a
continuation. Decoding past `0xD926` would be reading a different function's
body and calling it this one's.

## The exit state is set three instructions before the jump, and the callee takes it on entry

`0xD91B` stores `0x80` to XDATA `0x2015`, `0xD921` copies that `A` into `R7`,
and `0xD922` clears `R6`. **Those two registers are the whole of what this
routine passes to `0xEADA`**, and `0x2015`'s stored value is where `R7` comes
from — so this is the one place in the routine where a write visibly reaches
past its own boundary.

The callee has a committed listing, and it consumes both registers in its
first four instructions:

```
EADA     90 0a 47 mov      DPTR, #0xa47
EADD     ee - -   mov      A, R6
EADE     f0 - -   movx     @DPTR, A
EADF     ef - -   mov      A, R7
```

`ec/decompiled/index.csv` carries it as `bank0,EADA,FUN_CODE_eada,251,
call-target` — unannotated, so it has no name, but the listing is committed
and its boundary is the call-target census's, which is an upper bound
(`ec/annotations/bank-call-audit.md` §1). So the exit state is not merely
set: `R6` goes straight into XDATA `0x0A47` and `R7` is read into `A` on the
next instruction. What `0xEADA` does with `A` afterwards is not decoded here.

## The gate, and the correction the issue's reading needs

The issue reads the `0x201C` test as *"re-sets that bit when `R7` is non-zero"*.
The test is as described, but **`R7` is not the `1` written at `0xD8A8`.**
Between `0xD8A8` and the `mov a,r7` at `0xD8C9` the routine makes seven calls,
and four of the callees write `R7` in committed listings:

| callee | annotation | where it writes `R7` |
|---|---|---|
| `0xD72B` | `scatter_0200_to_table_6d74` | `mov R7,A` on entry, then `inc R7` in the loop to `0x0E` |
| `0xD927` | `FUN_CODE_d927` (unannotated) | `mov R7,A` |
| `0xD946` | `FUN_CODE_d946` (unannotated) | `mov R7,A` |
| `0xBFDE` | `init_xdata_from_code_table_64fd` | `mov R7,0x69` / `mov R7,A` |

`0xD72B` alone fixes it: it leaves `R7 = 0x0E`, and three of the five calls
that follow it write `R7` again. So the gate at `0xD8C9` is on a value the
intervening calls produced, and the `mov r7,#0x01` at `0xD8A8` is an
**argument to `0x5597`**, not a flag carried forward.

**That sharpens what `0x5597` is doing at the top.** `common,0x5597` is
`write_009f_4f_or_0f_by_r7`: with `R7 = 0` it writes `0x4F` to XDATA `0x009F`,
and with `R7` non-zero it writes `0x0F`. So the routine opens by running the
same selector twice with opposite arguments and taking a **different init for
each arm** — `lcall 0xD722` (`zero_0a4b_then_tail_jump_541d`) on the `R7 = 0`
path, `lcall 0xD72B` (`scatter_0200_to_table_6d74`) on the `R7 = 1` path. The
`R7` at `0xD8A8` is a mode argument that does not survive; that is what makes
`select_…` the right verb for a name, and it is why the issue's "power-on /
settling" is a guess: the routine's first act is a **branch**, not a settle.

**The gate's two conditions, precisely.** Bit 0 of XDATA `0x0983` is cleared at
`0xD8C3`, `0xC295` (`test_1665_bit4_inverted`) is called, and the bit is put
back only when *both* `R7` is non-zero *and* bit 1 of `0x201C` reads clear —
`jb acc.1,0xd8da` jumps past the restore. What either condition *means* is not
decoded; the bytes say what the gate is on, not what it is for.

## The two waits are timer1-counted, not instruction-counted

The issue calls `R7=0x32`/`0x0EA2` and `R7=0x64`/`0x0EA2` "two delay calls",
which is right in shape. The mechanism is already named in the tree rather
than read here: `0x0EA2` carries the annotation
`timer1_counted_delay_using_0a56` in `ec/annotations/ghidra-functions.csv`,
whose comment records that it stores `R7` into XDATA `0x0A56` as a loop
counter, calls `0x0EE8` (`timer1_load_th1_fd_tl0_clear_tf1_start`) per counter
value, spins until bit 7 of `0x8F` is set, decrements `0x0A56` and repeats —
and that `0x8E`/`0x8F` are TCON.6/TF1 and TCON.7, i.e. TR1/TF1, so the wait
is counted on **timer1 overflows**. Its committed listing
`ec/decompiled/bank0/0EA2.asm` is the machine code behind that reading.

So `0xD8A0` waits 50 ticks, calls `0xC174` (`set_1603_bit3`), waits 100 ticks.
The unit is a timer tick, which is why the two seeds are round numbers; how
long a tick is, is not decoded here, and the annotation says the same.

## Both addresses are instruction starts

```
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D8A0 --converge
0x0D8A0: 24 of 24 preceding anchors decode onto it, 0 step over it
```

24 of 24 with 0 stepping over is the same score #559 records for `0xD89F` and
`0xD96C`, and it rules out the `bank1,19A8` failure mode where an operand byte
was mistaken for an entry. The decode rests on `disasm8051.py` unmodified;
`--self-test` is the oracle for the decoder's own tables and is not re-run
because nothing about it changed.

## Uniqueness: one DPTR immediate each, and one caller for the trampoline

Scanning the committed 256 KiB image for the opcodes that could name these
addresses:

| target | `90 hi lo` (DPTR immediate) sites | `12`/`02` operand sites |
|---|---|---|
| `0xD89F` | 1 — at `0x158E` (`common,0x158E`), the reset trampoline | 0 |
| `0xD8A0` | 1 — at **`0x1504`** (`common,0x1504`), a different trampoline | 0 |
| `0xD96C` | 1 — at `0x1594` (`common,0x1594`), the reset trampoline | 0 |

The common area is identity-mapped in `ec/firmware/GMxMGxx_11.800`, so
`common,0x1504` is image byte `0x1504`; bank 0's code is at file offset
`0x8000` + (addr − `0x8000`), so `bank0,0xD8A0` is image byte `0x0D8A0`. That
`0xD8A0` has a route of its own, distinct from the reset vector's, is
re-derived here rather than inherited: the reset vector
(`ec/decompiled/common/0070.asm`) `lcall`s `0x110A`, `0x158E`, `0x0F75` and
`0x1594`, and names neither `0x1504` nor `0xD8A0`.

**As in #559, this is a category fact and not a gap.** `bank-call-targets.csv`
counts `lcall`/`ljmp` *operands*, so a `mov DPTR,#imm16` produces no row in it
whatever. The census never claimed these addresses and is not wrong to omit
them.

## `common,0x1504`: a bank-switch trampoline, and its one caller

`ec/decompiled/common/1504.asm` is two instructions and six bytes:

```
1504     90 d8 a0 mov      DPTR, #0xd8a0
1507     02 11 00 ljmp     0x1100
```

`0x1100` is the Keil BL51 cross-bank switch stub this repository's decompiled
output names `bl51_bank_select_0`, so `common,0x1504` is a **bank-switch
trampoline into bank 0** — the same shape as `common,0x158E` and
`common,0x1594`, which #558 named `load_dptr_d89f_tail_jump_1100` and
`load_dptr_d96c_tail_jump_1100`. `1504.c` renders the pair as
`bl51_bank_select_0(0xd8a0); return;`, and there is no `ret` in the listing:
the trailing `return;` is the decompiler reading the tail jump as a call, so
the `.c` is not a shape the name repeats.

**The boundary is hard, not the hypothesis an unannotated listing carries.** The
six-byte trampoline grid runs unbroken either side of this site and the index
carries every site in the run at six bytes: `common,14FE`
(`mov DPTR,#0xD9FB`), `common,1504`, `common,150A` (`mov DPTR,#0x8564`),
`common,1510` (`mov DPTR,#0xA749`, tail-jumping `0x1114` rather than `0x1100`).

**`common,0x1504` is not one of #558's four, and no naming work is
duplicated.** Those four rows are `common,0x07F0`, `common,0x0F75`,
`common,0x158E` and `common,0x1594`; `common,0x1504` has no
`ghidra-functions.csv` row of its own, which is the deferral below.

**Who calls it: exactly one site, and it is not the reset vector.**

```
$ grep -n '^026C' ec/decompiled/common/0213.asm
54:026C     12 15 04 lcall    0x1504
```

`ec/decompiled/common/0213.asm` is `FUN_CODE_0213`, 136 bytes,
`seed_basis=call-target`, unannotated. The `lcall 0x1504` sits on the arm
reached when `R7` is not `0x33` after `lcall 0x14F8`, between `lcall 0x0F58`
and `lcall 0x0609`, and it falls into the shared `common,0x150A` tail at
`0x0272`. `bank-call-targets.csv` records the same edge independently of the
byte scan.

**The route is distinct from the boot path, and that stops being readable one
step earlier.** `FUN_CODE_0213` itself has exactly one caller, `common 0x03C1`,
which has no committed listing — so the chain
`common 0x03C1 → common,0x0213 → common,0x026C → common,0x1504 → bank0,0xD8A0`
is established as far as the evidence goes and no further. **Whether the boot
path reaches `0x03C1` is not traced here and is not claimed.**

## The one-byte question, positioned

The issue asks for a labelled position, and asks that an unsettleable
question be left open rather than resolved by preference. Taken in that order:

**Establishable, and all of it re-derived above.**

- The reset vector's trampoline at `common,0x158E` carries the immediate
  `0xD89F`, and `0xD89F` is a single `ret` byte — the fourth in a run that
  closes `bank0,D889.asm` and `bank0,D894.asm` (#559).
- One byte on, `0xD8A0` is a 60-instruction routine, 24/24 on `--converge`.
- It has a **route of its own**: `common,0x1504`, reached from
  `common 0x026C` inside `FUN_CODE_0213`, a function the reset vector does not
  call in its window.

**Not establishable, and now less likely to be settled by any future reading of
this routine.** *"The linker lost a byte"* is not claimed, and reading the
routine does not make it claimable. What the reading adds is a fact that is
consistent with the lost-byte story without requiring it: **the routine is
already reachable by a working trampoline with its own caller**, so the boot
path's operand naming the `ret` one byte short costs nothing that
`common,0x1504` does not already provide. If the operand were corrected to
`0xD8A0`, the route would gain a second entry into a routine that already has
one; if it was meant as-is, the `ret` is a no-op stub on a bank 0 that the
vendor left reachable. Both readings of the linker are consistent with every
byte here, and nothing in the image distinguishes them.

**The question therefore stays open**, with one thing added to it: the second
route means the reset operand's correctness is *not load-bearing* for whether
`0xD8A0` runs at all. That is a smaller claim than the issue's and it is the
one the bytes support.

## The addresses: four bytes no `registers.yaml` row named, not two

The issue asks whether the addresses this routine touches deserve rows, *"if the
writer set is small"*. For four of them it is as small as this repository's
methods can measure, and all four sites are inside this routine:

| address | `scan_refs.py` | site | what this routine does | row |
|---|---|---|---|---|
| `0x2012` | `refs=1 ec=1 pd=0` | `0xD90E` | `orl a,#0x01` — sets bit 0, leaves the other seven (`read+write`) | added |
| `0x2014` | `refs=1 ec=1 pd=0` | `0xD915` | `mov a,#0x06` (`write`) | added |
| `0x2015` | `refs=1 ec=1 pd=0` | `0xD91B` | `mov a,#0x80`, then `R7=A` (`write`) | added |
| `0x201C` | `refs=1 ec=1 pd=0` | `0xD8CC` | `movx a,@dptr` / `jb acc.1` — **read only** (`read`) | added |
| `0x0983` | `refs=22 ec=22 pd=0` | `0xD8BF` | clears then conditionally re-sets bit 0 | declined |
| `0x161B` | `refs=2 ec=2 pd=0` | `0xD8E7` | `movx @dptr,a` = `0x04` | declined |
| `0x161C` | `refs=3 ec=3 pd=0` | `0xD8ED` | `movx @dptr,a` = `0x04` | declined |

**The four added rows are the four the issue did not list.** The issue names
`0x0983`, `0x201C`, `0x161B` and `0x161C`; it missed `0x2012`, `0x2014` and
`0x2015`, which the same decode writes in its last block. Those three are the
better candidates under the issue's own criterion, not the worse ones: each has
exactly one direct site in the image and that site is here.

**No byte of the `0x2000`–`0x20FF` page carried a `registers.yaml` row before
this change**, which is the narrower claim the tree supports and the one that
makes these four a single finding rather than four unrelated ones. The page
itself was not unnamed: `ec/annotations/xdata-registers.csv` already carried
eight rows in it — `0x2000`, `0x2001`, `0x2002`, `0x2006`, `0x2007`, `0x2009`,
`0x200B` and `0x200F` — each spelled `DAT_EXTMEM` with a `cluster_id` and a
non-zero ref count, and `ec/annotations/xdata-clusters.csv` the matching
cluster rows. `registers.yaml` names `0x2000`/`0x2001`/`0x2002` only in the
notes of `XDATA_0450`/`XDATA_0451`/`XDATA_0452` and in
`copy_2000_2002_to_0450_0452`, never as a row of their own. What is new here
is the register row, not the first mention of the page.

**And these four are the only bytes in the page this routine is the sole
direct accessor of.** Sweeping `0x2000`–`0x20FF` for `90 hi lo` in the EC
image puts every other byte of the page at sites this routine does not touch,
with between one and eighteen sites each; `0x2012`, `0x2014`, `0x2015` and
`0x201C` are the only four whose single site in the image is inside it.

**The three declined addresses, and the figures that declined them.**
`0x0983` has 22 direct sites and a `main-ec-208` census row naming 14 citing
functions; `0x161B` and `0x161C` carry `main-ec-172` rows and each has a
second writer in bank 1. A row added from this routine would assert a decoding
this issue did not do. **`0x161B`/`0x161C` also have a second writer that
writes the same value this one does** — `bank1,0x9A1B`
(`set_161b_161c_4_and_0681_86`) stores `0x04` to `0x161C`, then `0x04` to
`0x161B`, then `0x86` to `0x0681`. That is **static co-writing**: the same
value to the same pair from a routine in another bank. It is a fact about two
independent listings and says nothing about a shared mechanism, an ordering
constraint or a protocol between them, and no such claim is made here.

**What these rows do and do not say.** Each records one EC-side site and its
direction; the status is `present-untested`, whose ceiling is exactly that,
because nothing was run. For `0x201C` there is **no writer found by either
committed method** — a computed DPH or an indirect `movx @Ri` is invisible to
both scans, so that is *"not found by this method"* and never *absent*, and a
byte only ever read must be written by something. The writer is an open
question, not an answer. What `0x06`, `0x80` and bit 1 *mean* is not decoded
here at all.

## The annotation rows are deferred, and this is the measured reason

Two rows are owed and neither lands on this branch. Both were tested against
the gates on a scratch copy of this tree, using the tools' own entry points.

**A `bank0,0xD8A0` row fails four checks.** `build_ec_decompile.py --check`
reports, for `bank0` and for `common`:

```
FAIL  bank0: manifest records annotations_unmatched=0; the committed files give 1.
FAIL  bank0: the annotation bank0 D8A0 resolves to no exported function
FAIL  subsystems.md: bank0 D8A0: the evidence ec/decompiled/bank0/D8A0.asm does not exist on disk
FAIL  subsystems.md: the census states N annotated function rows and the committed files hold N+1
```

The manifest is written by a Ghidra run, and `ec/decompiled/bank0/D8A0.asm` is
what that run would emit. The last line's census figure is left as `N` rather
than written out: it is a count of a CSV every landing row moves, so the run
that adds this row reads it off `build_ec_decompile.py --check`'s own output
instead of off this file.

**A `common,0x1504` row fails on the same root cause from the other side.** Its
listing *does* exist, so the evidence and unmatched checks pass; what fails is
the manifest's per-program `annotations_applied` counter, for `bank0`, `bank1`
and `common` alike — *"That figure came from a report, so this is a manifest no
run produced"* — plus the same `subsystems.md` census lines and a stale
cross-decoder report. **One Ghidra export is what both rows need**, which is the
same conclusion #559 reached from the export side and #255 from the listing
side.

### The row-by-row list for the pinned-toolchain run

Everything that moves when the export lands, so that run needs no
re-derivation. The naming follows #558's precedent, which put the address in
the name for a reason: these are six-byte trampolines on a grid, so the suffix
is an address and not a claim that this one differs in any other way.

| # | file | change |
|---|---|---|
| 1 | `ec/annotations/ghidra-functions.csv` | add the 2 rows: `common,0x1504` `load_dptr_d8a0_tail_jump_1100` (type `bank-switch`, `basis: hand-decoded`) and `bank0,0xD8A0` `select_009f_4f_or_0f_then_gate_0983_on_201c` (type `init`, `basis: hand-decoded`), the latter commented to say the exit is a tail jump with no `ret`, that the boundary is fixed by `bank0,D927`'s committed listing, and that the `R7` the gate tests is the one `0xD72B`/`0xD927`/`0xD946`/`0xBFDE` leave rather than the `1` set eleven instructions earlier |
| 2 | `ec/decompiled/bank0/` | add `D8A0.asm`, `D8A0.c` — and **only these two**; `common/1504.asm` and `.c` are already committed |
| 3 | `ec/decompiled/index.csv` | +1 row |
| 4 | `ec/decompiled/listing-index.csv` | +1 row |
| 5 | `ec/ghidra/reassembly.csv` | +1 row, via a full `--report` on the pinned toolchain |
| 6 | `ec/ghidra/c-digests.csv` | +1 row, via `--write-digests` |
| 7 | `ec/ghidra/manifest.csv` | whatever the export writes for `annotations_unmatched` and `annotations_applied` — this is the row that gates both entries above |
| 8 | `ec/annotations/subsystems.md` | the `annotated function rows` census at **both** restatements, and the per-program rows `check_subsystems()` recomputes |
| 9 | `ec/annotations/ghidra-variables.csv` | only if the export emits variables for `0xD8A0` |
| 10 | `docs/findings/citing-listing-evidence.md` | its two annotation-row restatements |

**Two figures above are deliberately left as names, not numbers.** The census
lines in `subsystems.md`, `c-digests.csv` and the cross-decoder report all
move together, and each is a `--check` that a half-landed export turns red;
`build_ec_decompile.py --check` prints the current value of each, and the run
that lands the export reads them off its own output rather than off this table.

**If a seed reports `annotations_unmatched > 0` for bank0, the run must say so
out loud** — that is `ec/ghidra/README.md`'s "the project needs `--mode
rebuild-project`" case, and it would mean the committed project does not hold a
function at `0xD8A0`. `--converge` is not evidence against it: 24/24 says the
address is a coherent instruction start, not that the *project* has a function
there. `--mode export-only` seeds the scratch copy and leaves the committed
`.rep` unwritten, so no rebuild is needed unless that verdict comes back
otherwise.

## What is not claimed

- **Nothing was observed on hardware.** No register was read back and no bit
  was seen set. The gate's two conditions are described as the bytes state
  them, not as behaviour.
- **What the routine *is for* is not decoded.** That it runs early, that the
  two waits are settling time, and that `0x2015`'s `0x80` is an enable are all
  consistent with the bytes and none of them is established by them. The name
  proposed above follows the two things the bytes do say — it selects, and it
  gates — for that reason.
- **`0x193C`, `0x1942` and `0x284D` are not read, and none of the three has a
  committed listing.** `0xEADA` and `0x0EA2` do, and are read from theirs
  above: `0x0EA2` carries an annotation of its own, while `0xEADA` has only
  the call-target census's name `FUN_CODE_eada` and is read no further than
  its first four instructions. The remaining callees are named here from their
  existing annotations and not re-decoded: `0x5597`, `0xD722`, `0xD72B`,
  `0xBFDE`, `0xC295`, `0xC174`, `0xDB96`, `0xD9D2`, `0xD9DB`, `0xD9DC`,
  `0xD9FE`, `0x8000`.
- **The four `0x20xx` rows record sites, not meanings.** `0x06`, `0x80`, bit 0
  and bit 1 are values the routine stores and tests. What any of them selects
  is not established, and the writer of `0x201C` is an open question.
- **`common,0x03C1` and the boot path are not traced.** The route into this
  routine is established as far as that one caller and no further.
- **The one-byte question is left open**, as above, and this reading adds a
  reason it is unlikely to be closed from this side rather than an answer.

## Reproducing this

Everything above re-derives from committed inputs:

```sh
# 1. the decode, its 60 instructions, and the tail jump that ends it
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D8A0 --runtime 0xD8A0 -n 61
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D8A0 --runtime 0xD8A0 -n 60 \
  | grep -c ' ret '        # -> 0: the exit is a tail jump, not a ret

# 2. 24 of 24 anchors decode onto it, 0 step over
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D8A0 --converge

# 3. the boundary: 0xD927 is its own committed entry, not a continuation
grep -E '^bank0,D927,' ec/decompiled/index.csv     # -> 31 bytes, call-target
cat ec/decompiled/bank0/D927.asm                   # ends `ret` at 0xD945
ls ec/decompiled/bank0/D8A0.asm                   # -> no such file

# 4. the trampoline, the six-byte grid either side of it, and its one caller
cat ec/decompiled/common/1504.asm
grep -E '^common,(14FE|1504|150A|1510),' ec/decompiled/index.csv   # all 6 bytes
grep -n '^026C' ec/decompiled/common/0213.asm                    # -> lcall 0x1504
grep -n '026C' ec/annotations/bank-call-targets.csv

# 5. uniqueness: one DPTR immediate each, no lcall/ljmp operand naming any
python3 - <<'EOF'
data=open('ec/firmware/GMxMGxx_11.800','rb').read()
for t in ('d89f','d8a0','d96c'):
    for op,name in ((b'\x90','DPTR imm'),(b'\x12','lcall'),(b'\x02','ljmp')):
        pat=op+bytes.fromhex(t); i=0; s=[]
        while (j:=data.find(pat,i))>=0: s.append(hex(j)); i=j+1
        print(f'0x{t} {name:9s}: {s}')
EOF
# -> one DPTR site each (0x158E, 0x1504, 0x1594); no lcall/ljmp site for any

# 6. the gate's R7 is not the 1 set at 0xD8A8: four callees write it
grep -lE 'mov +R7' ec/decompiled/bank0/D72B.asm ec/decompiled/bank0/D927.asm \
  ec/decompiled/bank0/D946.asm ec/decompiled/bank0/BFDE.asm
sed -n '8,20p' ec/decompiled/bank0/D72B.asm        # mov R7,A; inc R7 up to 0x0E, then ret

# 7. the two waits' callee and the exit state's callee, both from their
#    committed listings; 0x5597 and 0x0EA2 already carry annotation rows
cat ec/decompiled/common/5597.asm
grep -E '^bank0,0EA2,' ec/decompiled/index.csv   # -> timer1_counted_delay_using_0a56, annotation
head -12 ec/decompiled/bank0/EADA.asm            # -> DPTR #0xa47, store R6, read R7 into A

# 8. the four addresses this routine alone touches in the 0x20xx page
for a in 2012 2014 2015 201C 0983 161B 161C; do
  python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x$a | grep '^0x'
done
# no registers.yaml row for any byte of the page, before this change:
git show origin/main:ec/annotations/registers.yaml \
  | grep -cE '^\s*-?\s*addr:\s*"?0x20[0-9A-F][0-9A-F]'   # -> 0
# eight bytes of the page the census already named, under DAT_EXTMEM:
git show origin/main:ec/annotations/xdata-registers.csv \
  | awk -F, '$1 ~ /^0x20/ {print $1, $3, $5, $6}'
python3 - <<'EOF'
data=open('ec/firmware/GMxMGxx_11.800','rb').read()[:0x18000]
for i in range(len(data)-2):
    if data[i]==0x90 and 0x2000 <= (a:=(data[i+1]<<8)|data[i+2]) <= 0x20FF:
        print(f'0x{a:04X} site at {i:#x}')
EOF
# -> 0x2012@0xD90E, 0x2014@0xD915, 0x2015@0xD91B, 0x201C@0xD8CC: one each, all here

# 9. the co-writer on 0x161B/0x161C, which is static co-writing and nothing more
cat ec/decompiled/bank1/9A1B.asm

# 10. the four register rows, the two regenerated files, and the gate
python3 ec/tools/gen_xdata_symbols.py --check
python3 ec/tools/check_site_resolution.py --check
python3 ec/tools/check_status_vocabulary.py --check
python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
bash .github/scripts/agent-gates.sh
```

The two `ghidra-functions.csv` rows are **not** in that list because they do not
land here; §"The annotation rows are deferred" gives the measured reason and
the table that lands them.