# The `bank0` `0x8038` handlers as control flow

[`bank-call-audit.md`](bank-call-audit.md) §9 decodes the eight handlers this
table dispatches to as "one handler written eight times", and says so about the
limits of that reading: each row of its per-case table is **a linear decode of
the window between one target and the next, not a control-flow trace of the
handler**, and "a `charge-profile-flow.md`-grade walk of eight handlers is a
separate piece of work". This is that walk, for the eight cases `0x00`-`0x07`,
the shared epilogue at `0x821F` and the default at `0x8274`. §9's own
paragraph standing next to its table records what the walk changed; this file
carries the detail.

Everything below is **what the bytes in
[`ec/firmware/GMxMGxx_11.800`](../firmware/GMxMGxx_11.800) decode to**. Nothing
here was run on hardware, no register was read back, no execution order or
timing is claimed, and no `status:` in [`registers.yaml`](registers.yaml)
moves. The only committed inputs are that image, the committed
`ec/decompiled/bank0/*.asm` listings (the byte-of-record, cited by path rather
than re-derived) and the committed CSVs named per section.

### What the walk changed, and what it did not

[`bank-call-audit.md`](bank-call-audit.md) §9 carried a paragraph beside its
per-case table saying the table was a linear decode and that a control-flow walk
might find a body reaching past its window. This is that walk's result, and it
is recorded there in the same §4a-4d form. In short:

- **The per-case table stands.** All eight rows — target, gate, word slot, byte
  pair, `0x0610` bit, distinct helpers — are confirmed by the walk. Nothing in
  §4 corrects a column.
- **Two bodies reach past their window** (§4): case `0x05` by the `sjmp` at
  `0x81DD`, case `0x07` by falling into `0x8274`. Neither changes the
  attribution.
- **One value is wrong.** §9's "leaves with `a` holding `0x81 + case`" holds for
  cases `0x00`-`0x06` and not for `0x07`, whose immediate at `0x826C` is
  `0x80` (§4.8).
- **One shape is more uniform than §9 could see, and one is less.** The
  bit-7-clear arm is a single `ljmp 0x8274` in all eight, which a linear decode
  of the windows could not have shown (§3); but the bit-7-set arm leaves in
  three distinct shapes, not one (§3, §4).
- **The question the issue's item 3 turns on does not have the answer it
  assumed.** Bit 7 of a gate byte is set by every arming site in the walk
  (§6.3, §7), so "whoever sets bit 7 decides whether a channel runs" cannot be
  answered in that form from these bytes.

## 1. Reproducing it

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x1904 0x1906 0x1909 0x190C --callee-depth 1 --csv \
          > ec/annotations/bank0-8038-handler-arms.csv
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
          0x1904 0x1906 0x1909 0x190C 0x0610 0x08D0 0x08D2 0x08D4 0x08D6 \
          0x08D8 0x08DA 0x08DC 0x08DE 0x0600 0x0601 0x0602 0x0603 0x0604 0x0605 \
          0x0606 0x0607 0x0608 0x0609 0x060A 0x060B 0x060C 0x060D 0x060E 0x060F \
          0x0A59 --csv
```

The sixteen `0x0600`-`0x060F` addresses are **all eight accumulator pairs**,
not a sample of them. An earlier draft of this command named `0x0600` and
`0x060E` only, and the consumer count §9 reported rested on them: two of its
three came from the scan of `0x060E`, and the third, `bank1,0xB728`, from the
census's row for `0x060A`. The shortfall was in the scan, not in the census —
it already named consumers of the other six pairs that this document did not
report. §9.1 is the account, and it is the reason the command reads this way
now.

All eight handlers open with `mov dptr,#<gate>` and branch on bit 7 of the byte
they just read, so seeding `walk_branch_arms.py` on the four gate bytes reaches
every handler **and** the `0x1904` site inside the default's own neighbourhood
(§7). Every load-bearing excerpt below is re-checked against the bank image its
own command builds, with `r2 -a 8051`, and that command is printed beside it —
which is why the `bank1` transcripts in §9 need the `0x10000` offset above
rather than the `0x08000` one.

[`bank0-8038-handler-arms.csv`](bank0-8038-handler-arms.csv) is the per-arm
table `--csv` writes: 18 `arm` rows and 63 `callee` rows. **All 18 arms report
`status: complete`** — none hit the depth limit, the instruction budget, the
indirect-jump cut or the end-of-image cut, which is what lets the negatives
below be stated without a hedge. Sixteen of those arms are the eight handlers'
two arms each; the other two are the `0x82D8` site of §7.1. The doc-plus-CSV
shape is the one [`xdata-0400-045f.md`](xdata-0400-045f.md)/`.csv` established.

## 2. The dispatch site, and the one edge no byte scan can see

The table sits immediately after the `lcall` at `0x8035`, and the callee pops
the return address the call pushed into DPTR, so the pointer to the table is
never an immediate. §9 reads the whole entry layout off the reader at `0x7151`
and retires three "corroborating" edges in [`bank-call-targets.csv`](bank-call-targets.csv)
as phantoms; that is §9's work and it stands. What the walk adds is only this:
the dispatch itself is the computed `jmp @a+dptr` at `0x716B`, `a` cleared at
`0x716A`, and **no byte scan in this repository resolves an edge out of it**,
because the `73` opcode carries no displacement. That is the only path into the
eight handlers found by reading, and it is why §8 below ends where it does.

The selector is XDATA `0x08E0`, read at `0x8034` immediately before the call.

## 3. The shared skeleton, and the two shapes its arms take

Every case opens identically — load the gate, read it, test bit 7 — and then
splits into two arms. Case `0x00`, verbatim from the image:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8054; pd 4' /tmp/bank0.bin
            0x00008054      901904         mov dptr, #0x1904
            0x00008057      e0             movx a, @dptr
        ┌─< 0x00008058      20e703         jb acc.7, 0x805e
       ┌──< 0x0000805b      028274         ljmp 0x8274
```

**The bit-7-clear arm is one instruction in all eight cases**: a three-byte
`ljmp 0x8274` at `0x805B` / `0x809B` / `0x80DE` / `0x8121` / `0x8164` / `0x81A4`
/ `0x81E6`, and — case `0x07` is the exception and §4.8 has it — the branch
itself is spelled `jnb` rather than `jb`, so the same edge is the *taken* one.
The walk reports all eight of these arms `complete` with no XDATA access and one
callee, `0x8274`.

**Six of the eight bit-7-set arms are a single linear block** — one entry, no
internal branch — of 26 to 35 instructions. The two exceptions are `0x05` and
`0x07`, two blocks each: `0x05` runs 27 instructions to its `sjmp` and 9 more
from `0x821F`, `0x07` 35 to the `ret` at `0x827D` and 9 more from `0x827E`, and
the `jz` at `0x8278` is inside `0x07`'s first block. Cases `0x00`-`0x04` have
one distinct shape, and cases `0x05`-`0x07` differ from it and from each other
in how they leave, which is the first thing the linear window decode folds
together. The four shapes:

| leaving the bit-7-set arm | cases | evidence |
|---|---|---|
| `ljmp 0x821F` (3-byte) | `0x00` `0x01` `0x02` `0x03` `0x04` | `0x8091` `0x80D4` `0x8117` `0x815A` `0x819A` |
| `sjmp 0x821F` (2-byte, PC-relative) | `0x05` | `0x81DD` |
| no transfer at all — falls through into `0x821F` | `0x06` | `0x821D` `mov a,#0x87` is immediately followed by `0x821F lcall 0xbb08` |
| `lcall 0xBCB1` then falls through into the default | `0x07` | `0x8271`, `0x8274` |

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x81db; pd 2' /tmp/bank0.bin
            0x000081db      7486           mov a, #0x86
        ┌─< 0x000081dd      8040           sjmp 0x821f
```

Case `0x05`'s shape is the only one of the four that leaves by a PC-relative
edge, and the only `sjmp` in any of the eight. The PC-relative census does
carry that edge: [`bank-relative-branch-targets.csv`](bank-relative-branch-targets.csv)
resolves `0x081DD` to `0x821F` as `target_class: entry`, with 21 of 24 framings
putting an instruction start there — the family
[`bank-call-audit.md`](bank-call-audit.md) §8 counts, `sjmp` first in it. What a
linear window read cannot do is *act* on that row: §9's window for case `0x05`
is `0x819D`-`0x81DE`, which ends at the `sjmp` with nothing to follow (§4). Case
`0x07` leaves its window with no branch at all, running past `0x8273` into the
default. The `0x06` fall-through is visible to nothing at all: no branch, no
call, no reference, just the next address.

**The three committed Ghidra entries inside case `0x00`'s window are listing
boundaries, not control-flow boundaries.** `8054.asm`, `805B.asm` and `806C.asm`
are three separate files, and `0x8048.asm` is a fourth
(`unresolved_midstream_bytes`); the walk finds the case's control flow to be
exactly **two** units: the one-instruction arm at `0x805B`, and one 26-instruction
linear block `0x805E`-`0x8093`. `0x806C` is an instruction start *inside* that
block, not a branch into it:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8069; pd 4' /tmp/bank0.bin
            0x00008069      900600         mov dptr, #0x0600
            0x0000806c      e0             movx a, @dptr
            0x0000806d      900a59         mov dptr, #0x0a59
            0x00008070      f0             movx @dptr, a
```

