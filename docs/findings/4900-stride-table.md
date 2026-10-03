# The 0x4900 stride table: how far it runs, what geometry the two strides imply, and what the index is

`docs/findings/common-runtime-tranche.md` §"The rest" recorded two stride
constructions under `common 0x4900` and stopped, because without the table
neither meant much. This measures the table over the committed image
`ec/firmware/GMxMGxx_11.800` and answers the four questions that were open,
each with the command that produces the answer. The tool is
[`ec/tools/stride_index_table.py`](../../ec/tools/stride_index_table.py); it
reads committed files only and writes nothing but stdout.

Nothing here was read back from hardware and nothing here needs it. Every
figure below is over bytes already in the repository, and a zero is "not found
by this method", never "absent".

## The dump

```
python3 ec/tools/stride_index_table.py ec/firmware/GMxMGxx_11.800 --at 0x4900 --len 0x128
```

```
0x4900, 296 byte(s). The record-like run the constructions address is 0x494E-0x4A25 (216 bytes).

04900  4A 76 12 4A 4D E0 54 F1 F0 7B 01 80 14 90 0A 58  |Jv.JM.T..{.....X|
04910  E0 60 9E 12 4A 41 74 FE F0 02 48 B1 12 49 47 E4  |.`..JAt...H..IG.|
04920  FB 12 4A FB EB 70 06 CF E9 CF 12 43 A5 12 4A 76  |..J..p.....C..Jv|
04930  12 4A 4D E0 54 F1 12 4A 40 74 FE F0 CF EB CF 22  |.JM.T..J@t....."|
04940  CF E9 CF 12 43 A5 22 CF E9 CF 12 43 A5 22 1C 01  |....C."....C."..|
04950  1C 03 1C 02 1C 00 1C 04 1C 05 1C 06 11 05 11 01  |................|
04960  02 1C 07 1C 12 1C 14 1C 13 1C 11 1C 15 1C 16 1C  |................|
04970  17 11 05 11 01 04 1C 18 1C 2A 1C 2C 1C 2B 1C 29  |.........*.,.+.)|
04980  1C 2D 1C 2E 1C 2F 11 06 11 02 01 1C 30 1C 36 1C  |.-.../......0.6.|
04990  38 1C 37 1C 35 1C 39 1C 3A 1C 3B 11 04 11 00 10  |8.7.5.9.:.;.....|
049A0  1C 3C 1C A1 1C A3 1C A2 1C A0 1C A4 1C A6 1C A7  |.<..............|
049B0  11 55 11 54 01 1C A8 1C B1 1C B3 1C B2 1C B0 1C  |.U.T............|
049C0  B4 1C B6 1C B7 11 55 11 54 02 1C B8 1C 00 1C 10  |......U.T.......|
049D0  1C 0A 16 1B 16 1C 16 02 18 00 89 1C 11 1C 21 1C  |..............!.|
049E0  1B 16 21 16 22 16 03 06 00 8A 1C 29 1C 32 1C 31  |..!."......).2.1|
049F0  16 3E 16 3F 16 06 C0 00 8B 1C 35 1C 3E 1C 3D 16  |.>.?......5.>.=.|
04A00  49 16 4A 16 08 06 00 8C 1C A0 1C AA 1C A9 16 30  |I.J............0|
04A10  16 37 16 05 81 00 F8 1C B0 1C BA 1C B9 16 14 16  |.7..............|
04A20  15 16 01 30 00 F9 FF E9 75 F0 15 A4 24 50 F5 82  |...0....u...$P..|

