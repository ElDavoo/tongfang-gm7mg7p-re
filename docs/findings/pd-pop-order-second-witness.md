# The `pop` order at PD `0x1052`/`0x1054` has a second witness, and it corroborates §3's reading (issue #1143)

**Read the headline before anything else.** All of it is static analysis of the
committed `ec/firmware/GMxMGxx_11.800`. No register was read back, no write was
attempted, nothing ran on the machine, and `ec/annotations/registers.yaml` is
untouched because no register status changed. Nothing here is evidence about
what the EC does at runtime; it is evidence about which way one byte was read.

[`pd-inline-arg-trampoline.md`](pd-inline-arg-trampoline.md) §3 measures both
readings of the two `pop`s in the PD image's `0x104D` and adopts one, and it is
careful about the difference: what the scan measures is the comparison, and
adopting the left-hand column is the inference. That inference is load-bearing —
the `resume` and `resume_opcode` columns of all 458 rows of
`ec/annotations/pd-inline-arg-sites.csv` are derived from the chosen order, and
`disasm8051.INLINE_ARG_CALLS` frames on it — so what it needed was a second
witness that is not that comparison.

**This is that witness, and it corroborates rather than closes.** It says the
byte-swapped reading does not fit this firmware's tables, by a route that does
not touch the 40-against-427 comparison at all: a different routine, in a
different program, reached by reading where that routine's `mov` instructions
put its bytes. **§7 says what this does not establish**, including that the
direction `LCALL` pushes a return address is not in question here: it pushes the
low byte first, and both `0x7151` and `0x1052` take the expected order. The
issue offered two routes and this takes the first; the second is out of scope
for the reason given in §2.

## 1. Reproducing this

Every figure below comes from one of these, from the repository root:

```console
$ python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --simulate
$ python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --pd-siblings
$ python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --self-test
...
self-test passed

$ python3 -m unittest discover -s ec/tools -p test_pop_order_oracle.py
OK

$ python3 -m unittest discover -s ec/tools -p test_pop_order_simulate.py
OK
```

`--self-test` re-derives the byte shapes §3 rests on against the image, so a
different dump re-checks them rather than inheriting this image's answer; the
suite is what puts that into a run CI collects. The two suites are separate
because they catch different mistakes: `test_pop_order_oracle.py` holds the
census to the committed spans and to the prose §9 already records, and
`test_pop_order_simulate.py` holds `--simulate`, which executes the reader's own
bytes rather than counting sites and which §5's headline claim is built on.

## 2. The route, and why the other one was left

The issue's route 1 was an oracle that is not the comparison, and it pointed at a
concrete one already in the tree.
`ec/annotations/bank-call-audit.md` §9 read the byte order off the Keil `switch`
helper at `common,0x7151` in the **main EC**, by looking at that routine's `mov`
**destinations** rather than by counting values — and that helper opens with the
identical `pop 0x83 ; pop 0x82`. §9 covers one table (`0x8038`, eight arms, named
in prose); §10 tabulates the other fourteen without measuring the order over
them. So the work is a census over a population §9 and §10 already committed, not
a new decoder.

Route 2 was **left open and is not answered here.** It asks for the ITE core's
documented `LCALL` push order, and no ITE datasheet or core manual is committed;
the single EC image is the only firmware input, so there is no second image and
no second call site whose argument bytes are known independently. A datasheet
line fetched from the web is not reproducible from committed inputs, which is
the bar CLAUDE.md sets for evidence an upstream maintainer can check.

One thing to say about route 2 plainly, because §7 of the PD write-up had it
backwards: the question as originally posed assumed a *discrepancy* between this
core and the manual, and there is none. `LCALL` pushes the low byte first, the
high byte is on top, and `pop DPH ; pop DPL` is the order that recovers it — so
route 2 would corroborate the architecture rather than settle an anomaly, and
there is no anomaly here to settle. §7 has the correction and what it does and
does not move.

**One correction to the issue's preliminary figures, which is why this file does
not use them.** The issue recorded 131 entries over the 15 tables and said `0x41F1`
and `0x424E` "do not parse". Those are table *bases*; the `lcall` sites are
`0x041EE` and `0x0424B`, three bytes earlier. `index-table-spans.csv` and
§10 carry them as well-formed — fourteen and forty-nine entries respectively — and
`decode_index_table.py --self-test` asserts every constant in §10's block against
the image. The discrepancy is a byte offset, not a disagreement about the data,
and the committed numbers are the ones carried forward. Nothing here is a second
walker over the tables: the census imports `decode_index_table`'s
`decode_table()`, `reader_call_sites()` and `malformed()` rather than restating
them, the arrangement `pd_index_tables.py` already set for the PD half, so the two
readings of the tables cannot drift from the committed one.