The `unresolved_midstream_bytes` at `0x8048` sits **inside the jump table, not
beside it**: `0x8048` is the second byte of entry 5, the `81 9d 05` at
`0x8047`-`0x8049` that carries case `0x05`'s address. The eight entries run
`0x8038`-`0x804F`, the `00 00` terminator is at `0x8050`, the default address
field is `0x8052`-`0x8053`, and case `0x00`'s first instruction is `0x8054` —
so there are **no bytes at all** between the default field and that
instruction, and an earlier draft of this sentence described seven that are not
there. The committed `8048.c` calls its own decoded items "Seven bytes" over
the `0x8048`-`0x8053` span, which is that file's wording about its items rather
than a count of the span; §9's `px 32` transcript at
`../annotations/bank-call-audit.md:1053` is where the bytes are, and it shows
them as table contents. The walk never reaches any of them from any of the
eighteen arms, and that conclusion is unchanged.

## 4. The per-case walk

`window` is the span §9's linear decode was working over — target to next
target, from [`bank0-8038-dispatch-table.csv`](bank0-8038-dispatch-table.csv).
`blocks` is what the walk decoded, arm by arm. Both span columns are byte
extents: the second address is the **last byte** of the span, so a span ending
in a three-byte `ljmp` ends two past that `ljmp`'s own address. `leaves via`
names the instruction itself, so it is that instruction's start.

| case | target | window §9 used | bit-7-set arm reaches | leaves via |
|---:|---|---|---|---|
| `0x00` | `0x8054` | `0x8054`-`0x8093` | `0x805E`-`0x8093`, 26 insn, 1 block | `0x8091 ljmp 0x821F` |
| `0x01` | `0x8094` | `0x8094`-`0x80D6` | `0x809E`-`0x80D6`, 27 insn, 1 block | `0x80D4 ljmp 0x821F` |
| `0x02` | `0x80D7` | `0x80D7`-`0x8119` | `0x80E1`-`0x8119`, 27 insn, 1 block | `0x8117 ljmp 0x821F` |
| `0x03` | `0x811A` | `0x811A`-`0x815C` | `0x8124`-`0x815C`, 27 insn, 1 block | `0x815A ljmp 0x821F` |
| `0x04` | `0x815D` | `0x815D`-`0x819C` | `0x8167`-`0x819C`, 26 insn, 1 block | `0x819A ljmp 0x821F` |
| `0x05` | `0x819D` | `0x819D`-`0x81DE` | `0x81A7`-`0x81DE` **and `0x821F`-`0x8230`**, 36 insn, 2 blocks | `0x81DD sjmp 0x821F` |
| `0x06` | `0x81DF` | `0x81DF`-`0x8230` | `0x81E9`-`0x8230`, 35 insn, 1 block | none — the block *contains* `0x821F`-`0x8230` |
| `0x07` | `0x8231` | `0x8231`-`0x8273` | `0x8238`-`0x8293`, 44 insn, 2 blocks | `0x8271 lcall 0xBCB1`, then falls into `0x8274` |

**Two of the eight reach past the window §9 used, and neither changes what §9
attributes to its case.** Case `0x05` is the one the issue anticipated: the
`sjmp` at `0x81DD` lands in the epilogue, which lies inside case `0x06`'s
window, so a linear decode of `0x819D`-`0x81DE` ends at a `sjmp` with nowhere
to go. Case `0x07`'s block continues past its window into `0x8274`'s two arms.
Cases `0x00`-`0x04` and `0x06` stay inside their own window.

### 4.1 Case `0x00` — `0x8054`

The shape all eight share, and the one §9's skeleton paragraph is a linear read
of. Taken arm, in full:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x805e; pd 26' /tmp/bank0.bin
            0x0000805e      12b9df         lcall 0xb9df
            0x00008061      9008d0         mov dptr, #0x08d0
            0x00008064      ee             mov a, r6
            0x00008065      f0             movx @dptr, a
            0x00008066      a3             inc dptr
            0x00008067      ef             mov a, r7
            0x00008068      f0             movx @dptr, a
            0x00008069      900600         mov dptr, #0x0600
            0x0000806c      e0             movx a, @dptr
            0x0000806d      900a59         mov dptr, #0x0a59
            0x00008070      f0             movx @dptr, a
            0x00008071      900601         mov dptr, #0x0601
            0x00008074      12b965         lcall 0xb965
            0x00008077      900601         mov dptr, #0x0601
            0x0000807a      f0             movx @dptr, a
            0x0000807b      900a59         mov dptr, #0x0a59
            0x0000807e      e0             movx a, @dptr
            0x0000807f      900600         mov dptr, #0x0600
            0x00008082      f0             movx @dptr, a
            0x00008083      900610         mov dptr, #0x0610
            0x00008086      e0             movx a, @dptr
            0x00008087      4401           orl a, #0x01
            0x00008089      12ba3d         lcall 0xba3d
            0x0000808c      12be7e         lcall 0xbe7e
            0x0000808f      7481           mov a, #0x81
        ┌─< 0x00008091      02821f         ljmp 0x821f
```

Five steps: load the source word into `r6:r7` (§6), copy it into the word slot
`0x08D0`/`0x08D1` with `r6` at the lower address, fold the accumulator pair
`0x0600`/`0x0601` through `0xB965` (§5), set bit `0x01` of `0x0610` through
`0xBA3D`, and re-arm the gate through `0xBE7E`. The `movx @dptr,a` at `0x8082`
is followed by a `mov dptr` with no intervening read, so DPTR is still `0x0600`
and the store lands there; the byte `0x0A59` is the one just stored at
`0x8070`.

### 4.2 Case `0x01` — `0x8094`

Identical shape, first `lcall` `0xBDAE`, second `lcall 0xB9EA` (cases `0x01`,
`0x02`, `0x03`, `0x05`, `0x06`, `0x07` all carry the second one; cases `0x00`
and `0x04` do not). Slots `0x08D2`/`0x08D3`, pair `0x0602`/`0x0603`, `orl a,#0x02`
at `0x80CA`, gate helper `0xBB9A`, `mov a,#0x82` at `0x80D2`, `ljmp 0x821F` at
`0x80D4`. §9's row for this case is confirmed on every column.

### 4.3 Case `0x02` — `0x80D7`

`0xBDBA` then `0xB9EA`; slots `0x08D4`/`0x08D5`, pair `0x0604`/`0x0605`,
`orl a,#0x04` at `0x810D`, gate helper `0xBE88`, `mov a,#0x83` at `0x8115`,
`ljmp 0x821F` at `0x8117`. §9's row confirmed.

### 4.4 Case `0x03` — `0x811A`

`0xBDC6` then `0xB9EA`; slots `0x08D6`/`0x08D7`, pair `0x0606`/`0x0607`,
`orl a,#0x08` at `0x8150`, gate helper `0xBE92`, `mov a,#0x84` at `0x8158`,
`ljmp 0x821F` at `0x815A`. §9's row confirmed.
[`bank-call-audit.md`](bank-call-audit.md) §4's separate note that `0x811A`
also decodes as plausible code in `bank1` is untouched: everything here is a
`bank0` reading of the `bank0` image.

### 4.5 Case `0x04` — `0x815D`

`0xB9DF` alone, as case `0x00`; slots `0x08D8`/`0x08D9`, pair
`0x0608`/`0x0609`, `orl a,#0x10` at `0x8190`, gate helper `0xBE7E`, `mov a,#0x85`
at `0x8198`, `ljmp 0x821F` at `0x819A`. §9's row confirmed — and note the
source word is the *same* `0x1918` case `0x00` reads (§6), which is the first of
the four pairings the gate table already implied.

### 4.6 Case `0x05` — `0x819D`

The two-block case. `0xBDAE` then `0xB9EA`; slots `0x08DA`/`0x08DB`, pair
`0x060A`/`0x060B`, `orl a,#0x20` at `0x81D3`, gate helper `0xBB9A`, `mov a,#0x86`
at `0x81DB`, and then `0x81DD sjmp 0x821F` into the epilogue at `0x821F`-
`0x822E`. §9's row is confirmed on every column; the *exit shape* is not the
`ljmp` the other five use, and a linear decode of `0x819D`-`0x81DE` cannot see
where that `sjmp` goes. §9 separately records `bank1,0xB728` as the consumer of
this case's accumulator — §9 below.

### 4.7 Case `0x06` — `0x81DF`

The fall-through case, and the only one whose bit-7-set block contains the
epilogue rather than reaching it by any transfer. `0xBDBA` then `0xB9EA`; slots
`0x08DC`/`0x08DD`, pair `0x060C`/`0x060D`, `orl a,#0x40` at `0x8215`, gate helper
`0xBE88`, `mov a,#0x87` at `0x821D` — and the next address, `0x821F`, is the
epilogue's first instruction. §9's row is confirmed on every column.

### 4.8 Case `0x07` — `0x8231`

