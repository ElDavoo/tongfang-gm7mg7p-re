# `common,0x07F0`, `0x0F75`, `0x158E` and `0x1594`: the top of the corrected call-graph ranking, read (issue #558)

Issue #525's `citation_callers.py` refused 21 `fill-at-citer` pairs, and with
them the top of `../ec/annotations/call-graph-callees.csv` became a different
set of addresses. Four came out on top: `common,07F0` at
`cited_by=3 / inbound=3`, and `common,0F75`, `common,158E` and `common,1594`
each at `cited_by=1 / inbound=1`, all four still `annotated=no` and all four
`FUN_CODE_*`. This file is the reading of those four listings and the four rows
it produced. The write-up for the correction that put them there is
`citing-listing-evidence.md`; `../ec/annotations/call-graph.md` carries the
census and the summary, and `findings.md` §27 is the short version.

Every figure below is reproduced by a command named beside it, over committed
inputs. **Nothing here is a behavioural claim.** No register `status:` changed,
no `registers.yaml` row was added, and no live test ran: the counter, the three
cleared regions and the bank selects are static readings of committed bytes, and
where a row needs a machine to go further it says so.

## The four readings, and the three places the issue's prose does not survive the bytes

### `0x07F0` — six instructions, and a counter with three other writers

`ec/decompiled/common/07F0.asm` carries **six** instructions, not the seven the
issue lists, and the six it lists are right: `mov DPTR,#0x43`, `movx A,@DPTR`,
`inc A`, `movx @DPTR,A`, `movx A,@DPTR`, `ret`. It increments XDATA `0x0043`
and returns the stored value, re-reading rather than trusting the incremented
A — so a counter that has wrapped past `0xFF` still returns what is in the
byte. `07F0.c` agrees (`DAT_EXTMEM_0043 = DAT_EXTMEM_0043 + '\x01'; return
DAT_EXTMEM_0043;`).

**The three citing comments' reading of the callers reproduces, and the bytes
are more specific than the prose.** `common,0x012F`, `common,0x018C` and
`common,0x029B` each say the routine "polls 0x07F0 until it returns 5, writing 0
to 0x0043 and 0x200B on each pass". Read out of the firmware, all three sites
are the same shape, and the value is 0 in both cases — but the two bytes are
written at different moments:

```
0146  e4          clr   a
0147  90 00 43    mov   dptr,#0x0043
014A  f0          movx  @dptr,a          <- 0x0043, once, before the loop
014B  90 17 0a    mov   dptr,#0x170a
014E  e0          movx  a,@dptr
014F  20 e0 10    jb    acc.0,0x0162
0152  e4          clr   a
0153  90 20 0b    mov   dptr,#0x200b
0156  f0          movx  @dptr,a          <- 0x200B, on every pass
0157  12 07 f0    lcall 0x07f0
015A  b4 05 ee    cjne  a,#0x05,0x014b  <- back to the bit-0 test
```

`0x018C` repeats it at `0x01A4`/`0x01B0` over `0x1709` and `0x029B` at
`0x02B3`/`0x02BF` over `0x1708`, byte for byte apart from the channel byte and
the `jb` displacement. So the loop re-tests the channel byte's bit 0 on every
pass and clears `0x200B` each time, while `0x0043` is cleared once on entry —
"on each pass" is right about `0x200B` and one step late about `0x0043`. That
is a reading of the callers, not of this function, and it is recorded here
rather than in the row, which stays on its own six instructions.

**Neither address has a `registers.yaml` row, and the scans are committed here
so a follow-up does not have to re-run them.** `0x0043` and `0x200B` have no
entry in `../ec/annotations/registers.yaml` — the file's 155 rows carry no
address at all in `0x0000`-`0x00FF` and none in `0x9000`-`0x909F` — and
`../ec/ghidra/xdata-symbols.csv` has no symbol for either. Both addresses are
EC-side rather than PD-side, so the `no entry` claim in the `0x07F0` row is the
kind `build_ec_decompile.py`'s `stale_no_entry_claims` check polices and
currently holds:

```
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x0043 0x200B
0x0043  refs=4     ec=4     pd=0     referenced   0x0043
0x200B  refs=18    ec=18    pd=0     referenced   0x200B

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0043 0x200B --counts-only
0x0043: 4 direct MOV DPTR site(s)  common=4
0x200B: 18 direct MOV DPTR site(s)  bank0=3  bank1=4  common=11
```

`0x0043` is written at four sites and the only reads of it anywhere in the
image are this function's two — `common` `0x0147`, `0x01A4` and `0x02B3` (three
bare `movx @dptr,a`, each immediately preceded by its own `clr a`) and `0x07F0`.
**`0x200B` is written at all eighteen and read at none**, which is the more
interesting of the two: it is a sink. The three sites
that pair it with `0x07F0` are `0x0153`, `0x01B0` and `0x02BF`, the poll loops
above. The rest are `common` `0x02CC` and `0x07B7` (seven consecutive
`movx @dptr,a`), `0x10F2` (four, then `ret`), `0x2AC2` (seven), `0x362A`
(one), `0x3E53` (three), `0x50CE` and `0x51B8` (four each); `bank0` `0x8649`
(six, then `ret`), `0xBF3D` (two), `0xD7A5` (one, after a `clr a`); and
`bank1` `0xA560`, `0xA571` and `0xA58D` (one each, then `djnz r5,-8`) and
`0xC545` (one, then `djnz r7,-8`). The full per-site table is one command
away:

```
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0043 0x200B --csv
```