## 3. What `0x7151` does with the two bytes

`--self-test` pins these against the image; the decode is
[`ec/annotations/bank-call-audit.md`](../../ec/annotations/bank-call-audit.md)
§9's and is reproduced here only in the form the argument uses.

| offset | read by | meaning |
|---|---|---|
| 0 | `0x7161` `movc a,@a+dptr`, then `0x7162` `mov r0,a`, then `0x7168` `mov dph,r0` | high address byte — **DPH ends up holding offset 0** |
| 1 | `0x7163` `mov a,#1 ; 0x7165 movc a,@a+dptr ; 0x7166 mov dpl,a` | low address byte |
| 2 | `0x716C` `mov a,#2 ; movc a,@a+dptr ; 0x716F xrl a,r0` | case value, compared against the selector saved in `R0` at `0x7155` |
| — | `0x7157`/`0x715C` `movc` with `a` clear, each followed by a `jnz` | the walk stops when offsets 0 and 1 are both zero, and `0x715F`'s two `inc dptr` then pick up the two bytes after it — the default |
| — | `0x7172` three `inc dptr`, then `sjmp 0x7156` | stride 3 |

**This is the whole of §9's sentence, and it is a different claim from §3 of the
PD write-up.** Which byte of an *entry* is the high one is settled by those
`mov` destinations: it is a property of `0x7166` and `0x7168` and needs no
population to establish it. The order of the two `pop`s is one link further back —
it decides whether `DPTR` points at the table *at all* — and that is what
§4 measures. Keeping the two apart is the difference between a decode and a
measurement, and the tool prints them as two blocks for that reason.

## 4. The census, both readings side by side

```console
$ python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800
reader 0x7151 (pop-dph-dpl-selector-r0, file 0x07151), named by 15 `lcall` byte site(s)

The entry order -- `malformed()` under each reading.  The left-hand column is
what `decode_index_table.decode_table()` builds and what bank-call-audit.md §9 records;
adopting it over the other is the reading, not this tool's finding.

  site      region  entries  address big-endian        byte-swapped
  0x00DD3  common        9                  ok  1 fall-through 6 unresolvable
  0x04064  common       15                  ok  1 fall-through 15 unresolvable
  0x041EE  common       14                  ok      1 fall-through
  0x0424B  common       49                  ok  1 fall-through 9 unresolvable
  0x08035  bank0         8                  ok      1 fall-through
  0x08662  bank0         8                  ok      1 fall-through
  0x0918A  bank0        10                  ok      1 fall-through
  0x09284  bank0         7                  ok      1 fall-through
  0x0A34A  bank0         7                  ok      1 fall-through
  0x0A682  bank0         7                  ok      1 fall-through
  0x0D148  bank0        12                  ok      1 fall-through
  0x0D435  bank0        24                  ok      1 fall-through
  0x0DDBB  bank0        16                  ok      1 fall-through
  0x0EBDC  bank0         8                  ok      1 fall-through
  0x0F254  bank0         7                  ok      1 fall-through
...
  15 candidate site(s); well-formed: 15 of 15  0 of 15
  A well-formed verdict is corroboration, not proof: a run of data can pass all
  three clauses without being a table (bank-call-audit.md §10.2).
```

The fifteen sites, their entry counts and their spans are §10's, re-derived
through the import rather than re-walked, and the two agree: the tool's census
and `ec/annotations/index-table-spans.csv` are compared row by row in
`test_pop_order_oracle.py`, in both directions, so a row that drifted in either
file would fail. **Nothing in §10 is edited by this file.** If the run had
disagreed with it, that would be a finding about §10 with its own issue, and this
one would record the disagreement and stop.

### Which of `malformed()`'s three clauses is doing the work

It is worth being precise about which clause separates, because it is not the one
a reader might expect. `malformed()` asks three things: case values strictly
ascending; every target and the default resolving inside the caller's own region;
and the byte after the table being one of its own targets.