The one case whose branch is spelled the other way round, and the one with no
committed listing:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8231; pd 4' /tmp/bank0.bin
            0x00008231      90190c         mov dptr, #0x190c
            0x00008234      e0             movx a, @dptr
        ┌─< 0x00008235      30e73c         jnb acc.7, 0x8274
        │   0x00008238      12bdc6         lcall 0xbdc6
```

`jnb acc.7,0x8274` sends **bit 7 clear** to the default and lets bit 7 set
continue — the same split as the other seven, taken the other way round, so the
CSV's `arm` column reads `taken` for what is semantically the clear arm. The
body is `0xBDC6` then `0xB9EA`; slots `0x08DE`/`0x08DF`, pair `0x060E`/`0x060F`,
`orl a,#0x80` at `0x8264`, gate helper `0xBE92`, then `0x826C mov a,#0x80`,
`0x826E lcall 0xBB08`, `0x8271 lcall 0xBCB1` and a fall-through into `0x8274`.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x826a; px 6' /tmp/bank0.bin
- offset -   0 1  2 3  4 5  6 7  8 9  A B  C D  E F  0123456789ABCDEF
0x0000826a  be92 7480 12bb                           ..t...
```

**`0x826C` is `74 80` — `mov a,#0x80`, not `0x88`.** §9's skeleton paragraph
says the handlers leave "with `a` holding `0x81 + case`"; that holds for cases
`0x00`-`0x06` (`0x81` `0x82` `0x83` `0x84` `0x85` `0x86` `0x87`) and does not
hold for `0x07`, whose immediate is `0x80`. The correction is recorded beside
§9's table.

**No function is exported at `0x8231`.** There is no `ec/decompiled/bank0/8231.asm`
in the tree, and §9's blind-spot list already explains why: the only path in is
the computed `jmp @a+dptr` at `0x716B`. This section decodes the address from
the bank image and needs no listing. It is the second reason §9's blind spot is
real rather than a convenience, and it is why the row that would seed a
`bank0,0x8231` annotation is **deferred, not applied** — see *Left out* below.

## 5. The two helpers all eight share

### 5.1 `0xB965` — the accumulator fold

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xb965; pd 24' /tmp/bank0.bin
            0x0000b965      e0             movx a, @dptr
            0x0000b966      900a58         mov dptr, #0x0a58
            0x0000b969      f0             movx @dptr, a
            0x0000b96a      a3             inc dptr
            0x0000b96b      e0             movx a, @dptr
            0x0000b96c      2f             add a, r7
            0x0000b96d      ff             mov r7, a
            0x0000b96e      900a58         mov dptr, #0x0a58
            0x0000b971      e0             movx a, @dptr
            0x0000b972      3e             addc a, r6
            0x0000b973      c3             clr c
            0x0000b974      13             rrc a
            0x0000b975      fe             mov r6, a
            0x0000b976      ef             mov a, r7
            0x0000b977      13             rrc a
            0x0000b978      ff             mov r7, a
            0x0000b979      ee             mov a, r6
            0x0000b97a      f0             movx @dptr, a
            0x0000b97b      a3             inc dptr
            0x0000b97c      ef             mov a, r7
            0x0000b97d      f0             movx @dptr, a
            0x0000b97e      900a58         mov dptr, #0x0a58
            0x0000b981      e0             movx a, @dptr
            0x0000b982      22             ret
```

`0xB965` is entered with DPTR holding the **low** byte of the accumulator pair
(`0x0601`, `0x0603`, `0x0605`, `0x0607`, `0x0609`, `0x060B`, `0x060D`, `0x060F`
— one `lcall 0xB965` in each of the eight, at `0x8074`, `0x80B7`, `0x80FA`,
`0x813D`, `0x817D`, `0x81C0`, `0x8202`, `0x8251`). It reads it into `0x0A58`
and adds the 16-bit pair `0x0A58`/`0x0A59` to `r6:r7` — `0x0A58` into `r6`,
`0x0A59` into `r7`, the carry running from `0x0A59` to `0x0A58`. Which of
`r6`/`r7` is the high byte is settled by the shift and not by the add: `clr c ;
rrc a` runs twice, `r6` first and `r7` consuming the carry out of it, so `r6`
is the **low** byte of the sum and `r7` the high one. The carry out of the high
byte is discarded. It writes the result back to `0x0A58`/`0x0A59` in that same
order and returns the new low byte in `a`.

Written in the arithmetic the bytes perform, and with the byte order read off
the caller's own stores rather than assumed:

> the accumulator pair `P` := `(P + V) >> 1`, where `P` is 16-bit big-endian in
> `<high>:<low> = 0x0600:0x0601` (and the other seven pairs), `V` is the
> `r6:r7` word the handler just copied to its slot, big-endian in
> `<high>:<low> = 0x1918:0x1919` because `0xB9DF` leaves `r6` holding `0x1919`
> and `r7` holding `0x1918` (§6.1), and the floor of one bit is dropped.

The handler completes the round trip itself: `a` (the new low byte) goes back
to `0x0601`, and `0x0A59` (the new high byte) is copied to `0x0600`. **Nothing
in this repository establishes that the EC performs any filtering with it.** The
name "accumulator" here is for the shape — a value carried across calls and
halved against a fresh sample — and a write being accepted is not evidence the
EC acts on it.

### 5.2 `0xBA3D` and `0xBB08` — one bit of `0x1901`

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xba3d; pd 6' /tmp/bank0.bin
            0x0000ba3d      f0             movx @dptr, a
            0x0000ba3e      901901         mov dptr, #0x1901
            0x0000ba41      e0             movx a, @dptr
            0x0000ba42      54fe           anl a, #0xfe
            0x0000ba44      f0             movx @dptr, a
            0x0000ba45      22             ret
```

Both open with `movx @dptr, a`, storing whatever the caller had in `a` to
whatever address the caller had loaded — which is how `0xBA3D` comes to perform
the `0x0610` write §9 attributes to the handler, and why the walk's
`--callee-depth 1` rows credit `0xBA3D` with `0x1901 r+w` and the handlers with
`0x0610 read`. Then `0xBA3D` **clears** bit 0 of `0x1901` and `0xBB08` **sets**
it. `0xBA3E` is the same routine entered one byte later, skipping the store: it
is what the default calls at `0x827E` and what the `0x8294` block calls at
`0x82A1` and `0x8313`.

`0xBAFD` is a third entry into that family — `movx @dptr, a`, then
`0x1900 |= 0x03`, then the same `0x1901 |= 0x01`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xbafd; pd 13' /tmp/bank0.bin
            0x0000bafd      f0             movx @dptr, a
            0x0000bafe      901900         mov dptr, #0x1900
            0x0000bb01      e0             movx a, @dptr
            0x0000bb02      4402           orl a, #0x02
            0x0000bb04      f0             movx @dptr, a
            0x0000bb05      e0             movx a, @dptr
            0x0000bb06      4401           orl a, #0x01
            0x0000bb08      f0             movx @dptr, a
            0x0000bb09      901901         mov dptr, #0x1901
            0x0000bb0c      e0             movx a, @dptr
            0x0000bb0d      4401           orl a, #0x01
            0x0000bb0f      f0             movx @dptr, a
            0x0000bb10      22             ret
```

`0xBB08` is what remains of `0xBAFD` once the `0x1900` half is stepped over, so
the epilogue's "set bit 0 of `0x1901`" and the default's `0xBAFD` call are two
entries into one stretch of bytes. §7 has the callers.

## 6. The per-case helpers, and what the word slot holds

This is the issue's item 2, and the answer is not in the handlers: `r6`/`r7`
are loaded by the first one or two `lcall`s of each bit-7-set arm, and the
`lcall` targets are reached at byte offsets rather than at one shared entry.
`0xB9EA` is 11 bytes after `0xB9DF` and past that export's own last byte,
dropping into the `r6`/`r7` tail at `0xB9EF`-`0xB9F4`; and `0xBE7E`, `0xBE88`
and `0xBE92` are three ten-byte, `ret`-terminated entries of one shape that
the project happens to export separately, over a byte stream that runs on from
`0xBE7E` to `0xBE9B`. `0xBB9A` is that same ten-byte shape in a different
stretch, at `0xBB99`-`0xBBA3` — eleven bytes, the one longer because `0xBB99`
opens it with a store of the caller's `a`.

### 6.1 The two entry points into one word loader

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xb9df; pd 16' /tmp/bank0.bin
            0x0000b9df      901918         mov dptr, #0x1918
            0x0000b9e2      e0             movx a, @dptr
            0x0000b9e3      900a57         mov dptr, #0x0a57
            0x0000b9e6      f0             movx @dptr, a
            0x0000b9e7      901919         mov dptr, #0x1919
            0x0000b9ea      e0             movx a, @dptr
            0x0000b9eb      900a56         mov dptr, #0x0a56
            0x0000b9ee      f0             movx @dptr, a
            0x0000b9ef      e0             movx a, @dptr
            0x0000b9f0      fe             mov r6, a
            0x0000b9f1      a3             inc dptr
            0x0000b9f2      e0             movx a, @dptr
            0x0000b9f3      ff             mov r7, a
            0x0000b9f4      22             ret
            0x0000b9f5      9008cc         mov dptr, #0x08cc
            0x0000b9f8      e4             clr a
```

