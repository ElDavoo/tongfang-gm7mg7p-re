# The PD image's three table readers each carry their own entry layout, and every one of them ends in the same four-byte terminator-and-default pair

(2026-10-04, issue #1120. Static reading of committed bytes through
`ec/tools/decode_index_table.py` and `ec/tools/pd_index_tables.py`, against the
`ITE8850-PD` image at file `0x20000` inside `ec/firmware/GMxMGxx_11.800`. No
capture opened, no EC, no hardware, no Windows, no `registers.yaml` row touched.
The main EC's three committed CSVs come back byte-identical.)

[`table-reader-spellings.md`](table-reader-spellings.md) result 3 reads the
PD image's three dispatchers under this family's 3-byte entry and records that
two of them are not that layout: `0x11C2` walks 4 bytes per entry and `0x11EF`
walks 6. It also said the full entry layout of `0x11EF` "is not decoded here and
is not claimed", and it could not say more, because the entry width was a
constant in `decode_index_table.py` rather than something a caller supplied.
That is what this page closes, and what it establishes is:

- **One rule fits all three readers:** two target bytes at entry offsets +0/+1,
  then `stride - 2` key bytes, compared most significant first. A 3-byte entry
  has one key byte, a 4-byte entry two, a 6-byte entry four.
- **The terminator does not scale with any of that.** It is a zero target pair
  — the same two bytes that carry every entry's target — followed by a 2-byte
  default, so `end` is four bytes past the terminator at every stride. This is
  re-derived from the four readers' own code rather than scaled from the 3-byte
  case, and the derivation lands on the same number at all four.
- **Two `0x11C2` tables that used to "pass" the 3-byte rule were passing by
  coincidence of alignment**, and the bytes say so. Both are real tables and
  both pass under their own reader's rule; what the old reading counted between
  them was misaligned.
- **One row still fails: `0x242C5`**, under `0x119C` at this family's own
  stride. That is now a true statement about a table rather than an artefact of
  a foreign rule, and it stays open.

`ec/tools/decode_index_table.py` takes the stride as a parameter (`ENTRY_LEN`
being the main EC's own), so `pd_index_tables.py` hands each reader the width
`entry_stride()` derived from that reader's own `inc dptr` loop. Every row of
[`pd-index-table-spans.csv`](../../ec/annotations/pd-index-table-spans.csv) is
now decoded and judged at its own reader's width, and `well_formed` is a
statement about the table in that row. Its two case columns become
`first_key`/`last_key` and carry the key bytes the row's entry really has, so
the column's width on its own says which reader produced the row — a 3-byte
entry's one key byte and a 4-byte entry's two are not the same value.

## The three layouts, from the readers' own compare chains

`entry_stride()` reads the length of the `inc dptr` run feeding the last
backward `jnz`/`sjmp` in a reader's body, and it gives 3, 4, 6. The stride
alone says how wide an entry is, not what is in it — so what follows reads each
reader's `movc a,@a+dptr` chain, which is where the key bytes and their
comparison registers are named.

| reader | prologue | key bytes | compared against | loop-back | `inc dptr` run |
|---|---|---|---|---|---|
| `0x07151` (main EC) | `d0 83 d0 82 f8` | +2 (1) | `r0` | `80 df` → `0x7151` | 3 |
| `0x119C` | `d0 83 d0 82 f8` | +2 (1) | `r0` | `80 df` → `0x11A1` | 3 |
| `0x11C2` | `d0 83 d0 82 f8` | +2, +3 (2) | `B`, then `r0` | `80 d8` → `0x11C7` | 4 |
| `0x11EF` | `d0 83 d0 82` (**no `f8`**) | +2..+5 (4) | `r4`,`r5`,`r6`,`r7` | `80 ca` → `0x11F3` | 6 |

The `mov a,#N` immediately before each key `movc` is the index the record byte
is read at, so the `#2`/`#3`/`#4`/`#5` in the two chains below *are* the entry
offsets, and the `xrl`/`cjne` after each is the comparison. The key bytes are
read most significant first: the chain bails to the next entry at the first
mismatch, and only a full match reaches the `jz` into the load-and-dispatch
tail. Ghidra's decompile of the same bytes agrees without being told the
stride: the generated
[`ec/decompiled/pd/11EF.c`](../../ec/decompiled/pd/11EF.c) steps
`pcVar1 = pcVar1 + 6` and compares `pcVar1[2]` through `pcVar1[5]` against
four parameters.

`0x11C2` is the two-byte key, with byte +2 against `B` and byte +3 against the
selector the prologue saved in `r0`:

```console
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x11dd; pd 8' /tmp/pd.bin
        ╎   0x000011dd      7402           mov a, #0x02
        ╎   0x000011df      93             movc a, @a+dptr
       ┌──< 0x000011e0      b5f006         cjne a, b, 0x11e9
       │╎   0x000011e3      7403           mov a, #0x03
       │╎   0x000011e5      93             movc a, @a+dptr
       │╎   0x000011e6      68             xrl a, r0
       │└─< 0x000011e7      60e9           jz 0x11d2
       └──> 0x000011e9      a3             inc dptr
```

`0x11EF` is the four-byte key, against `r4` through `r7`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1209; pd 18' /tmp/pd.bin
        ╎   0x00001209      7402           mov a, #0x02
        ╎   0x0000120b      93             movc a, @a+dptr
        ╎   0x0000120c      6c             xrl a, r4
        ┌──< 0x0000120d      7012           jnz 0x1221
        │╎   0x0000120f      7403           mov a, #0x03
        │╎   0x00001211      93             movc a, @a+dptr
        │╎   0x00001212      6d             xrl a, r5
        ┌───< 0x00001213      700c           jnz 0x1221
        ││╎   0x00001215      7404           mov a, #0x04
        ││╎   0x00001217      93             movc a, @a+dptr
        ││╎   0x00001218      6e             xrl a, r6
        ┌────< 0x00001219      7006           jnz 0x1221
        │││╎   0x0000121b      7405           mov a, #0x05
        │││╎   0x0000121d      93             movc a, @a+dptr
        │││╎   0x0000121e      6f             xrl a, r7
        │││└─< 0x0000121f      60dd           jz 0x11fe
        └└└──> 0x00001221      a3             inc dptr
            0x00001222      a3             inc dptr
```

**Why `0x11EF` was invisible to a byte search for this family's prologue.** Its
fourth byte is `e4` (`clr a`), not `f8` (`mov r0,a`): the selector save happens
*after* the two zero-tests rather than before them, because the key arrives in
four registers rather than in the accumulator. So the `d0 83 d0 82 f8` literal
misses it entirely and only the bare `pop dph ; pop dpl` plus a `movc` in the
prologue window finds it — which is the argument
[`table-reader-spellings.md`](table-reader-spellings.md) already made for why
the search is tiered. The consequence is that until this change no annotation
row named this routine, and still nothing says what its three call sites put in
`r4`-`r7`. **The three sites are known; the key's provenance is not**, and that
is open.

## The terminator and the default are four bytes at every stride

This is the part that had to be re-derived rather than scaled, so it is derived
per reader and the derivation is pinned at all four. Every reader's zero-tests
branch to the same 13 bytes, byte-identical in all four images' worth of
readers:

```console
$ python3 -c '
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
tail = bytes.fromhex("a3a393f8740193f5828883e473")
for off in (0x0715F, 0x211AA, 0x211D0, 0x211FC):
    print("0x%05X" % off, d[off:off + len(tail)] == tail, d[off:off + len(tail)].hex(" "))
'
0x0715F True a3 a3 93 f8 74 01 93 f5 82 88 83 e4 73
0x211AA True a3 a3 93 f8 74 01 93 f5 82 88 83 e4 73
0x211D0 True a3 a3 93 f8 74 01 93 f5 82 88 83 e4 73
0x211FC True a3 a3 93 f8 74 01 93 f5 82 88 83 e4 73
```

Read as instructions that is: `inc dptr ; inc dptr` — step DPTR past a two-byte
zero target pair — then `movc a,@a+dptr ; mov r0,a ; mov a,#1 ; movc a,@a+dptr ;
mov dpl,a ; mov dph,r0 ; clr a ; jmp @a+dptr`, which loads the two bytes *after*
the pair into DPTR and dispatches through them. So:

- the **terminator is two bytes** — the same zero target pair an entry's own
  target would be, which is what the reader's two zero-tests are testing;
- the **default is two bytes** after it, read by the same `jmp @a+dptr` a
  matched entry goes out through;
- and `end` is **four bytes past the terminator**, at every stride.

The `inc dptr` count in that tail is `2` and not `stride`, and that is the whole
of the derivation: it is the code's own statement that the zero pair it steps
over is two bytes wide, whatever the entries around it are. It does not scale,
and it does not need to.

`decode_index_table.py` names these `TERM_LEN` and `DEFAULT_LEN` and pins the
tail bytes at all four offsets in `--self-test`, so "four bytes at every
stride" is a claim about these offsets rather than a constant someone could
scale later.

## Two `0x11C2` tables that passed the wrong rule, and why they passed

Under the 3-byte rule, `0x283CF` and `0x292EF` came back `well_formed=yes`. That
was the only evidence [`table-reader-spellings.md`](table-reader-spellings.md)
had that the rule was wrong rather than the tables, so it is worth being exact
about what happened. Both tables are real and both pass under their own
reader's rule:

```console
0x283D2: 83 e2 04 02 | 84 7b 04 04 | 85 02 04 ff | 00 00 85 63   -> 0x83E2 key 0x0402, 0x847B key 0x0404, 0x8502 key 0x04FF, default 0x8563
0x292F2: 93 02 07 01 | 93 38 07 02 | 93 db 07 ff | 00 00 94 40   -> 0x9302 key 0x0701, 0x9338 key 0x0702, 0x93DB key 0x07FF, default 0x9440
```

**The `00 00` pair sits at `0x283DE` and `0x292FE` — twelve bytes into each
table, which is a 3-aligned offset and a 4-aligned one alike.** The 3-byte
reading therefore found the same terminator, read the same two bytes as the
same default, and reported the same `end`. Everything it counted between them
was read a byte out of step: it took each record's *second key byte* as the next
record's high target byte. That is the entire reason the two rows passed rather
than failed, and it is a coincidence of these two tables' alignments rather than
a property of the 0x11C2 reader. The verdict "these are real tables" stands;
the reasoning that supported it does not, and it is not the support either one
needs now that each is decoded at stride 4.

## What the `0x11EF` sites are, at their own width

The old reading gave all three of `0x11EF`'s sites **one entry each**, and
[`table-reader-spellings.md`](table-reader-spellings.md) pinned that zero as a
result: entry bytes +2 and +3 of a 6-byte record are `00 00`, which a 3-byte
reader takes as the terminator. That was a true account of what the wrong rule
does. At stride 6 they are real tables:

```console
0x22501: 25 32 00 00 00 05 | 25 11 00 00 00 08 | 00 00 25 7d     -> 2 entries, keys 0x00000005 and 0x00000008, default 0x257D
0x2286A: 2e 22 00 00 00 00 | 28 98 00 00 00 01 | 29 54 00 00 00 02 | 29 f3 00 00 00 03
         2b 82 00 00 00 04 | 2c 73 00 00 00 05 | 2d 76 00 00 00 06 | 00 00 2d 9c  -> 7 entries, keys 0x00-0x06, default 0x2D9C
0x2BCF1: bd 01 00 00 00 10 | bd 3b 00 00 00 11 | 00 00 bd 52     -> 2 entries, keys 0x10 and 0x11, default 0xBD52
```

The keys are four-byte big-endian counters — `00 00 00 00` … `00 00 00 06` at
`0x2286A` is a clean sequence with no gaps — which is the shape of an index into
something a caller counts, and the three tables' targets (`0x2532`, `0x2511`,
`0x2E22`…`0x2D76`, `0xBD01`, `0xBD3B`) are CODE addresses in the flat PD image.
**What the counter indexes is not decoded here.** All three tables' handlers are
targets this page identifies and does not walk.

Naming `0x11EF` is what lets two other committed tables say something about it.
`pd_no_ret_fallthrough.csv`'s `0x11C2` row carried an empty fall-through-name
cell, because the address it falls into had no listing to name; it now reads
`dispatch_code_table_4byte_key_r4r7`, and `0x11EF` has a row of its own. And
`pd_call-targets.csv` reclassifies three byte-scan sites — `0x11F6`, `0x120A`
and `0x120E` — from `mid-instruction` of `0x11C2` to `operand` of `0x11EF`,
which is listed, so their `in_listing` cell goes with it. Both files are
regenerated from their tools rather than edited. Neither says anything about
control flow the walk had not already decoded: a listing changes which function
a byte falls *inside*, and that is all a name is.

## The one row that still fails: `0x242C5`

Under `0x119C` at this family's own 3-byte stride, `0x242C5` fails both "keys
strictly ascending" and "the byte after the table is one of its own targets":
20 entries, keys `0x20`-`0x58`, the first two in ascending order and then not
(`0x53, 0x58, 0x4C, 0x42, 0x4F, 0x44, 0x49, 0x43` …), and a fall-through at
`0x4308` that is not one of its own targets.

**This change does not resolve it and does not make it go away.** What it does
is move it. Before, `0x242C5` failed a rule that did not belong to its reader,
so a reader could not tell it apart from the failures the same rule produced
under `0x11C2` and `0x11EF`; now it fails at its own reader's own width, and the
two readers that walk another layout no longer fail at all. A real table with
out-of-order case values would fail exactly the same way, so the checks still do
not decide between "a table this family did not emit" and "not a table of this
family at all". Reading its bytes by hand is the next step and is not attempted
here.

## The region bound, and what it does to a reader whose loop runs past its neighbour

`pd_readers()` bounds `entry_stride()`'s decode at the **next tier-2 candidate's
file offset**, falling back to `reader + 0x100`. On this image that is 38 bytes
for `0x119C`, 45 for `0x11C2` and 250 for `0x11EF` — the next tier-2 candidates
are at `0x212E9` and `0x21302`, both past `0x11EF`.

**The window is not the routine.** None of the four readers has a `ret`; all of
them leave through `jmp @a+dptr`, so a linear decode runs past the routine's end
whatever the bound is. For `0x11EF` that is 0xC1 bytes past `0x1228`, into
`load_dptr_then_indirect_jump` at `0x1229` (already named in
`ghidra-functions.csv`). `entry_stride()` takes the *last* backward
`jnz`/`sjmp` in the window, so on this image its answer is the window's answer;
that it is the reader's own loop-back is a fact about the bytes in
`load_dptr_then_indirect_jump`, not about a tight bound.

**The one tightening this makes.** `entry_stride()` now also requires the branch
it adopts to target at or after the reader's own file offset, so a backward
branch belonging to a *different* routine that reaches back past this one's head
cannot be picked up. All three PD loop-backs (`0x11A1`, `0x11C7`, `0x11F3`)
qualify and the main EC's `0x7151` returns `ENTRY_LEN` as before, so today's
answers do not move — but the caveat above is now checkable rather than merely
true today, which is the same standard `PROLOGUE_BODY_INSNS`'s short window is
held to.

**The standing limit.** A stride read off a `movc`/`inc dptr` loop is a linear
decode, not a control-flow trace: a branch that never executes counts the same
as one that does. The whole of this page is a reading of bytes.

## Two different fours

`pd_index_tables.py`'s stride 4 for `0x11C2` and the 4 bytes `pd_image_census.py`
reads inline after each call site are **unrelated quantities that happen to be
equal.** The first is the width of one dispatch record; the second is how many
inline argument bytes follow an `lcall` to the PD image's `0x104D`, read as a
pool entry. They are not the same number and neither was derived from the other.
Naming the difference here is so that a later reader does not merge them.

The second is **not a constant**, and
[`pd-code-table-inline-width.md`](pd-code-table-inline-width.md) gives it a
constant name that nothing in the tree carries. It is `CODE_TABLE_ENTRY_WIDTHS`'s
entry for the target — a per-dispatcher lookup, and the reason the two
quantities can drift apart.

## What this does not say

- **Nothing behavioural.** No register was read, no `status:` in
  [`registers.yaml`](../../ec/annotations/registers.yaml) moves, no live
  observation is claimed, and no handler of any of the decoded tables is walked.
  The decoded `target`s are CODE addresses; this change decodes tables, not
  routines.
- **A decoded table is not an executed one.** All three readers dispatch through
  `jmp @a+dptr`, which carries no address for any of the committed byte scans to
  resolve a caller edge out of, so no table here has a handler with a recorded
  caller. Still #41's input.
- **`0x11EF`'s key provenance is open.** Three call sites, and nothing decoded
  about what they put in `r4`-`r7`. `0x11C2`'s `B` is the same question one
  stride down: the compare names the register, not who writes it.
- **The main EC's three CSVs are unchanged**, which is the check that this did
  not move anything it should not have:
  `index-table-entries.csv`, `index-table-spans.csv` and
  `bank0-8038-dispatch-table.csv` all come back byte-identical, and
  `decode_index_table.py --self-test` still returns `ENTRY_LEN` for `0x07151`.

## Reproducing

No hardware, no Ghidra, no network; every input is a committed file. Both
self-tests print one line per assertion before the verdict, and the PD spans
CSV is regenerated byte-identical from the committed one by `--self-test` itself.

```console
$ python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/pd_index_tables.py --self-test
$ python3 ec/tools/pd_index_tables.py --spans-csv \
    | diff - ec/annotations/pd-index-table-spans.csv
```

The PD tool's `--self-test` also checks the two column lists differ by the two
renames and nothing else, so a column added to the main EC's `SPAN_COLUMNS`
later cannot be quietly dropped from the PD file.