```

`disasm8051.py` cannot produce this dump. It has no hex mode, and its `-n`
counts instructions rather than bytes, so `--at 0x4900 -n 200` frames the run
as garbage instructions and reports the framing as if it were the finding. A
dump of a byte run is not a decode and is printed as one.

## 1. Where the block starts and ends, and whether the two strides partition the same region

**One region, not two.** Every construction in §2 builds an address in the same
216 bytes, `0x494E`–`0x4A25`. The two strides walk that run at different step
sizes and nothing else.

The **lower** bound is firm and has two independent supports:

* `0x494D` is a `ret`. The function the committed export places immediately
  below the run is `common 0x4947`, seven bytes ending there, and a forward
  `walk_branch_arms.descend()` from its seed decodes five instructions and
  stops at that `ret` without decoding `0x494E`.
* `+0x4E` is the lowest base offset any of the constructions uses, and
  `0x4900 + 0x4E` is `0x494E` — the byte immediately after that `ret`. So the
  lowest address the arithmetic reaches is the first byte after the last
  instruction the export places there.

The **upper** bound is one byte weaker and is stated as such. `0x4A26` is a
call target in the committed listings (`bank1/4874.asm` calls it) and
`ec/decompiled/index.csv` exports it as a function entry, so the run is
declared to end at `0x4A25`, the byte before it. Nothing in the committed tree
independently settles `0x4A25` itself: it is one `mov R1,A` in the middle of
the run's tail and it could as well be a final entry byte. The run's declared
length is therefore a lower bound on the data, not an exact end.

```
python3 ec/tools/stride_index_table.py ec/firmware/GMxMGxx_11.800 --boundary
```

```
the two ends of the declared run, and the two functions they are bracketed by

  0x494E  0x494E (run start)
         converges: 24 of 24 nearby anchors
  0x4A26  0x4A26 (byte after the run)
         converges: 24 of 24 nearby anchors
  0x494E  walk from bracketing function below the run
         common 4947 FUN_CODE_4947, seed 0x4947: run start not-reached, byte after the run not-reached; the walk ended at ret
  0x494E  walk from bracketing function above the run
         bank1 4A26 code_table_pointer_from_r1, seed 0x4A26: run start not-reached, byte after the run reached-by-walk; the walk ended at DPTR built at run time (a store to DPL/DPH); ret
  0x4A25  run length at the 2-byte entry width
         108 entries cover it exactly (216 of 216 bytes), with 49 distinct bytes at the entry offsets
```

Three things in that output are worth reading carefully rather than skipping.

**The convergence counts decide nothing, and that is the point.** 24 of 24 at
both ends is what a run of two-byte entries does: every offset in it is a
plausible instruction boundary, so a linear walk syncs onto all of them. If
this page had stopped at `--converge` it would have "established" that the run
is code. The walk verdict beside it is the one that carries information, and it
is `walk_branch_arms.descend()`'s verdict, not a new one: a flow walk reports
whether it decoded the byte as an instruction, and it cannot tell code from a
table it wandered into. Both ends are reported as `not-reached` by the walk
from below, which is a negative this method decided (the walk finished and the
byte is not in it), not "the byte is data".

**The upper-bound walk says `reached-by-walk` for its own entry.** That is
tautological — the seed *is* `0x4A26` — and it is printed rather than hidden
so a reader can see that the run's upper bound rests on the call target and
the export, not on the walk.

## 2. How many constructions there are — the issue's five, and what a scan finds

The issue named five sites: `common 0x4A42`, `common 0x43A5` (which it
described as three constructions), and `common 0x4A76`. Scanning the image for
the construction's own byte shape finds more, and the census is the scan's:

```
python3 ec/tools/stride_index_table.py ec/firmware/GMxMGxx_11.800 --sites --base 0x49
```

The shape is eleven bytes — `mov B,#stride / mul AB / add A,#off / mov DPL,A /
clr A / addc A,#base_hi` — and **the `mov DPH,A` that finishes the pointer is
not part of it**. A scan that included that store would find the sites that
store `DPH` themselves and miss the ones that `ret` with the page still in the
accumulator, leaving the following `lcall` to store it. On this image that is
the majority, so such a scan would report the majority of the census absent.
The store is therefore a reported column, not a pattern byte.

Over the whole image the eleven bytes occur at 193 offsets, 28 of them in the
common area, 15 in bank0, none in bank1, and the rest in the separate
`ITE8850-PD` image at file `0x20000`. Of the common-area sites, the ones that
build an address into page `0x49` are the nineteen below, and every one of them
is on an instruction line of a committed `.asm` listing — the cross-check that
separates a census from a byte scan, since a linear scan also finds the eleven
bytes inside somebody's immediate operand.