`0xB9DF` reads XDATA `0x1918` into the scratch byte `0x0A57` and `0x1919` into
`0x0A56`, then the shared tail at `0xB9EF` loads `r6` from `0x0A56` and `r7`
from `0x0A57`. `0xB9EA` is that routine entered at its `movx a,@dptr`: the
caller has already staged the high byte at `0x0A57` and left DPTR on the low
byte, so `0xB9EA` completes the same job for a *different* pair. The `lcall`
census over the bank image:

| address | `lcall` byte sites | what it reads into `0x0A57` |
|---|---|---|
| `0xB9DF` | `0x805E`, `0x8167` | `0x1918` |
| `0xB9EA` | `0x80A1`, `0x80E4`, `0x8127`, `0x81AA`, `0x81EC`, `0x823B` | whatever the staging `lcall` left at `0x0A57` |
| `0xBDAE` | `0x809E`, `0x81A7` | `0x1907` |
| `0xBDBA` | `0x80E1`, `0x81E9` | `0x190A` |
| `0xBDC6` | `0x8124`, `0x8238` | `0x190D` |

Each staging routine reads its byte, stores it to `0x0A57`, and **leaves DPTR
pointing at the low byte of the same word**, which is what makes the `0xB9EA`
that follows read the other half:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xbdae; pd 5' /tmp/bank0.bin
            0x0000bdae      901907         mov dptr, #0x1907
            0x0000bdb1      e0             movx a, @dptr
            0x0000bdb2      900a57         mov dptr, #0x0a57
            0x0000bdb5      f0             movx @dptr, a
            0x0000bdb6      901908         mov dptr, #0x1908
```

So, read off the bytes, with each word written `<high>:<low>` as §5.1 defines
the accumulator pair:

| case | source word `<high>:<low>` | gate | relation to the gate |
|---:|---|---|---|
| `0x00` | `0x1918`:`0x1919` | `0x1904` | elsewhere in the same page |
| `0x01` | `0x1907`:`0x1908` | `0x1906` | `gate + 1` |
| `0x02` | `0x190A`:`0x190B` | `0x1909` | `gate + 1` |
| `0x03` | `0x190D`:`0x190E` | `0x190C` | `gate + 1` |
| `0x04` | `0x1918`:`0x1919` | `0x1904` | same word as `0x00` |
| `0x05` | `0x1907`:`0x1908` | `0x1906` | same word as `0x01` |
| `0x06` | `0x190A`:`0x190B` | `0x1909` | same word as `0x02` |
| `0x07` | `0x190D`:`0x190E` | `0x190C` | same word as `0x03` |

**There are four distinct source words across eight cases, paired exactly the
way the four gate bytes are paired.** Each case still has its own accumulator
pair and its own bit in `0x0610`, so the shape is four words sampled into eight
independent accumulators — the reading the issue proposed, and it holds at the
byte level. It is worth being precise about what that is and is not: the
pairing is what the bytes show; *why* a word would be sampled twice is not in
this image.

### 6.2 What the `0x08D0`-`0x08DE` slot holds

The store is unconditional once the arm is taken — `mov dptr,#<slot> ; mov a,r6
; movx @dptr,a ; inc dptr ; mov a,r7 ; movx @dptr,a` — so `r6` is the **low**
byte at the slot's own address and `r7` the high byte at the next one up. Since
§6.1 already fixed `r6` as the low byte of the source word, the slot holds

> a straight 16-bit copy of the source word, low byte at the lower address:
> `0x08D0` = `0x1919`, `0x08D1` = `0x1918` for cases `0x00`/`0x04`;
> `0x08D2`/`0x08D3` = `0x1908`/`0x1907` for `0x01`/`0x05`; `0x08D4`/`0x08D5` =
> `0x190B`/`0x190A` for `0x02`/`0x06`; `0x08D6`/`0x08D7` = `0x190E`/`0x190D` for
> `0x03`/`0x07`; `0x08D8`/`0x08D9`, `0x08DA`/`0x08DB`, `0x08DC`/`0x08DD` and
> `0x08DE`/`0x08DF` repeating the first four in the same order.

The copy is the same 16-bit value `V` §5.1 names, laid down the other way
round: the source word sits in XDATA with its high byte at the *lower* address
(`0x1918` before `0x1919`) and the slot with its low byte there (`0x08D0`
before `0x08D1`), while the accumulator pair is big-endian like the source
(`0x0600` before `0x0601`). Two comparisons follow and they come out
differently: the slot against its source is one value byte-swapped, and the
slot against the accumulator pair is a different value in a different order —
which is what §5.1's `P := (P + V) >> 1` rests on.

**No byte in this image writes those sixteen addresses other than the eight
handlers themselves**, by the two scans in §1 — `trace_xdata_refs.py` finds one
direct `mov dptr` site per slot and no `movx a,@dptr` naming any of the sixteen
in either bank. (The odd bytes, `0x08D1` and `0x08DF` among them, get no direct
site of their own: they are written by the `inc dptr` after the first, which the
scan reports as a two-byte consecutive write. `0x08DE` does have a direct site,
`0x823E`; it is the *census* CSV that has no row for it, or for `0x08DF` above
it — §9.) So the slots are written here and, by these scans, read nowhere in the
committed tree. That is "not found by this method", not "unused": the walk is
byte-level, DPTR-tracking and bounded, and it cannot see a pointer handed to
another routine that this image's call graph does not name.

### 6.3 The four gate helpers are one rotating routine

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xbe7e; pd 20' /tmp/bank0.bin
            0x0000be7e      901904         mov dptr, #0x1904
            0x0000be81      749f           mov a, #0x9f
            0x0000be83      f0             movx @dptr, a
            0x0000be84      901906         mov dptr, #0x1906
            0x0000be87      22             ret
            0x0000be88      901909         mov dptr, #0x1909
            0x0000be8b      749f           mov a, #0x9f
            0x0000be8d      f0             movx @dptr, a
            0x0000be8e      90190c         mov dptr, #0x190c
            0x0000be91      22             ret
            0x0000be92      90190c         mov dptr, #0x190c
            0x0000be95      749f           mov a, #0x9f
            0x0000be97      f0             movx @dptr, a
            0x0000be98      901904         mov dptr, #0x1904
            0x0000be9b      22             ret
            0x0000be9c      900780         mov dptr, #0x0780
            0x0000be9f      e0             movx a, @dptr
            0x0000bea0      64a2           xrl a, #0xa2
            0x0000bea2      22             ret
            0x0000bea3      90044c         mov dptr, #0x044c
```

`0xBE7E`, `0xBE88` and `0xBE92` are three ten-byte, `ret`-terminated entries
of one shape that the project happens to export separately, over a byte stream
that runs on from `0xBE7E` to `0xBE9B`, and `0xBB9A` is a fourth in the same
shape in a different stretch at `0xBB99`-`0xBBA3` — eleven bytes, the one
longer because it opens with the store-to-caller's-DPTR `movx @dptr, a`, which
is why the default at `0x8286` uses `lcall 0xBB99` to write `0x1904` and then
finds `0x1909` in DPTR at `0x8289`. Each entry **writes `0x9F` to one gate and
leaves DPTR on the next gate in the ring `0x1904` → `0x1906` → `0x1909` →
`0x190C` → `0x1904`**.

`0x9F` is `1001 1111`: **bit 7 is set.** So the value these helpers write is one
on which every handler's bit-7 test takes, and the handler that called one calls
it on the way out, having already read the gate as one. The walk does not settle
what discriminates a channel; it settles that bit 7 is not the thing that goes
clear, and that the issue's "whoever sets bit 7 of a gate byte is what decides
whether a channel runs" cannot be answered in that form, because **every**
arming site in the walk sets it. §9 has the arms, and §7 has the one place the
default writes something else (`0x80`).

## 7. The epilogue `0x821F` and the default `0x8274`

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x821f; pd 9' /tmp/bank0.bin
            0x0000821f      12bb08         lcall 0xbb08
            0x00008222      9008e1         mov dptr, #0x08e1
            0x00008225      7406           mov a, #0x06
            0x00008227      f0             movx @dptr, a
            0x00008228      9008e0         mov dptr, #0x08e0
            0x0000822b      e0             movx a, @dptr
            0x0000822c      04             inc a
            0x0000822d      f0             movx @dptr, a
        ┌─< 0x0000822e      028274         ljmp 0x8274