**The resolution clause does almost nothing on the banked tables, and the tool
prints its column separately precisely so that cannot be misread.** For a
banked caller the region `offset_for_runtime()` resolves against is
`0x8000`-`0xFFFF`, and a byte-swapped `0x80D7` is `0xD780` — still inside it. So
on every banked table the count is zero under *both* readings, and on twelve of
the fifteen tables it is zero both ways. The column would read as "no
difference" on those, if it were the only one; the three that do move are all
common-area, where a swapped address above `0x8000` is not resolvable at all.

The clause that separates is the fall-through one: the byte after the table must
be one of its own targets, because that is the jump a compiler emits into the
first case. Exchange the two address bytes and the set of targets changes while
the address immediately following the table does not, so every table fails it —
including the twelve where resolution could not tell them apart. The
case-ascending clause is unaffected by either reading, since it reads the third
byte.

So the sharp statement is a site-level one: **15 of 15 tables are well-formed
under the reading §9 records and 0 of 15 under the swap**, and on the banked
tables the reason is specifically the fall-through clause. One site's reasons in
full, because the cells above are counts:

```console
What the second column is counting, in full, for the table at file 0x00DD6
(the `lcall` at 0x00DD3, 9 entries):

    entry target 0x0DF5 -> 0xF50D
    entry target 0x0DF7 -> 0xF70D
    entry target 0x0DF9 -> 0xF90D
    entry target 0x0DFB -> 0xFB0D
  default      0x0E0D -> 0x0D0E
  first entry case 0x02 at file 0x00DD6, unchanged by either reading -- the case byte is
  the third byte of an entry and the swap only exchanges the two address bytes in front of it

    byte-swapped: 0xF70D does not resolve from common
    ...
    byte-swapped: the byte after the table (0x0DF5) is not one of its own targets
```

`0xDF5` is the first arm, and it is also the byte immediately after the table —
the compiler's fall-through into case `0x02`. Under the direct reading it is both,
so the clause holds; under the swap it is `0xF50D` as an arm and still `0x0DF5` as
the following byte, and the two no longer agree. That is the whole mechanism in
one line.

### Arm locality, and why it is only a proxy

| site | `address big-endian` | `byte-swapped` |
|---|---|---|
| `0x00DD3` | 6/9 | 0/9 |
| `0x04064` | 15/15 | 0/15 |
| `0x041EE` | 0/14 | 0/14 |
| `0x0424B` | 9/49 | 1/49 |
| `0x08035` | 3/8 | 0/8 |
| `0x08662` | 8/8 | 0/8 |
| `0x0918A` | 10/10 | 0/10 |
| `0x09284` | 7/7 | 0/7 |
| `0x0A34A` | 6/7 | 0/7 |
| `0x0A682` | 5/7 | 0/7 |
| `0x0D148` | 8/12 | 0/12 |
| `0x0D435` | 24/24 | 1/24 |
| `0x0DDBB` | 5/16 | 0/16 |
| `0x0EBDC` | 1/8 | 0/8 |
| `0x0F254` | 2/7 | 0/7 |

Entries landing in the same 256-byte page as their own table base. **This is a
proxy and is reported as a rate, never as a fraction of every arm**, for two
reasons that are both visible in the table. A `switch` arm may legitimately point
forward into the next page or backward into the previous one, which is why
`0x0D435` reads 24 of 24 and `0x0EBDC` reads 1 of 8 under the direct reading
alone. And `0x041EE`'s fourteen arms all sit one page above their own base, so
both readings score it 0-of-14 and the column is **silent** there — a fact the
suite asserts rather than rounding away, because a column that separated
everywhere would be being read as a test and it is not one.

The proxy is here because §9 and §10 recorded what it can and cannot carry, and
because a reader who wants to see the separation for themselves should have it
next to the clause that actually decides. It is not the load-bearing column and
the tool says so in its own output.

## 5. The link back to the two `pop`s, which is the part that is new

The entry order is settled by the bytes. What §3 of the PD write-up needed was a
witness for the *other* link: that the two `pop`s put `DPTR` on the table at all.
So the tool runs the same walk from the byte-swapped return address — the
address the `lcall` pushed with its two bytes exchanged, which is what DPTR would
hold if `pop 0x83` took the low byte.