The last column is `--sites`'s own `function` cell, verbatim: the innermost
`ec/decompiled/index.csv` row whose extent covers the site, as `scope`, `addr`
and `name`. A `FUN_CODE_*` name is a placeholder the export carries and no
annotation row names, which is the whole of what an "annotated" flag would add
here, so the name is left to say it.

| site | stride | `base_off` | index register | owning exported function |
|---|---|---|---|---|
| `common 0x43B1` | 15 | `+0xCC` | R6 | `common 43A5 per_channel_state_sequence_on_15byte_stride_table_43a5` |
| `common 0x43F6` | 15 | `+0xD6` | R6 | `common 43A5 per_channel_state_sequence_on_15byte_stride_table_43a5` |
| `common 0x440B` | 15 | `+0xD8` | R6 | `common 43A5 per_channel_state_sequence_on_15byte_stride_table_43a5` |
| `common 0x454F` | 21 | `+0x61` | an XDATA read | `common 451A FUN_CODE_451a` |
| `common 0x4A28` | 21 | `+0x50` | R1 | `bank1 4A26 code_table_pointer_from_r1` |
| `common 0x4A42` | 21 | `+0x54` | R1 | `common 4A42 dptr_from_21byte_stride_index` |
| `common 0x4A5E` | 21 | `+0x4E` | an XDATA read | `common 4A5E FUN_CODE_4a5e` |
| `common 0x4A77` | 15 | `+0xCE` | R1 | `common 4A77 FUN_CODE_4a77` |
| `common 0x4A84` | 21 | `+0x4E` | R6 | `common 4A83 FUN_CODE_4a83` |
| `common 0x4AA7` | 21 | `+0x5A` | R1 | `common 4AA7 FUN_CODE_4aa7` |
| `common 0x4AB8` | 21 | `+0x50` | an XDATA read | `common 4AB8 FUN_CODE_4ab8` |
| `common 0x4AC5` | 21 | `+0x4E` | R1 | `common 4AC4 FUN_CODE_4ac4` |
| `common 0x4AD3` | 21 | `+0x54` | an XDATA read | `common 4AD3 FUN_CODE_4ad3` |
| `common 0x4AE0` | 21 | `+0x56` | R7 | `common 4AE0 FUN_CODE_4ae0` |
| `common 0x4AEF` | 21 | `+0x52` | R6 | `common 4AEF FUN_CODE_4aef` |
| `common 0x4B03` | 15 | `+0xD0` | R6 | `common 4B03 FUN_CODE_4b03` |
| `common 0x4B13` | 21 | `+0x58` | an XDATA read | `common 4B0F FUN_CODE_4b0f` |
| `common 0x4B2B` | 15 | `+0xD4` | R6 | `common 4B29 FUN_CODE_4b29` |
| `common 0x4B38` | 15 | `+0xD2` | R6 | `common 4B37 FUN_CODE_4b37` |

`common 0x4A77` is the one whose annotated neighbour is not its own entry: the
construction is the second instruction after `common 0x4A76
dptr_4900_plus_15x_r1`, and the export gives the instruction its own one-byte
row because of the function-boundary question issues #617 and #652 discuss.
That row is cited here as an anchor and the boundary is not re-opened.

The issue's five are the sites whose construction an annotation row already
names: `common 0x43A5` holds three of them, `common 0x4A42` one, and
`common 0x4A76` one — the last by the neighbour the paragraph above describes.
Fourteen more exist, thirteen of them in the run of pointer builders at
`0x4A26`–`0x4B40`, and the one outside it is `common 0x454F`. The issue's count
is left visible here rather than edited away; what changed is that it was a list
of the *annotated* sites rather than of the constructions, and that is the whole
of the difference. The last column above says which is which, per site, and is
what to read rather than the count.

## 3. Record counts, and what the `+0x54` / `+0xCC` / `+0xD6` / `+0xD8` offsets are

```
python3 ec/tools/stride_index_table.py ec/firmware/GMxMGxx_11.800 --records --stride 15
python3 ec/tools/stride_index_table.py ec/firmware/GMxMGxx_11.800 --records --stride 21
```

**They are mid-record field offsets, on a grid of the site's own stride. They
are not record heads and they are not two separate sub-tables.**