```

The epilogue sets bit 0 of `0x1901` (through `0xBB08`), loads the selector
`0x08E1` with `0x06`, post-increments `0x08E0`, and hands over to the default.
**All sixteen of the eight handlers' arms reach `0x8274`**: eight by the
bit-7-clear `ljmp`, seven by this epilogue's `ljmp` at `0x822E` (cases
`0x00`-`0x06`), and case `0x07` by falling through `0xBCB1` into it. The
eighteenth arm in [`bank0-8038-handler-arms.csv`](bank0-8038-handler-arms.csv)
belongs to the `0x82D8` site of §7.1, not to a handler.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8274; pd 17' /tmp/bank0.bin
            0x00008274      9008e1         mov dptr, #0x08e1
            0x00008277      e0             movx a, @dptr
        ┌─< 0x00008278      6004           jz 0x827e
        │   0x0000827a      e0             movx a, @dptr
        │   0x0000827b      14             dec a
        │   0x0000827c      f0             movx @dptr, a
        │   0x0000827d      22             ret
        └─> 0x0000827e      12ba3e         lcall 0xba3e
            0x00008281      901904         mov dptr, #0x1904
            0x00008284      7480           mov a, #0x80
            0x00008286      12bb99         lcall 0xbb99
            0x00008289      f0             movx @dptr, a
            0x0000828a      90190c         mov dptr, #0x190c
            0x0000828d      12bafd         lcall 0xbafd
            0x00008290      12bcb1         lcall 0xbcb1
            0x00008293      22             ret
            0x00008294      900a56         mov dptr, #0x0a56
```