```console
  site      region  return    swapped   entries found  case values
  0x00DD3  common  0x0DD6    0xD60D     unresolvable  0xD60D does not resolve from common
  0x04064  common  0x4067    0x6740             none  no `00 00` terminator within 64 entries
  0x041EE  common  0x41F1    0xF141     unresolvable  0xF141 does not resolve from common
  0x0424B  common  0x424E    0x4E42             none  no `00 00` terminator within 64 entries
  0x08035  bank0   0x8038    0x3880             none  no `00 00` terminator within 64 entries
  0x08662  bank0   0x8665    0x6586             none  no `00 00` terminator within 64 entries
  0x0918A  bank0   0x918D    0x8D91             none  no `00 00` terminator within 64 entries
  0x09284  bank0   0x9287    0x8792             none  no `00 00` terminator within 64 entries
  0x0A34A  bank0   0xA34D    0x4DA3             none  no `00 00` terminator within 64 entries
  0x0A682  bank0   0xA685    0x85A6             none  no `00 00` terminator within 64 entries
  0x0D148  bank0   0xD14B    0x4BD1             none  no `00 00` terminator within 64 entries
  0x0D435  bank0   0xD438    0x38D4             none  no `00 00` terminator within 64 entries
  0x0DDBB  bank0   0xDDBE    0xBEDD             none  no `00 00` terminator within 64 entries
  0x0EBDC  bank0   0xEBDF    0xDFEB             none  no `00 00` terminator within 64 entries
  0x0F254  bank0   0xF257    0x57F2             none  no `00 00` terminator within 64 entries
```

**Under the swap, not one of the fifteen has a table there.** Two of the swapped
addresses are above `0x8000` and are not resolvable from the common area at all —
nothing in the byte says which bank is mapped, which is
`trace_xdata_refs.offset_for_runtime()`'s own rule and not a measurement of this
one. The other thirteen resolve to a file offset and find no `00 00` terminator
within `decode_index_table.MAX_ENTRIES`. That is a `0` and it reads **"no table
is there by this method"**, never "no table exists": a `switch` table elsewhere in
the image would not be found by starting the walk at a fixed address, and the two
unresolvable rows are the region rule rather than evidence at all.

`--simulate` is §9's sentence made runnable. It executes the reader's own 38 bytes
over the `0x8038` table under both push orders, differing in nothing but which
stack byte the first `pop` takes:

```console
$ python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --simulate
reader 0x7151 entered with its return address 0x8038 on the stack
and a selector of 0x00 in A.  The table is at file 0x08038, runtime
0x8038 (bank0), 8 entries of 3 bytes, first case 0x00 at 0x8054.

==============================================================================
the two `pop`s take 0x80 then 0x38, so DPTR = the return address
==============================================================================
  0x7151  d0 83    pop  0x83           A=0x00 R0=0x22 DPL=0x33 DPH=0x80  DPTR=0x8033
  0x7153  d0 82    pop  0x82           A=0x00 R0=0x22 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7155  f8       mov  r0,a           A=0x00 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7156  e4       clr  a              A=0x00 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7157  93       movc a,@a+dptr      A=0x80 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7158  70 12    jnz  0x716c         A=0x80 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x716C  74 02    mov  a,#0x02        A=0x02 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x716E  93       movc a,@a+dptr      A=0x00 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x716F  68       xrl  a,r0           A=0x00 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7170  60 ef    jz   0x7161         A=0x00 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7161  93       movc a,@a+dptr      A=0x80 R0=0x00 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7162  f8       mov  r0,a           A=0x80 R0=0x80 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7163  74 01    mov  a,#0x01        A=0x01 R0=0x80 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7165  93       movc a,@a+dptr      A=0x54 R0=0x80 DPL=0x38 DPH=0x80  DPTR=0x8038
  0x7166  f5 82    mov  0x82,a         A=0x54 R0=0x80 DPL=0x54 DPH=0x80  DPTR=0x8054
  0x7168  88 83    mov  0x83,r0        A=0x54 R0=0x80 DPL=0x54 DPH=0x80  DPTR=0x8054
  0x716A  e4       clr  a              A=0x00 R0=0x80 DPL=0x54 DPH=0x80  DPTR=0x8054
  0x716B  73       jmp  @a+dptr        A=0x00 R0=0x80 DPL=0x54 DPH=0x80  DPTR=0x8054

  18 instruction(s) executed; `clr a ; jmp @a+dptr` transfers to 0x8054, which is case 0x00 of
  the table this call carries -- a handler that exists.
```

`0x7165` reads offset 1 and `0x7168` puts offset 0 in `DPH`, and the dispatch
lands on `0x8054` — a real handler. Under the swap the same routine walks
`0x3880` upward three bytes at a time, matching no case and reaching no `00 00`:

```console
==============================================================================
the two `pop`s take 0x38 then 0x80, so DPTR = the byte-swapped 0x3880
==============================================================================
  0x7151  d0 83    pop  0x83           A=0x00 R0=0x22 DPL=0x33 DPH=0x38  DPTR=0x3833
  0x7153  d0 82    pop  0x82           A=0x00 R0=0x22 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x7155  f8       mov  r0,a           A=0x00 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x7156  e4       clr  a              A=0x00 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x7157  93       movc a,@a+dptr      A=0xF8 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x7158  70 12    jnz  0x716c         A=0xF8 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x716C  74 02    mov  a,#0x02        A=0x02 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x716E  93       movc a,@a+dptr      A=0x10 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x716F  68       xrl  a,r0           A=0x10 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x7170  60 ef    jz   0x7161         A=0x10 R0=0x00 DPL=0x80 DPH=0x38  DPTR=0x3880
  0x7172  a3       inc  dptr           A=0x10 R0=0x00 DPL=0x81 DPH=0x38  DPTR=0x3881
  0x7173  a3       inc  dptr           A=0x10 R0=0x00 DPL=0x82 DPH=0x38  DPTR=0x3882
  0x7174  a3       inc  dptr           A=0x10 R0=0x00 DPL=0x83 DPH=0x38  DPTR=0x3883
  0x7175  80 df    sjmp 0x7156         A=0x10 R0=0x00 DPL=0x83 DPH=0x38  DPTR=0x3883
  0x7156  e4       clr  a              A=0x00 R0=0x00 DPL=0x83 DPH=0x38  DPTR=0x3883
  0x7157  93       movc a,@a+dptr      A=0x46 R0=0x00 DPL=0x83 DPH=0x38  DPTR=0x3883
  ...
  512 instruction(s) executed and the walk reached no dispatch in 512 instructions and left DPTR at 0x380A.
```

`0x3880` is not the table; it is ordinary code in the common area, and the walk
reads its bytes as case values until the low byte of `DPTR` wraps. That is the
visible form of §9's reading being wrong: the routine is fine, the pointer is not
on a table.

## 6. The other eight `pop dph ; pop dpl` sites, as population

```console
$ python3 ec/tools/pd_pop_order_oracle.py ec/firmware/GMxMGxx_11.800 --pd-siblings
`d0 83 d0 82` occurs 9 time(s) in this dump, by a byte scan over the whole file;
1 in common, 8 in pd-image.

  file      runtime   region     tier    shape                        `lcall` sites
  0x07151  0x7151    common     tier 2  pop-dph-dpl-selector-r0     15
  0x21052  0x1052    pd-image   tier 1  pop-dph-dpl                 0  (not found by this method)
  0x2113E  0x113E    pd-image   tier 1  pop-dph-dpl                 0  (not found by this method)
  0x21157  0x1157    pd-image   tier 1  pop-dph-dpl                 0  (not found by this method)
  0x2119C  0x119C    pd-image   tier 2  pop-dph-dpl-selector-r0     9
  0x211C2  0x11C2    pd-image   tier 2  pop-dph-dpl-selector-r0     16
  0x211EF  0x11EF    pd-image   tier 2  pop-dph-dpl                 3
  0x212E9  0x12E9    pd-image   tier 2  pop-dph-dpl                 0  (not found by this method)
  0x21302  0x1302    pd-image   tier 2  pop-dph-dpl                 0  (not found by this method)
```

A reader will ask why the oracle is `0x7151` and not one of the eight PD-side
sites, so the reason is worth the space:

- `0x21052` is the pair **inside** `0x104D` — the routine
  [`pd-inline-arg-trampoline.md`](pd-inline-arg-trampoline.md) is about, and the
  one whose two `pop`s this whole file exists to give a second witness to. It is
  named here as the question, not analysed as a candidate.
- `0x2113E` and `0x21157` are neither readers nor dispatchers: both pop three
  more bytes after the pair, into `A` and then `r1`/`r2`/`r3`. That is an
  argument-unpacking shape.
- `0x2119C` and `0x211C2` carry the same `d0 83 d0 82 f8` prologue as `0x7151`
  and are named by `lcall` sites. Their tables are `pd_index_tables.py`'s subject
  and are decoded there — and their entry widths are **not** this family's:
  `0x119C` walks three-byte entries like `0x7151`, while `0x11C2` walks four and
  `0x11EF` six, which is `pd_index_tables.py`'s `reader_stride` column and the
  reason its `well_formed` verdict under the three-byte rule is explicitly not a
  verdict about those tables. `0x11EF` also drops the selector save, so the
  enumerated shape names it `pop-dph-dpl` rather than
  `pop-dph-dpl-selector-r0`.