At stride 15, `common 0x43A5`'s three constructions land on record 8 field 6,
record 9 field 1 and record 9 field 3 of the grid that starts at the **run's
first byte, `0x494E`** — where `+0x4E`, the lowest base offset any site on this
block uses, is record 0 field 0. At stride 21 they land on record 6 field 0,
record 6 field 10 and record 6 field 12 — the same three addresses, named as
three fields of one 21-byte record six records in. Both readings are printed for
every site; neither is the answer, because the bytes do not choose.

The anchor matters and is named in every one of these numbers: the grid is
counted from `0x494E`, not from `0x43A5`'s own `+0xCC` base at `0x49CC`, which
that grid places at record 8 field 6 rather than at record 0. §7 keeps the two
apart for the walk as well — `steps_from_base_cc` is five where
`steps_from_run_start` is fourteen — because an index printed without the grid
it was computed on is a number with nothing to check it against.

**The record count is two measurements and this page will not merge them.**

1. *How many whole records of that stride fit in the declared run.* The run is
   216 bytes: fourteen whole 15-byte records with 6 bytes over, ten whole
   21-byte records with 6 bytes over.
2. *How far the 8-bit walk gets from a given anchor before it leaves the run.*
   From the run's first byte, fourteen steps at stride 15 and ten at stride 21;
   from the `+0xCC` base, five at stride 15 and four at stride 21.

They are different questions with different answers, and the tool prints both
on every run. A reader who wants one "record count" is looking for something
the arithmetic does not supply: **15 and 21 are both odd, so
`A*stride mod 256` is a bijection over all 256 index values and the
construction admits every 8-bit index.** The tool refuses an even stride
outright for the same reason — at an even parity the index maps onto half the
offsets, so the record count it implies is a different claim.

**One tiling is worth recording and one is refuted.**

The run's 216 bytes are a whole number of 2-byte entries from its first byte,
and the byte after the last one is `0x4A26`, the call target. The run is also
a whole number of 15-byte records *from the `+0xCC` base*: `0x49CC` to
`0x4A25` is 90 bytes, six records, and `0x49CC + 90` is `0x4A26`. The same
arithmetic at stride 21 does not land: from the run's first byte, 216 is ten
21-byte records and 6 bytes over, so the 21-grid does not end on the boundary
above the run.

The 15-byte fit is one observation and not a proof. 90 is divisible by 15 and
`0x49CC + 90` lands on a function entry, but 15 is one of two strides the byte
pattern would have to be lucky about, and the run has an even length whichever
stride is tried — which is why this is recorded beside the refuted one and not
leaned on.