**Why this change does not add the rows.** Issue #558 made adding them
conditional ("if a row is genuinely warranted, change it in the same PR as the
evidence"), and they are not added here. `ghidra-functions.csv` rows name
functions; a `registers.yaml` row is a claim about a register, and the
immediately preceding tranche set the precedent in `call-graph.md` §"What is
left": *"Naming a helper is not a finding about a register."* Both addresses
would be `present-untested` on this evidence, which is what a row records
before anything has been observed — and a row is a standing invitation to read
the byte as a register, on a sweep-only census with a documented
indirect-addressing blind spot. Adding one also drags the generated
`xdata-symbols.csv` and renames `DAT_EXTMEM_0043` across the `.c` export. The
counts above are the input a follow-up needs, so the next issue does not
re-read anything; it only has to decide the status.

### `0x0F75` — three loops, and the issue describes two of them and bounds the third wrongly

`ec/decompiled/common/0F75.asm` carries **33** instructions in **49 bytes**, and
**three** clear loops. The issue's reading is quoted first because two of its
three bounds do not survive the bytes:

> 35 instructions: `mov R7,#0x20`, `DPTR=0`, a compare-and-store loop that
> clears `0x0000`-`0x001F`, then `DPTR=0x9000` and a second loop clearing
> `0x9000`-`0x9097`.

What the bytes say, loop by loop. **All three bound on the pointer's _high_
byte, not its low one**, and the loop the issue omits entirely is the one that
clears *internal* RAM rather than XDATA.

| loop | bytes | bound | clears | issue said |
|---|---|---|---|---|
| 1 | `0F75`-`0F85` | `DPH < 1` | XDATA `0x0000`-`0x00FF`, 256 bytes | `0x0000`-`0x001F`, 32 bytes |
| 2 | `0F87`-`0F93` | `R7 < 0xC0` | **internal** RAM `0x20`-`0xBF`, 160 bytes | *not mentioned* |
| 3 | `0F95`-`0x0FA3` | `DPH < 0x98` | XDATA `0x9000`-`0x97FF`, 2048 bytes | `0x9000`-`0x9097`, 152 bytes |

Loop 1 seeds R7 with `0x20` and then never uses R7: its counter is R4, loaded
from DPH every iteration, and the exit is `subb A,#0x1` / `jnc`. It stops when
DPH reaches 1, which is at DPTR `0x0100`, so it clears the whole first XDATA
page. **`0x20` is loop 2's counter seed, not loop 1's bound** — the 32-byte
reading is the one a reader gets by reading the first `mov` as the first loop's
limit.

Loop 2 is `mov A,R7; clr C; subb A,#0xC0; jnc` around
`xch A,R0; mov A,R7; xch A,R0; clr A; mov @R0,A; inc R7`. The `xch` pair is the
compiler idiom for `R0 = R7` (the first `xch` parks the old R0 in A, the second
puts R7 into R0 and the old R0 back in A, which the `clr A` then discards), and
`mov @R0,A` is the **indirect internal** form, so this clears internal RAM —
`DAT_INTMEM_20` is what the `.c` calls it — and leaves R7 at `0xC0`.

Loop 3 loads `DPTR,#0x9000`, copies DPH into R6 and compares that against
`0x98`. **`0x98` is 152, and the span is not 152 bytes**: the compare is on the
high byte of a pointer that the loop advances a byte at a time, so the loop runs
from `0x9000` until DPH reaches `0x98`, which is `0x9800` — 2,048 bytes. The
152-byte reading is what a *low*-byte compare on the same immediate would give,
and that is the compare the code does not perform. This is the same class of
slip as loop 1's 32, and it is the reason the row names the three regions with
their byte ranges rather than the immediates that produced them.

`0F75.c` agrees on all three, independently: its first loop runs
`for (puVar3 = (undefined1 *)0x0; (char)((ushort)puVar3 >> 8) == '\0'; ...)`, its
second `for (; puVar1 < (undefined1 *)0xc0; ...)` over `DAT_INTMEM_20`, and its
third the same high-byte test against `0x98`. Two committed readings that
agree with each other against the issue's prose is the check that the prose is
what is wrong.

**Its trailing `return bVar2 + 0x68;` is a loop-exit artifact, not a returned
value.** `bVar2` is the last high-byte compare, the function ends in `ret`, and
there is no value in A to read: the `.asm` has no return value, which is the
same reason `158E.c`'s and `1594.c`'s trailing `return;` is not one either.

**What the three regions are cleared *for* is not decoded, and the call site
supports nothing more than where it sits.** The single inbound site is the
`lcall 0x0F75` at `../decompiled/common/0070.asm:13`, inside the row already
named `reset_entry_stack_bank0_then_code_init`. That places it between the
`lcall 0x158E` and the `lcall 0x1594` in Keil startup, which is a statement
about the call site's position and not about the loops' purpose. The row says
"not decoded" and stops there.

### `0x158E` and `0x1594` — the same two instructions, and a `.c` that is wrong about their shape

`158E.asm` and `1594.asm` are two instructions each: `mov DPTR,#0xD89F` /
`#0xD96C`, then `ljmp 0x1100`. They are the BL51 cross-bank select shape that
`common,0x1100`'s own row describes, and the shape of their immediate
neighbours `0x159A` (`load_dptr_c251_tail_jump_1100`) and `0x1636`
(`load_dptr_d991_tail_jump_1100`), so both take the same name form.

**Both `.c` files show a `return;` that the listing does not have.**
`158E.c` reads `bl51_bank_select_0(0xd89f); return;` and `1594.c` reads
`bl51_bank_select_0(0xd96c); return;`. There is no `ret` in either `.asm`:
the trailing `return;` is the decompiler reading the tail `ljmp` as a call and
then the function end as a return. The `.asm` is right, as its own header says.
The rows do not repeat the `.c`'s call-and-return shape, and the `.c` files are
left as the machine emitted them — correcting a decompile is a separate step
from naming a function, and the row is where the correction lives.

**Both immediates are bank-0 addresses, and the issue's `#465` does not
resolve.** A repo-wide search for `465` and for the bank the stub actually
selects finds no such issue; the method the issue is reaching for — read a BL51
forwarder's `imm16` in the bank the stub selects, not the bank the stub sits in
— is **issue #255**, written up at `../ec/annotations/xdata-06c2-06db-timers.md`
§4 and carried in the `bank1,0x19A8` row, which also records that its
48-forwarder census was **not** re-measured against bank 0. So both `0xD89F`
and `0xD96C` are bank-0 addresses even though the stubs are common-area, and
nothing here re-runs that census.

**The citation and the byte scan agree, independently.**
`../ec/annotations/bank-call-targets.csv:24` and `:26` carry the `lcall 0x158E`
at `common 0x007C` and the `lcall 0x1594` at `0x0082`; `../decompiled/common/0070.asm:12`
and `:14` are those same two `lcall`s. Each stub has one inbound site.

## The boundary, and the two bytes the plan expected to be unowned

The four `.asm` headers each carried the census caveat ("this boundary is a
hypothesis and the instructions below may not be the whole function") because
they were un-annotated. Each was checked against `../decompiled/index.csv`, and
all four are hard ends:

| addr | index size | ends at | that address is | evidence |
|---|---|---|---|---|
| `0x07F0` | 8 | `0x07F8` | its own row `FUN_CODE_07f8` | `ret` at `0x07F7` **and** the next index row |
| `0x0F75` | 49 | `0x0FA6` | its own row `FUN_CODE_0fa6` | `ret` at `0x0FA5` **and** the next index row |
| `0x158E` | 6 | `0x1594` | `0x1594`'s own row | the 6-byte trampoline grid runs unbroken; the listing's own `ljmp` covers all six bytes |
| `0x1594` | 6 | `0x159A` | the already-named `load_dptr_c251_tail_jump_1100` | grid continues, successor annotated |

**`0x1592`-`0x1593` are not a gap, and the plan's expectation that they might
be undecidable is wrong in a way worth recording.** They carry no listing line
and no index row, which is the shape a genuine un-owned run would have — so
they were read out of the committed firmware rather than reasoned about. At
file offset `0x1592` of `ec/firmware/GMxMGxx_11.800` they are **`11 00`**, the
second and third bytes of `0x158E`'s own `ljmp 0x1100` at `0x1591`. The
six-byte size the index carries for `0x158E` already covers them; the listing
just prints a three-byte instruction on one line. This is the one place in the
four where the census caveat could genuinely have bitten, and it does not:

```
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x158E -n 12
0x0158e  90d89f   mov  dptr,#0xd89f
0x01591  021100   ljmp 0x1100
0x01594  90d96c   mov  dptr,#0xd96c
0x01597  021100   ljmp 0x1100
0x0159a  90c251   mov  dptr,#0xc251
...
```

Six bytes apart, unbroken, with no un-owned run anywhere in the run. The
`0x158E` row records it; the `0x1594` row records that its successor is
annotated, which is a cleaner end still.

## The follow-up, in the exact form it should be filed in

**Seeding `0xD89F` and `0xD96C` was a separate issue, and the issue's framing of
it is one correction away from right.** The issue says the two immediates "have
no listing, no index row and no mention anywhere in the tree". The first two
halves are right and the third is not: the immediates *do* appear, in
`158E.asm:9` and `1594.asm:9` and in the two `.c` files. What they have is no
row or listing **in their own right**. And per #255's method they resolve in the
bank the stub selects, so a follow-up seeds **`bank0`** rows at `0xD89F` and
`0xD96C` — not `common` ones, which is the same category error #255 corrected
in nine rows.

**The follow-up is now issue #559, and it has read both; the two paragraphs
above are what it was filed with.** It is written up at
`reset-vector-dptr-targets.md` and summarised in `../findings.md` §26. The
answers are not the ones this section predicted: `0xD89F` is a single `ret` byte
and `0xD96C` is a 0x25-byte routine clearing XDATA `0x0100`–`0x0FFF` except the
`0x07FD`–`0x07FF` cluster, both scoring 24 of 24 on `disasm8051.py --converge`.

**This section's stated reason for deferring the seeding is wrong, and #559 is
the correction.** It says seeding a function needs `--mode rebuild-project`, and
that two branches rebuilding the EC project cannot merge. It does not:
`--mode export-only` copies the committed project to scratch, seeds the copy's
functions from `ghidra-functions.csv` and exports from it, and the committed
`.rep` is never opened for writing — so there is no binary diff and no
`.gitattributes` `binary -diff -merge` refusal, and an EC seeding change *can*
merge alongside another. #559 seeded both this way, with
`annotations_unmatched 0`. `--mode rebuild-project` remains the right answer to
a *different* question — a seed that reports `annotations_unmatched`, meaning
the address has no function in the project at all — which is not what these two
were.

What still holds, and what #559 did not change: **neither address has a
committed row or listing**, and neither stub's row claims what the target holds.
#559 defers the two rows and their listings for its own reason —
`verify_reassembly.py --check` goes red on a fresh export without the pinned
`sdas8051` toolchain — not because the seeding was impossible here.

## The export this change regenerates had been one commit stale

Worth its own section, because it is why the diff is larger than four rows.

`ec/decompiled/` was last re-exported by `0b04a8b9` (issue #503). The next
commit, `a1d79a89` (issue #250, PR #504), changed
`../ec/ghidra/xdata-symbols.csv` — nine new symbols, which renames
`DAT_EXTMEM_1c03` to `XDATA_1C03` and eight others — and added three rows to
`ghidra-functions.csv` (`bank1,9CE8`, `bank1,9D53`, `bank1,E2D3`), **without
re-exporting**. `--check` does not catch that: it holds the `.c` headers against
`index.csv` and both against the annotations internally, and both were
self-consistent in the stale name.

So the first re-export since picks up seven rows, not four, and `c-digests.csv`
moves 38 rows rather than 4. **The seven are the four this tranche names and
the three #250's CSV already carried.** Nothing was hand-edited to achieve it
and nothing was reverted: the `.asm` instruction bodies are byte-identical
across the whole diff (`git diff --unified=0 -- 'ec/decompiled/*/*.asm'` shows
only header lines changing), the extra `.c` changes are the symbol rename, and a
second `--work` re-export leaves `git status` clean. The census in
`call-graph.md` moved by the seven, and every figure in it is the tool's
printed output.

## What this change does not do

- **No live or behavioural test.** Confirming what the `0x0043` counter counts,
  what clearing those three regions achieves, or what the two bank selects buy
  the reset path needs the physical machine. This PR's rows stop at what the
  bytes support.
- **No `registers.yaml` row for `0x0043` or `0x200B`**, for the reasons above,
  and no `status:` anywhere moves. `../ec/ghidra/xdata-symbols.csv` is
  generated from that file and is unchanged — `gen_xdata_symbols.py` is a no-op
  on this tree.
- **No `--mode rebuild-project`**, so no Ghidra database is written. The
  `.rep`/`.gpr` in `../ec/ghidra/project/` are untouched.
- **The seven `bank1` ff-fill rows that name these three addresses inside
  bodies their own comments record as unsupported are not edited.**
  `citation_callers.py` already refuses those 21 pairs as `fill-at-citer`, and
  substituting a name there would assert the very call the comment denies —
  `call-graph.md` §"The citing comments keep their bare addresses, on purpose".
  `common,0x0070`'s comment already records its four calls supportively, and
  `common,0x110A` and `common,0x00CF` already carry the artifact-citation
  caveat; all three are left as they are.
- **The `.c` bodies are not improved.** `0F75.c`'s phantom
  `return bVar2 + 0x68;` and the two stubs' phantom `return;` stay as the
  machine emitted them. The comment is where the correction lives.
- **Nothing upstream.** The mission's eventual `Wer-Wolf/uniwill-laptop` /
  `tuxudo-drivers` PR (issue #10) is not this issue's deliverable, and no
  stage may open one; a prepared patch and description in this repository is
  the form any such work takes.