- `0x12E9` and `0x1302` are a third shape again: four `movc a,@a+dptr` reads at
  offsets 0 through 3, each stored and `r0` incremented by one — through `mov
  @r0,a`, internal RAM, in the first and `movx @r0,a`, XDATA, in the second —
  then, with no `inc r0` after the fourth, `mov a,#4 ; jmp @a+dptr` to resume at
  `DPTR+4`. That is `0x104D`'s exact shape, a four-byte inline argument resumed
  four bytes on, with a different destination; note the tail needs no `clr a`
  where `0x104D` has one, because `mov a,#4` sets the offset outright. Neither
  reads a table at all. Their analysis is a separate investigation with its own
  oracle work.

**A zero `lcall` count is "not found by this method" and never "there is no
caller".** A dispatch through a table is not a `12 xx xx` byte sequence, so this
scan cannot see it; `pd-inline-arg-trampoline.md` §7 already applies the caveat
to the EC-side zero. If `0x12E9` and `0x1302` do have four-byte inline arguments
at sites no `lcall` byte names, extending `disasm8051.INLINE_ARG_CALLS` would
re-frame rows in committed CSVs across three tables — which is a new issue with
its own `--check` sweep, not a row added here.

[`table-reader-spellings.md`](table-reader-spellings.md) reads the shapes across
both images, and `pd_index_tables.py` censuses the PD's own tables. This file
does not repeat either.

## 7. What this does not establish

- **Not that the swapped reading is impossible.** Only that it does not fit these
  tables. A firmware that dispatched through `DPTR` to somewhere other than a
  `switch` table would not be contradicted by anything here.
- **Not a departure from the architecture.** `LCALL` pushes the return address's
  **low** byte first, so the **high** byte is on top of the stack, and `pop DPH`
  then `pop DPL` is the order that recovers it — the order both `0x7151` and
  `0x1052` take. `boot_xdata_sites.py`'s `_push_return` documents and implements
  that push order, and `trampoline-target-reading.md` records `ret` popping the
  caller's `PCH` then its `PCL`, which is the same fact from the other end.
  **Correction to an earlier conclusion in this repository:** the PD write-up's
  §3 read the same pair the other way round — "the MCS-51 `lcall` pushes the
  return address high byte first" — and built a `why does this core differ from
  the manual` question on it. That was backwards; the wrong sentence is left in
  place with a correction beside it in
  [`pd-inline-arg-trampoline.md`](pd-inline-arg-trampoline.md) §3 rather than
  silently edited. What §3's inference actually was — and what this file's
  census now corroborates — is which of the two readings **these tables** fit,
  which is a question about the tables and not about the architecture.
- **Not that any handler executes.** Every figure is a decode. The census counts
  *static* sites and says nothing about which run, how often, or in what order;
  §6's argument is the same one `pd-inline-arg-trampoline.md` §7 makes.
- **Not control flow, and not a second image.** Nothing here recovers control
  flow — `disasm8051.py` decodes linearly and stops at the first branch. And with
  one EC image there is no second firmware input whose tables could be read the
  same way and compared.
- **Nothing observed on hardware.** No register was read back, no write was
  attempted, nothing was run on the machine. Static analysis of a committed image,
  and that is all it is.
- **A zero is "not found by this method".** The swapped-base column's zeros and
  the two unresolvable rows both say that, and §5 says why the two are not the
  same thing.

## 8. What changed elsewhere

[`pd-inline-arg-trampoline.md`](pd-inline-arg-trampoline.md) §3, §7 and §8
item 3 are amended in place. The `--pop-order` table and the mechanism paragraph
stand as written and are not touched. §3's heading claim about the manual is
**corrected**, with the wrong sentence left visible beside the correction rather
than silently edited, and §7 and §8 item 3 drop the cause framing that was hung
on it — what those two now carry is that the *reading* has a second witness and
that the census is a decode over committed tables which says nothing about which
routines execute.
[`INDEX.md`](INDEX.md) carries the row for this file, generated by
`gen_findings_index.py`. [`ec/annotations/bank-call-audit.md`](../../ec/annotations/bank-call-audit.md) is
cited, not edited; `registers.yaml`, the committed index-table CSVs and
`pd-inline-arg-sites.csv` are all unchanged, and the tool writes no CSV of its
own.