*(A hypothesis worth keeping beside this: that the two strides are two record
geometries over the same bytes — one table, two grids — is what this page set
out to test and it does not survive the arithmetic. 21 tiles nothing whole. The
reading that does fit every base offset is that the entries are two bytes wide
and the strides are index steps over them, not record widths: every base offset
the constructions use is even — `0x4E`, `0x50`, `0x52`, `0x54`, `0x56`,
`0x58`, `0x5A`, and `0xCC`, `0xCE`, `0xD0`, `0xD2`, `0xD4`, `0xD6`, `0xD8` —
except `+0x61`, and both strides are odd, so a walk steps from an even offset
to an odd one and back. That is what a 2-byte entry stream looks like walked at
an odd stride. What the entries *are* is §5's open question.)*

## 4. The index register, and whether the constructions agree on a count

```
python3 ec/tools/stride_index_table.py ec/firmware/GMxMGxx_11.800 --index-range
```

The register is read out of the committed listing each site sits in, backwards
to the end of its block. **Eight sites index with R6, five with R1, one with
R7, and five with a read this tool does not follow** — `common 0x454F`,
`0x4AB8`, `0x4AD3` and `0x4B13` take it from a `movx A,@DPTR`, and
`common 0x4A5E` from the XDATA byte `0x0A17` its own DPTR points at.
`--index-range` prints the register per site, so the split above is a reading
of that column and not a separate count.

**The register a site's own listing names is not always the register its
callers write**, and `common 0x43A5` is the case. All three of its
constructions end in `mov A, R6`, which is why §2's column says R6, but the
entry's own prologue at `0x43A5`-`0x43A8` is
`xch A, R6 / mov A, R7 / xch A, R6 / mov A, R6`: it moves the caller's R7 into
R6 and discards the caller's R6, so the index the stride arithmetic multiplies
is the caller's R7. `--index-range` follows that prologue, and six of the seven
committed call sites then answer with a run-time value — `common 451A` at
`0x45A3` and `0x45BB` and `common 46F9` at `0x4704` from an XDATA byte, read
through `0x0A56` and `0x0A17` respectively, and `common 4921`, `common 4940` and
`common 4947` from R1 by the same `xch A, R7 / mov A, R1 / xch A, R7` hand-off.
`common 4666` at `0x4685` writes R6 at `0x4676` and writes R7 nowhere before the
call, so what its index is is not established by these listings.

**No committed listing passes a literal index to any of them.** Every caller
row `--index-range` prints is one of three cells: a run-time value, the bounded
`no constant within this window of the call in the caller's own listing`, or
`index register not named at the site`, where the site's own index load is a
read this tool does not follow. The second is a negative about four listing
lines, not a statement about what the register holds at run time and not a
statement about every caller. The callers the tool enumerates agree with
`ec/annotations/call-graph-callees.csv`'s own `inbound` count for every entry
that CSV has a row for — `common 0x43A5` has seven in both, `common 0x4A42`
four in both — which is a cross-check between two derivations rather than a
restatement of one. The one entry with no row, `common 0x4B03`, is one this
tool finds no caller for either; that is consistent, but it is "not found by
this method" rather than a second derivation agreeing with the first.

So the answer to "whether they agree on a record count" is **that the question
cannot be asked from these files**, and saying so is the finding. Two registers
appear among them, R6 and R1 -- the issue called `0x4A42`'s index `A`, which is
where the `mov A,R1` in front of it leaves the accumulator. An odd stride bounds
nothing on top of that. What the firmware can pass at run time is not recorded
anywhere in this repository, and this page does not infer it.

## 5. What this does not establish

* **What the entries mean.** The run reads as an opcode-like stream — `1C NN`,
  `11 NN`, `16 NN`, `06 NN`, `18 00`, `89 1C` — and that is a real lead and a
  separate job. Nothing above decodes it, and the 49 distinct bytes at the
  entry offsets are a measurement of that vocabulary's size, not of its
  meaning.
* **That the run is data rather than code.** §1 gives a walk's verdict and a
  call target. A flow walk cannot tell code from a table it wandered into, and
  `disasm8051.py --converge` answers 24 of 24 at both ends of the run, so the
  framing evidence it offers is the uninformative answer.
* **That any index range is reachable.** See §4.
* **That `0x4900` is a register.** It is a CODE address, and
  `ec/annotations/registers.yaml` is XDATA-scoped, so no row is implied here
  and none was added. `ec/ghidra/xdata-symbols.csv` is generated from that file
  and `gen_xdata_symbols.py --check` is in the gate.
* **That a region entry belongs in `ec/annotations/data-regions.yaml`.** It is
  the obvious home for an extent, and `data_regions.py --for-offset 0x4900`
  still answers `not listed`. `SHAPES` in that tool is a closed vocabulary
  (`ljmp-table`, `be-words`, `ff-triples`, `addresses`, `repeat-bytes`) and a
  stride-indexed record table honestly fits none of them; adding one is a new
  `--check` branch against every existing region in a shared tool, for an
  extent this page's own suite already holds by digest.

## 6. What to do next

* Annotate the rows §2's last column still shows as a `FUN_CODE_*` placeholder —
  the `0x4A26`–`0x4B40` pointer-builder family, which fifteen of the nineteen
  sites sit in and only `bank1 0x4A26` and `common 0x4A42` of which are named
  today, plus `common 0x451A` on the one site outside it. Naming them would
  rename exported functions and churn `ec/decompiled/index.csv`, so it is its
  own change and not this one's. `common 0x4A77` is the one to leave alone: it is
  the second instruction of the entry issues #617 and #652 already discuss, and
  re-opening that boundary is not this change.
* Decode the entry stream, which is the missing half of `common 0x43A5`: until
  a record's two bytes are named, the state sequence that walks the table is a
  walk over an unnamed thing.
* Give `SHAPES` a shape a stride-indexed table fits, and add the `0x4900`
  region to `ec/annotations/data-regions.yaml` with it.

## 7. The figures this page declares

`--check` re-derives every one of them from `ec/firmware/GMxMGxx_11.800` and
exits non-zero on any difference. `--emit-block` prints the block, so a figure
that moves is a command rather than an edit.

```
python3 ec/tools/stride_index_table.py ec/firmware/GMxMGxx_11.800 --check
```

```stride-index-table
records.15.leftover_bytes = 6
records.15.whole = 14
records.21.leftover_bytes = 6
records.21.whole = 10
site.0x43B1 = stride=15,base_off=0xCC,base_hi=0x49,dph_store=yes,listing=confirmed
site.0x43F6 = stride=15,base_off=0xD6,base_hi=0x49,dph_store=no,listing=confirmed
site.0x440B = stride=15,base_off=0xD8,base_hi=0x49,dph_store=yes,listing=confirmed
site.0x454F = stride=21,base_off=0x61,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4A28 = stride=21,base_off=0x50,base_hi=0x49,dph_store=yes,listing=confirmed
site.0x4A42 = stride=21,base_off=0x54,base_hi=0x49,dph_store=yes,listing=confirmed
site.0x4A5E = stride=21,base_off=0x4E,base_hi=0x49,dph_store=yes,listing=confirmed
site.0x4A77 = stride=15,base_off=0xCE,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4A84 = stride=21,base_off=0x4E,base_hi=0x49,dph_store=yes,listing=confirmed
site.0x4AA7 = stride=21,base_off=0x5A,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4AB8 = stride=21,base_off=0x50,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4AC5 = stride=21,base_off=0x4E,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4AD3 = stride=21,base_off=0x54,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4AE0 = stride=21,base_off=0x56,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4AEF = stride=21,base_off=0x52,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4B03 = stride=15,base_off=0xD0,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4B13 = stride=21,base_off=0x58,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4B2B = stride=15,base_off=0xD4,base_hi=0x49,dph_store=no,listing=confirmed
site.0x4B38 = stride=15,base_off=0xD2,base_hi=0x49,dph_store=no,listing=confirmed
sites.bank0 = 15
sites.bank1 = 0
sites.base_0x49 = 19
sites.base_0x49.with_dph_store = 6
sites.common = 28
sites.common_listed = 19
sites.pd-image = 150
sites.total = 193
sites.unknown = 0
table.bytes = 216
table.distinct_entry_bytes = 49
table.end = 0x4A25
table.entries_at_2 = 108
table.sha256 = 9ecf1319a6dcc9f3b4b044ae66f3c2726198dbb81f4b12d9eb9359d7bf8c1100
table.start = 0x494E
walk.15.steps_from_base_cc = 5
walk.15.steps_from_run_start = 14
walk.21.steps_from_base_cc = 4
walk.21.steps_from_run_start = 10
```

## 8. What landed, and what did not

`common 0x43A5`'s annotation row keeps its `type: unresolved`. Establishing
the geometry of the block does not establish what the sequence that walks it
switches between, and `unresolved` on that row is about the second thing. The
row's comment now carries the measured extent, the stride, the record framing
and the evidence path, and that is as far as this measurement moves it. The
name, the `type` cell and `ec/annotations/function-groups.csv` are untouched, so
`group_functions.py --apply` has nothing to regenerate.

The generated C is not untouched, and it is worth being exact about which
parts move. `ApplyAnnotations.java` copies the `comment` and `evidence` cells
verbatim into the plate comment of every export, so editing those cells moves
`ec/decompiled/common/43A5.c` and its one row in `ec/ghidra/c-digests.csv`.
The `.asm` does not move: the exporter writes only `scope`, `addr` and `name`
into its header, and `name` did not move either. `ec/decompiled/index.csv` and
`ec/decompiled/listing-index.csv` do carry an `evidence` cell for this row that
a full re-export would refresh, and they are left to it — the same lag they
already carry for rows other issues annotated, which is why
`build_ec_decompile.py --check` passing is not evidence that an export is
current: `verify_c_digests()` compares each committed `.c` against
`c-digests.csv` rather than against a fresh export, so a `.c` that was never
re-exported passes on its old digest.