§9 describes this arm and the description is confirmed: while `0x08E1` is
non-zero it decrements it and returns, and the zero arm is `0x827E`-`0x8293`.
Its writes, in the order the bytes make them, are `0x1904` = `0x80` (through
`0xBB99`, whose `movx @dptr, a` stores the caller's `a`), then `0x1906` = `0x9F`
(inside `0xBB99`) and `0x1909` = `0x9F` (the `movx @dptr, a` at `0x8289`, back
in the default once the `lcall` has returned), then `0x190C` = whatever `a`
held (the store inside `0xBAFD`), then bits 0 and 1 of `0x1900` and bit 0 of
`0x1901` (`0xBAFD`), then `0x08E1` = `6` and `0x08E0` = `0` (`0xBCB1`), then
`ret`.

**The default arms `0x1904` on every path through its zero arm, and disarms the
other three to `0x9F`** — which, per §6.3, has bit 7 *set*. The `0x80` and the
`0x9F` differ only in bits 0-6. So the byte-level answer to the issue's arming
question is: the four helpers and the default all write values whose bit 7 is
set, and no edge in the eighteen arms clears it. **Whether bit 7 has a meaning
here at all, and what does gate these channels, is not determined by this
walk** — see §11.

### 7.1 The block the `0x1904` scan reaches that is not the default

Seeding on `0x1904` also finds the site at `0x82D8`, which is the largest thing
the walk turned up and is **not** part of `0x8274`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x82d8; pd 5' /tmp/bank0.bin
            0x000082d8      901904         mov dptr, #0x1904
            0x000082db      e0             movx a, @dptr
        ┌─< 0x000082dc      30e720         jnb acc.7, 0x82ff
        │   0x000082df      901918         mov dptr, #0x1918
        │   0x000082e2      e0             movx a, @dptr
```

`0x82D8` is inside the routine the committed project exports as
[`ec/decompiled/bank0/8294.asm`](../decompiled/bank0/8294.asm), which runs from
`0x8294` to `0x8397` and has no annotation row. Both of its arms are reported
`complete` by the walk, and the two `0x82D8` rows of
[`bank0-8038-handler-arms.csv`](bank0-8038-handler-arms.csv) are where their
sizes, their block structure and what they touch are read from rather than
restated here, so the figures cannot drift from the file that generates them.
Between them the arms
reach `0x0610`, `0x08E1`, `0x0A00`, `0x0A56`-`0x0A5A`, `0x1900`, `0x1904`,
`0x1918`, `0x1919`, `0x1944`, and call `0xB9EE`, `0x70E4`, `0xBA3E`, `0xBDD2`,
`0x708F` and `0xBCBD`.

The edge the issue was after is in its bit-7-clear arm:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x82ff; pd 6' /tmp/bank0.bin
            0x000082ff      901904         mov dptr, #0x1904
            0x00008302      e0             movx a, @dptr
            0x00008303      4480           orl a, #0x80
            0x00008305      f0             movx @dptr, a
            0x00008306      901900         mov dptr, #0x1900
            0x00008309      e0             movx a, @dptr
```

`0x82FF` **sets bit 7 of `0x1904` with `orl a,#0x80`** — the only site in the
whole walk that ORs a gate bit rather than writing a whole byte — and sets bits
0 and 1 of `0x1900`, then `sjmp 0x82CB`, whose `jz 0x8313` and `jnb acc.0,0x82CB`
close the loop. Its bit-7-set arm at `0x82DF` reads `0x1918`/`0x1919` (the
`0x00`/`0x04` source word) through `0xB9EE`, calls `0x70E4`, increments `r5` and
falls out of the loop when `r5` reaches `0x08`; past that it calls `0xBDD2`,
`0xBCBD`, and writes `0xFF` to `0x1944`, `0` to `0x08E1`, and a bit built from
`r5` into `0x0610`.

So `0x8294` is the one routine in the walk that both **reads the case `0x00`/`0x04`
source word** and **sets a gate bit by OR-ing rather than by writing `0x9F`**.
Whether it is the routine the issue was looking for, and in what order any of
it runs, is not determined here. It is reported because it is in the bytes and
because it is the natural place a follow-up should start.

**The same routine holds one direct write to a gate byte that neither arm
reaches, and it is named here because §10's answer is bounded by it.**
`trace_xdata_refs.py` on `0x190C` reports a write site at `0x82B1`; the two
`0x82D8` rows of the arms CSV list `0x1900`, `0x1904`, `0x1918`, `0x1919` and
`0x1944` among the addresses their arms touch, and `0x190C` is not one of them.
`0x82B1` sits in the straight-line run the `jc 0x82A1` at `0x829C` takes, and
`a` there is not free — the `lcall 0xBB99` at `0x82AD` leaves it at `0x9F` on
the way back, and nothing between that call and the store changes it:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x82aa; pd 5' /tmp/bank0.bin
            0x000082aa      901904         mov dptr, #0x1904
            0x000082ad      12bb99         lcall 0xbb99
            0x000082b0      f0             movx @dptr, a
            0x000082b1      90190c         mov dptr, #0x190c
            0x000082b4      f0             movx @dptr, a
```

So it is `0x9F` to `0x190C`, bit 7 set like the values §6.3 and §7 read off the
helpers and the default. **That is one site outside one routine, not a sweep of
the image**: it says what this write holds, not that no byte in the bank can
clear the bit.

## 8. Who reaches the dispatcher

`0x8031` — the selector read and its `lcall 0x7151` — sits immediately after the
`ret` at `0x8030`, so nothing falls into it, and **no `lcall` byte site in
either bank names it**. The `bank0` entries into the enclosing initialiser,
read from [`bank-call-targets.csv`](bank-call-targets.csv) and then re-derived
byte by byte, are **twenty-two** — twenty-three rows in that file whose target
is `0x8000`-`0x8038`, less §9's already-retired `0xAA19` — and they sort into
three kinds:

| kind | sites | evidence |
|---|---|---|
| `lcall 0x8000`, the initialiser's own head | `bank0 0x0D902` | 24 of 24; `r2` at `0xD902` shows `12 80 00` at an instruction start |
| an `ljmp` whose target lands **mid-instruction** in the initialiser | `bank0 0x0AA51 → 0x802C` | `0x802C` is the second byte of the `lcall 0xBCB6` at `0x802B` — §9's "displaced by a positive alternative" argument, unchanged |
| a `0x02` read as an `ljmp` opcode where it is the **operand byte** of a shorter instruction | `bank0 0x0AA28 → 0x801D`, `bank0 0xAA67 → 0x8016`, and the other eighteen | §9's argument, with two differences worth naming. The opcode in front of each of these sites is not an `80` but one whose operand happens to be `0x02`, and the `80` that follows belongs to the instruction *after* it. Most of them are two-byte — `a2` (`mov c,bit`), `50`/`70`/`60` (relative branches), `71` (`acall`), `10` (`jbc`), `40`, `fc` — but **three** are the three-byte form of the same shape the worked example below has in its two-byte one: `0xAA26` is `30 e0 02`, `0xAA65` is `20 e0 02` and `0xAA75` is `30 e0 02` again, so the `0x02` each of `0xAA28`, `0xAA67` and `0xAA77` read as an `ljmp` opcode is the branch's displacement and the `80 1d` / `80 16` / `80 0f` behind it is an `sjmp`. An earlier draft of this sentence named two of the three and listed `e3` among the two-byte opcodes; `e3` is the opcode in front of `0xD768`, a site whose target is past `0x8000`-`0x8038` and so outside both this section's scope and its count, and `bank-call-targets.csv` carries no `e3` row among the twenty. The census's own `frame_onto` column agrees: **3** and **1** of 24 for these two, against 24 of 24 for `0xD902` and 0 of 24 for `0xAA19` |

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x9ae0; pd 4' /tmp/bank0.bin
            0x00009ae0      29             add a, r1
        ┌─< 0x00009ae1      5002           jnc 0x9ae5
       ┌──< 0x00009ae3      8026           sjmp 0x9b0b
       │└─> 0x00009ae5      12baae         lcall 0xbaae
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8029; pd 4' /tmp/bank0.bin
            0x00008029      7480           mov a, #0x80
            0x0000802b      12bcb6         lcall 0xbcb6
            0x0000802e      a3             inc dptr
            0x0000802f      f0             movx @dptr, a
```

**Neither of the two surviving edges is the dispatch**, and the table above is
what makes that so: `0xD902` reaches the initialiser's own head, `0xAA51` its
second byte of `0x802B`, and the twenty phantoms reach nothing at all. One
census row outside that count names `0x8031` too —
`bank1 0x14D05,0xCD05,ljmp,0x8031` in
[`bank-call-targets.csv`](bank-call-targets.csv) — and it is the third kind of
phantom again, in the other bank: the `02` at `0xCD05` is the displacement of
the `jc 0xcd08` at `0xCD04`, and the `80 31` behind it that the census read as
the rest of the `ljmp` is the operand of the `sjmp` at `0xCD06`, which goes to
`0xCD39`. Its `frame_onto` is 0 of 24, as §9's retired `0xAA19`'s is. Of the
committed *annotations*, the one that is about **bank0's** `0x8031` — the
selector read — is the cross-bank trampoline
[`bank1,0x1A98,trampoline_bank0_8031`](ghidra-functions.csv) —
`mov dptr,#0x8031` then `ljmp 0x1100` — which reaches the selector read through
the BL51 bank-switch stub rather than through a call, and whose `0x1100` body is
outside that listing. Two further rows carry the number without being about it:
`bank1,802D,branch_if_acc_zero_to_8031` branches to **bank1's** `0x8031`, a
different address in a different bank —
[`802D  60 02  -  jz  0x8031`](../decompiled/bank1/802D.asm) lands on
`90 06 36 e0` at [`8031.asm`](../decompiled/bank1/8031.asm), `mov dptr,#0x0636`
then `movx a,@dptr`, nothing like the selector read and no path into bank0 — and
`bank0,0x8026`'s comment names `0x8031` to say the selector read is *not* part
of that listing. This section therefore **ends at "not determined"**: by
these three CSVs, these two `lcall` byte scans and the committed trampoline
annotation, bank0's `0x8031` is reached by the trampoline and by nothing else
found.
A `ret`-based thunk or a computed target would be invisible to all of them, as
§9's blind-spot list says for the reader at `0x7151`.

## 9. The other readers and writers of the 32 addresses

[`xdata-registers.csv`](xdata-registers.csv) already carries a census for
thirty of the thirty-two, and the two it is missing — `0x08DE` and `0x08DF`, the
last pair of the `0x08D0` slot — are the two the table below gives **no row**.
It is still the cheapest starting point for the issue's item 3, but read it as
a census of the **decompiled C** — one reading of the bytes, which cannot see a
pointer that is built at run time or handed to a routine the listing does not
contain — so §1's `trace_xdata_refs.py` run re-derives the direct sites from the
image rather than restating it.

| address | refs | reader fns | writer fns | functions touched | address-taken | what this walk adds |
|---|---:|---:|---:|---:|---:|---|
| `0x0610` | 17 | 3 | 3 | 12 | 0 | the eight `orl a,#0xNN` / `lcall 0xBA3D` sites of §4, **none of which the census counts as a write** — each hands the ORed byte to `0xBA3D` as an *argument*, so the `write` column is 0 and the three in `writers` are `bank0,0x8294` and the two bank-1 read-modify-write sites `bank1,0xB728` and `bank1,0xD4D3`, none of them in this block. The same row's `functions` cell nonetheless tags eight functions `[writer]`, §4's seven case entries and the `0x806C` boundary of §3 among them, so the two columns of one row disagree and only the `write`/`read+write` pair above explains why |
| `0x1904` | 12 | 4 | 2 | 7 | 5 | the `orl a,#0x80` at `0x8303` (§7.1), which is an OR and not a whole-byte write; five of the twelve references are the address being taken rather than a `movx` |
| `0x08E1` | 18 | 4 | 8 | 8 | 1 | — |
| `0x0600` | 5 | 2 | 3 | 3 | 0 | — |
| `0x060E` | 3 | 3 | 0 | 3 | 0 | the census has **no writer** for this byte; the image has two, both in case `0x07` (`0x8249` read, `0x825F` write), for the reason in the row below |
| `0x08D0` | 2 | 0 | 2 | 2 | 0 | one direct site and one `mov dptr` (`0x8061`), writing two consecutive bytes; the census's two "writers" are not two sites but the two Ghidra entries `0x8048` and `0x8054` its decompile split one run across, and §3's finding is that those listing boundaries are **not** control-flow boundaries — `0x8048` is a mid-stream entry over table bytes the walk never reaches, and the committed `8048.c` says itself that the body Ghidra produced there "is a reading of bytes outside this window, not of these instructions". **Read by nothing either method finds** |
| `0x08DE` | **no row** | — | — | — | — | written by case `0x07` at `0x8242`; the census has no row at all, because the committed project exports no function at `0x8231` (§4.8) |
| `0x08DF` | **no row** | — | — | — | — | written by the same store one byte up — `inc dptr` at `0x8243`, then `mov a,r7` / `movx @dptr,a` at `0x8244`-`0x8245` — and absent for the same reason as the row above |
| `0x0A59` | 68 | 16 | 40 | 43 | 1 | the shared scratch byte of §4 and §5; far too widely used for the census to say anything about it *here* |

Three results from that table are worth stating as results rather than as rows.

**`0x08DE` missing from the census, and `0x060E` having no writer in it, are
the same blind spot twice.** The census is built from exported decompiled
functions; case `0x07` has none, so both its word slot and its accumulator's high
byte are missing or wrong in the file that is otherwise the natural index for
these thirty-two addresses. Re-derived from the image, `0x060E` is read at
`0x8249` and written at `0x825F` by case `0x07`, and `0x08DE` is written at
`0x8242`. These are the only rows in this section where the two methods
disagree, and the image wins.

**`0x08D0`-`0x08DF` is written here and read nowhere either method finds.** One
`mov dptr` site per slot, `movx` on both, `inc dptr` for the second byte, and
no `movx a,@dptr` naming any of the sixteen in either bank. That is "not found
by this method" — the walk is byte-level, DPTR-tracking and bounded — and it is
the single most surprising thing §6 leaves open.

**Two bank1 routines read the `0x060E`/`0x060F` accumulator, and what the first
one does with the result is not settled by its bytes.** `trace_xdata_refs.py`
finds the two, and both hand DPTR to the same 16-bit loader `0x8886` that §9's
`bank1,0xB728` uses — so case `0x07`'s accumulator leaves this block in two
places, not one:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xd979; pd 6' /tmp/bank1.bin
            0x0000d979      90060e         mov dptr, #0x060e
            0x0000d97c      128886         lcall 0x8886
            0x0000d97f      530203         anl r2, #0x03
            0x0000d982      900378         mov dptr, #0x0378
            0x0000d985      ac83           mov r4, dph
            0x0000d987      ab82           mov r3, dpl
```

**The three bytes at `0xD97F` are `53 02 03`, and this document does not pick
one reading of them.** The two renderings in the tree are `anl r2, #0x03`
(`r2 -a 8051`, the transcript above) and `anl 0x02, #0x3` (the committed
[`ec/decompiled/bank1/D946.asm`](../decompiled/bank1/D946.asm), which prints
`D97F 53 02 03 anl 0x02, #0x3`); `ec/tools/disasm8051.py` decodes no
instruction there at all and prints `db 0x53`. The first two are **one
instruction under two spellings** rather than a disagreement about it: `0x53` is
`ANL direct,#data` on the base 8051 map, three bytes, and direct address `0x02`
*is* `R2`, so both spend the same three bytes on the same operand. `0x8886`
puts the low byte of the word in `r1` and the high byte in `r2`, so on either
spelling the instruction masks the **high** byte with `0x03` — the top two bits
of the 16-bit value. That much is the bytes.

**What the masked value is then used for is not.** The `mov dptr,#0x0378` that
follows is a **constant address**, copied into `r3`/`r4` and then added into a
byte read from `0x03BD`; `r2` is not read again until `0xD9C1`, which is
outside the stretch this document decodes. So the pair is not a table index
into anything these bytes show — what they support is narrower: **the word is
loaded, one byte of it is masked, and nothing in what these scans decode uses
the result.** `bank1,0xDAED` follows with `a8 01` and `a9 02` and then calls
`0xA5A7` with `r2` = `0x75` and `r3` = `0x17`.

Those two bytes are worth stopping on, because the two disassemblers in this
tree read them differently and the base 8051 says a third thing. `r2 -a 8051`
gives `mov r0, r1` / `mov r1, r2`; `ec/tools/disasm8051.py` gives `mov r0,0x01`
/ `mov r1,0x02`; `0xA8`/`0xA9` are `MOV Rn,@R0` on the base instruction set. So
what is claimed here is only the bytes and their position — the word is loaded
by `0x8886` and passed to `0xA5A7` beside two constants, and **which registers
hold it afterwards is not determined**. Neither site is decoded further here,
and neither is named in a `ghidra-functions.csv` row this document could
check; the shape is the result, and nothing is claimed about what `0x0378`
holds or what `0xA5A7` does with the pair.

**`bank1,0xB728` is a cross-bank consumer of case `0x05`'s accumulator,
compared against a constant.** It is not the only one, and it is not the only
one for this pair either — §9.1 gives the census's own set for `0x060A`/`0x060B`.
Its bytes, from a `bank1` image:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xb728; pd 8' /tmp/bank1.bin
            0x0000b728      900610         mov dptr, #0x0610
            0x0000b72b      e0             movx a, @dptr
        ┌─< 0x0000b72c      10e501         jbc acc.5, 0xb730
        │   0x0000b72f      22             ret
        └─> 0x0000b730      f0             movx @dptr, a
            0x0000b731      90060a         mov dptr, #0x060a
            0x0000b734      128886         lcall 0x8886
            0x0000b737      7c03           mov r4, #0x03
```

It tests bit 5 of `0x0610` — case `0x05`'s done bit, per §9's table and §4.6's
`orl a,#0x20` — and on it being set, loads the 16-bit big-endian word at
`0x060A` (case `0x05`'s accumulator, whose two bytes `0x8886` moves into `r1`
and `r2` in that order) and compares it against `0x03E8`. It is a byte
reading: `0x060A` holds a 16-bit word and that word is compared with `1000`.
Nothing here says the comparison's outcome means anything, and §9.1 shows it is
not the only place a value a `0x8038` handler computes is read by other code —
it is the only one of them that compares it against a constant.

### 9.1 Every accumulator, and every consumer the widened scan finds

§1's `trace_xdata_refs.py` line names all sixteen accumulator bytes. Run over
all sixteen, it reports **48 direct sites, 32 of them inside the handler block
and 16 outside it** — and the sixteen outside are in both banks, which is what
the two-pair version of the command could not have shown. Of the eight pairs,
only `0x0600`/`0x0601` and `0x0604`/`0x0605` have no site outside the block;
the other six have between one and five.

| pair | sites outside `0x8038`-`0x8293` | what the census names for that pair |
|---|---|---|
| `0x0600`/`0x0601` | none | — |
| `0x0602`/`0x0603` | `bank0 0xB5D3` | `bank0:0xB5D3=FUN_CODE_b5d3` |
| `0x0604`/`0x0605` | none | — |
| `0x0606`/`0x0607` | `bank0 0xDAFD`, `0xDB02`, `0xDB2E` | nothing — see below |
| `0x0608`/`0x0609` | `bank0 0xBAAE`, `0xBAB3`; `bank1 0xA2B4`, `0xD4DC` | `bank1:0xA24E=FUN_CODE_a24e`, `bank1:0xD4D3=FUN_CODE_d4d3` |
| `0x060A`/`0x060B` | `bank1 0xB731`, `0xB7AB`, `0xB7F7`, `0xE8B7`, `0xE8CD` | `bank1:0xB728=clear_0610_bit5_and_dispatch`, `bank1:0xB784=FUN_CODE_b784`, `bank1:0xE8A4=compute_097e_times_10_write_0386_0387` |
| `0x060C`/`0x060D` | `bank1 0xF3F5` | `bank1:0xF3D7=store_scaled_quotient_0449` |
| `0x060E`/`0x060F` | `bank1 0xD979`, `0xDAED` | `bank1:0xD946=FUN_CODE_d946`, `bank1:0xDAAD=FUN_CODE_daad`, `bank1:0xDACC=FUN_CODE_dacc` |

Ten of the sixteen are in `bank1`, spread over the nine `ghidra-functions.csv`
rows the census names for them; the other six are in `bank0`, in three places.
**Three pairs — `0x060A`, `0x060C` and `0x060E`, cases `0x05`, `0x06` and
`0x07` — have every consumer this scan finds in the other bank, and six of the
eight pairs have a consumer at all.**

Two of the three `bank0` places have committed listings, and one does not:

- **`bank0,0xB5D3`** — [`B5D3.asm`](../decompiled/bank0/B5D3.asm), 323 bytes
  from a `call-target` boundary that [`bank-call-audit.md`](bank-call-audit.md)
  §1 calls an upper bound. It reads `0x0602` into `R6` and `0x0603` into `R7`,
  calls `0x8399`, and stores `R7` to `0x0875`. That is the reverse of §5.1's
  register order, where `r6` is the low byte of the folded sum; the bytes are
  what they are and this document does not say what the reversal is for.
- **`bank0,0xBAAE`** — [`BAAE.asm`](../decompiled/bank0/BAAE.asm), the named
  `load_r7_r6_from_0608_and_return_0399`. It loads `0x0608`/`0x0609` into
  `R7:R6` in the accumulator's own order and returns the byte at `0x0399` in
  `a`. **The census does not name it for either address**, and the committed
  [`BAAE.c`](../decompiled/bank0/BAAE.c) says why in its own comment: "The
  decompiled C reports only the 0x0399 return and drops the two register
  loads." It is the sharpest illustration of the caveat this section opens
  with — a real consumer invisible to a census of the decompiled C, in a
  listing that carries a name for exactly that reason.
- **`0xDAFD`-`0xDB2E`** — no committed listing and no `ghidra-functions.csv`
  row covers it: `bank0,D9FE,seed_07d3_gfid_and_08xx_defaults` is 203 bytes
  and ends at `0xDAC8`, and the next bank0 export is at `0xDB3E`. What the
  bytes do is visible: it reads `0x0607` into `R2`, `0x0606` into `R7`, copies
  `R2` into `R6`, and **subtracts** the pair from the 16-bit value at
  `0x0A33`/`0x0A34` (`subb a,r7` then `subb a,r6` — `r6` the low byte, `r7`
  the high one, §5.1's order, where `0xB965` adds). Case `0x03`'s accumulator
  is a *minuend* here rather than the addend the handler folds it as. No
  function boundary covers these bytes, so there is no name for the routine and
  this document does not invent one.

**`bank1,0xF3D7` is the one consumer that reaches outside the block to a
[`registers.yaml`](registers.yaml) row, and §10 turns on it.** `0xF3F5` is
`mov dptr,#0x060c ; lcall 0x8886` and the routine it sits in ends by storing
`a` to `0x0449`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xf3f0; pd 8' /tmp/bank1.bin
            0x0000f3f0      12f3c9         lcall 0xf3c9
            0x0000f3f3      7c00           mov r4, #0x00
            0x0000f3f5      90060c         mov dptr, #0x060c
            0x0000f3f8      128886         lcall 0x8886
            0x0000f3fb      530203         anl r2, #0x03
            0x0000f3fe      e9             mov a, r1
            0x0000f3ff      75f00a         mov b, #0x0a
            0x0000f402      a4             mul ab
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xf411; pd 3' /tmp/bank1.bin
            0x0000f411      900449         mov dptr, #0x0449
            0x0000f414      f0             movx @dptr, a
            0x0000f415      22             ret
```

`0x060C`/`0x060D` is case `0x06`'s accumulator pair. The committed
[`bank1,0xF3D7` row](ghidra-functions.csv) — `store_scaled_quotient_0449` —
already records what happens to it: the high byte is masked with `0x03`, the
value is multiplied by ten, divided by a divisor this routine picks from bit 6
of `0x0456`, and the result goes to `0x0449`. Both those addresses are rows in
`registers.yaml`, and both `registers.yaml` and the `0xF3D7` row cross-reference
each other about it. §10 says what follows, and what it does not.

## 10. The subsystem question, and where this stops

The issue asks whether any of this plausibly belongs to fan/thermal sensing,
battery, or power, and says to say so if the evidence does not reach.

**It does not reach, and this document does not answer the question.** What the
walk establishes is shape: eight handlers behind a gate bit, each copying a
16-bit word out of a 16-bit XDATA word and halving it into its own 16-bit
accumulator, with a done bit per case and a rotating ring of four gates. That
shape is consistent with a sampling or smoothing loop, and it is also
consistent with a dozen other things. Three of the four arguments below fail on
the same point — each is a statement about what the *values* mean, and nothing
in this image assigns meaning to them. The fourth is the one that has moved,
and it moved because §1's scan was widened rather than because the bytes
changed:

- **No name.** None of `0x1904`/`0x1906`/`0x1909`/`0x190C`, `0x1907`-`0x1919`,
  `0x08D0`-`0x08E1`, `0x0600`-`0x0610` or `0x0A56`-`0x0A59` is in
  [`registers.yaml`](registers.yaml); §9 re-runs that intersection and it is
  empty. Not one byte here has a DSDT name, a vendor header name or an
  annotation name attached to it.
- **No unit, no range, no sign.** The halves are all `0x9F` and the sources are
  unknown bytes. A fan tachometer, a thermistor millidegree count and a
  coulomb counter are 16-bit and halve beautifully; so is a timer.
- **No host-side record for the slots, and one for the accumulators.** Nothing
  outside this bank0 block reads the `0x08D0`-`0x08DF` slots by these scans
  (§6.2), and the sixteen addresses the block itself writes have no
  `registers.yaml` row between them. The accumulators are the other way round,
  and the first draft of this section said they were not: written as a blanket
  negative, from a scan (§1) that named two of the eight pairs. §9.1's widened
  scan finds sixteen sites outside the block, in three `bank0` places and nine
  `bank1` routines, and one of them — `bank1,0xF3D7` — writes to `0x0449`, a
  `registers.yaml` row whose own note says it is *"Derived from
  0x0434/0x0435: store_scaled_quotient_0449 (bank1 0xF3D7) reads the battery
  current pair and divides by 100 into this byte"*, and `0x0434`/`0x0435` is
  `BAT_CURRENT_MA`, the one address in this repository whose value is
  established live and agreed upstream. So the issue's "EC-internal half of
  something `registers.yaml` tracks from the host side" hypothesis now has one
  committed link behind it, and this document's earlier answer — that it "has no
  support" — was wrong on the strength of a narrow scan.
  **What that link is not:** the routine's own selector between the two paths
  is `R7`, which the committed `0xF3D7` row says "is set nowhere in this
  listing or in `0x198A`"; the divisor is `0x22` or `0x44` from a `SYSTEM_ID`
  bit, not the `100` the battery path uses; and the mask `anl r2,#0x03` discards
  the top two bits of the accumulator before the multiply. So the accumulator
  reaches a byte battery current also reaches, and the two values are not shown
  to be the same quantity, to be the same unit, or to be scaled the same way.
  That is a lead with a file behind it, not a subsystem.
- **The nearest neighbours are already spoken for, and are not these.** The
  blocks that *are* attached to a subsystem in this repository are attached
  through [`registers.yaml`](registers.yaml) rows —
  [`charge-profile-flow.md`](charge-profile-flow.md)'s `0x0741`/`0x07A6` and
  [`lightbar-bat-flow.md`](lightbar-bat-flow.md)'s `0x07E2` among them. None of
  the thirty-two addresses here is one of them, and the `0x0449` link above is
  not to a named measurement either: the `bank1,0xF3D7` row records it as "an
  EC-side site found with its meaning not established", which is what its
  `registers.yaml` row carries as `present-untested`.

So the honest answer is: **eight accumulating channels fed by four 16-bit
words, behind a gate bit that no edge in the walk's eighteen arms clears, with
no name and no unit; six of the eight have consumers this scan finds, and one
of those — case `0x06`'s — writes to a byte the EC also derives from battery
current — and no basis for calling all eight thermal, fan, battery or power.**
The gate clause stops where the evidence stops, and the stop is named rather
than assumed: the one direct write to a gate byte that no arm reaches is at
`0x82B1`, it holds `0x9F`, and it sets bit 7 like the rest (§7.1) — which is a
decode of one site, **not** a sweep for every writer of
`0x1904`/`0x1906`/`0x1909`/`0x190C`, and this document runs no such sweep.
Naming a subsystem here would be a guess wearing the grammar of a finding,
which is what `CLAUDE.md`'s calibration rule is written against. The consumer
side is no longer a blank, but the unit is: sixteen sites that read a value say
nothing about what the value measures. If a follow-up wants to close this, the
cheapest next step is named in §11 and is a human's, not this pipeline's.

## 11. What a live observation would settle, for a human at the machine

No EC is reachable from a GitHub-hosted runner, and nothing above was run on
hardware. Three readings at the machine would each close a specific gap, and
each is a read, not a write:

1. **The gate bytes at rest and in motion.** Read `0x1904`, `0x1906`, `0x1909`
   and `0x190C` in the same breath, repeatedly, on a machine that is otherwise
   idle. §6.3 and §7 say the four helpers and the default both write values
   with bit 7 set, and that no edge in eighteen arms clears it. If the byte is
   never anything but `0x9F` and `0x80` here, bit 7 is not a gate in the sense
   §9's skeleton assumes, and the real discriminator is elsewhere. **This is
   the observation that decides whether the eight handlers gate on anything at
   all**, and it is the one the issue's item 3 ultimately turns on.
2. **A source word against its slot.** Read `0x1918`/`0x1919` and `0x08D0`/`0x08D1`
   in the same sample. §6.2 says the slot is a copy; if the two agree in the
   same sample, the copy is not a stale artefact of the walk's bounds, and the
   slot's real reader is something these scans cannot see. If the slot never
   changes while the source does, that is also a result, and it would say the
   handlers are not running.
3. **A real value for the consumers §9.1 lists.** Sample the eight accumulator
   pairs while whatever they track changes, and read `0x0449` and `0x0434`/
   `0x0435` in the same breath — the last of those is `BAT_CURRENT_MA`, whose
   value is already established live, so a handler whose accumulator tracks
   current will move with it and one that does not will not. That comparison is
   the one this document can name precisely: `bank1,0xF3D7` masks the high byte
   of case `0x06`'s accumulator, multiplies by ten and divides by a divisor
   taken from `SYSTEM_ID` bit 6, and the routine's other branch — the one its
   own `R7` selector picks instead — divides battery current by `100` into the
   same byte. If `0x0449` correlates with `0x0434` only on the battery branch,
   that says the two are one quantity; if it moves when current is flat, it is
   a second, unnamed thing sharing a byte.
   The other consumers are the same kind of read with less to compare against:
   `bank1,0xD979` masks a byte of the `0x060E`/`0x060F` accumulator with `0x03`
   and nothing in the bytes §9 decodes uses the result; `bank1,0xDAED` passes
   the pair to `0xA5A7` with `0x75` and `0x17`; `bank1,0xB728` compares the
   `0x060A`/`0x060B` accumulator against `0x03E8`; `bank0,0xB5D3` stores one
   byte of case `0x01`'s to `0x0875`; and the unnamed `0xDAFD` region subtracts
   case `0x03`'s from the pair at `0x0A33`/`0x0A34`. Reading `0x0875` and
   `0x0A33`/`0x0A34` alongside the accumulator is what would put a number on
   any of them. Nothing short of that will.

Until one of those is run by a human, the correct description of this region is
the one in §10, and no `status:` in [`registers.yaml`](registers.yaml) moves:
a decode is not a behavioural observation, and a register write being accepted
on readback would not be one either.

## Left out, and why

- **Seeding a `bank0,0x8231` annotation row.** The address is real — §9's table
  and the bytes in §4.8 both say so — but no function is exported there, and
  `CLAUDE.md` is explicit that this is either a typo or a sign the project needs
  `--mode rebuild-project`. It is the latter, and `--mode rebuild-project`
  **writes the committed `.gpr`/`.rep`**: two branches that both rebuild one
  cannot merge, and `.gitattributes` makes git refuse rather than text-merge the
  database. §4.8 decodes the address from the bank image without any of that.
- **Renaming `bank0,0x805B`.** It wears the name `index_table_default`, and the
  walk confirms what §9 suspected: `0x805B` is a three-byte `ljmp 0x8274` — the
  case `0x00` bit-7-clear arm — while the same name also sits on `0x8274`
  itself, the block the jump lands in. The two names do not come from the same
  place, which is why this is not simply a row to edit: `0x8274` carries it from
  the `bank0,0x8274` row of [`ghidra-functions.csv`](ghidra-functions.csv),
  while `0x805B` has no row there at all and takes the name from the sdas8051
  reassembly match recorded in [`ghidra/reassembly.csv`](../ghidra/reassembly.csv),
  which `decompiled/index.csv` gives the source of as `call-target`. So which
  file a rename has to be made in is itself part of what is unestablished, and
  a rename on the `0x8274` side does mean editing a 1 MB CSV every open agent PR
  also edits, re-exporting so `index.csv` and the `.c` banners follow, and
  regenerating `xdata-registers.csv` and `xdata-cluster-names.csv` through
  `xdata_register_map.py`, all under a gate that recounts them. That is a large
  shared-file diff for a naming correction, and it is a separate piece of work.
  **Reported here, not applied.**
- **Renaming `0x806C`** (`store_byte_through_0a59_into_0600`) and the other
  mid-block entries, for the same reason and the same additional finding: §3
  shows `0x806C` is an instruction inside case `0x00`'s single linear block, not
  a routine of its own.
- **A new tool for the walk.** `walk_branch_arms.py` already does the
  both-arms-with-bounds work, seeded on the four gate bytes. Writing a second
  one would be the duplication `walk_flow_follow.py` and `walk_branch_arms.py`
  already sit next to each other to avoid.
- **Whether these are the EC-internal half of something `registers.yaml` already
  tracks from the host side.** §10 gives what the intersection over the
  thirty-two addresses is empty of, and the one committed link the widened scan
  turned up: case `0x06`'s accumulator reaching `0x0449` through
  `bank1,0xF3D7`, a byte `registers.yaml` also derives from battery current.
  Named as a lead with §11.3's comparison attached, not answered.
- **§10's other fourteen tables.** Out of scope; this is the one table.
- **Anything under `.github/workflows/` or `.github/actions/`.** The pipeline
  token has no `workflow` scope.
- **Anything in another repository.** The mission's eventual upstream
  contribution is a prepared patch committed *here*; no stage opens an issue or
  a pull request against `Wer-Wolf/uniwill-laptop`, `tuxedo-drivers` or
  anywhere else, and this document does not end at an upstream contribution in
  any case.
