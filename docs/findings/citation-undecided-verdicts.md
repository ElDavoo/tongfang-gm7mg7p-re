# The 45 undecided citation pairs, one verdict each (issue #526)

`ec/tools/citation_frames.py` partitions the `(callee, comment)` pairs its
matcher sees into kept, rejected and undecided, and the undecided ones are the
population it exists to hand to a human: no code verb or data marker falls
inside the bounded window, so only reading the sentence settles them.
`docs/findings/citation-code-vs-data.md` §"What the undecided 45 are" names
three shapes and settles three of them. **This file settles all 45, one row
each**, and says which sentence the verdict rests on.

It is the companion of that write-up, not a replacement for it: the census,
the collision set and the `FILLER_BUDGET` measurement are still there, and
nothing here re-derives them.

## Two deliverables, kept apart

The issue's "done" bar mixes a change to the tool with a record a human makes.
Conflating them is the overclaim this repository's calibration rule exists to
stop, so the two are separate and each row says which it is:

1. **What the tool does.** The undecided population is now rendered in
   `report()` the way the rejected one is, and carries the frame verdicts its
   mentions drew — an undecided `Candidate` has `reasons=()`, so the line used
   to end in a bare `--`, which reads as a rendering fault rather than as
   "the window settled nothing". One lexicon word, `sjmp`, was added.
2. **What a human recorded.** The table below. **44 of the 45 rows are readings,
   not reclassifications: the tool still reports all 44 as undecided**, and it
   will keep doing so until someone widens the lexicon. A row here is a
   settlement of the *sentence*, not a change to the *census*.

## The census, before and after

| | candidate pairs | kept | rejected | undecided |
|---|---:|---:|---:|---:|
| before this change | 382 | 152 | 185 | 45 |
| after | 382 | **153** | 185 | **44** |

Exactly one pair moves, and it moves because of the lexicon: `sjmp` takes
`bank1,9B3C ← bank1,9B03` out of the undecided set and into `kept`.
`ec/annotations/call-graph-callees.csv` is **byte-identical** across the change
(`python3 ec/tools/call_graph.py --check`, rc 0), because 0x9B3C has no row in
that table at all — no form in `call_graph.py`'s `TRANSFERS` reaches it, which
is the `unranked` population `report()` already counts. **`FILLER_BUDGET` stays
at 1**; see the budget table in `citation-code-vs-data.md` for why, and
`ec/tools/test_citation_frames.py::Undecided::test_the_budget_is_one_word` for
the constant that holds it.

**The figures in this file are derived from `citations()`'s own output, not
printed by the run** — the same caveat `citation-code-vs-data.md:22-29`
carries, and for the same reason: the report prints the census totals, and a
per-pair list has to come from the lists behind them. Ten of the 45 name a
callee the ranked table carries no row for, which is the `unranked` limit
`report()` states rather than a gap in the readings.

## Re-deriving the 45

The population is the one measured *before* `sjmp` entered the lexicon, so the
re-derivation removes it again rather than expecting 44 rows back. This prints
the 45 in the order the table numbers them:

    python3 -c "
    import sys, re; sys.path.insert(0,'ec/tools')
    import citation_frames as cf, call_graph as cg
    cf.CODE_VERB = re.compile(cf.CODE_VERB.pattern.replace(' | sjmp',''), cf.CODE_VERB.flags)
    k, r, u = cg.citations(cg.load_index())
    print('kept/rejected/undecided', sum(len(v) for v in k.values()), len(r), len(u))
    for c in sorted(u, key=lambda c: (c.callee, c.citer)):
        print('  %s,%s <- %s,%s' % (c.callee + c.citer))"

**The image reads in the evidence column are re-runnable** against the
committed firmware. The five jump tables this file settles are read as
three-byte `ljmp` entries at their stated runtime address in `bank1`:

    python3 -c "
    import sys; sys.path.insert(0,'ec/tools')
    from trace_xdata_refs import offset_for_runtime
    d = open('ec/firmware/GMxMGxx_11.800','rb').read()
    for a in ('8A80', '9AD2', 'AD50', 'C90C', 'D20D'):
        o = offset_for_runtime(int('0x' + a, 16), 'bank1')
        print('0x%s  %s' % (a, ' '.join('%04X' % ((d[o+i+1] << 8) | d[o+i+2])
                                        for i in range(0, 12, 3))))"

`bank1` is file 0x10000 (`ec/tools/make_bank_image.py`), and
`trace_xdata_refs.REGIONS` is the same table `call_graph.py` and the other
tools resolve against, so no offset is written out by hand here. The one table
with a corroborating fall-through is `D20D`: the four entries end at 0xD219 and
`12 cc 2d` — an `lcall 0xCC2D` — follows, which is the citing function's own
first instruction and the same well-formedness check
`ec/tools/decode_index_table.py` applies.

## The verdict vocabulary

| verdict | meaning |
|---|---|
| `code` | the mention names a **code** address, so the pair is a citation the ranking is right to want |
| `data` | the mention names an **XDATA/IRAM byte** — a true rejection, on the sentence rather than on a pattern |
| `retracted` | the mention sits inside a reading the *same comment* withdraws, so crediting it would credit a claim its author took back |
| `code, wrong program` | the mention names a code address in a different program from the index row the pair resolved to |

`code` is a statement about the **mention**, not about the graph edge. Several
rows are a comment naming another function's *body*, an *exit* or a
*comparable listing* — the address is a code address, but the sentence is not
asserting that the citing function transfers to it, and the "rests on" column
says which of the two it is. The column that matters is never left to be
inferred.

## The table

| # | pair (callee ← citer) | the clause, as committed | evidence | verdict | what it rests on |
|--:|---|---|---|---|---|
| 1 | `bank0,9AAD ← bank0,9BFD` | "0x9AAD reaches it by falling through into it from 0x9BFB" | `bank0/9AAD.asm:9` is `9AAD 7f 08 - mov R7,#0x8`; `bank0/9BFD.asm:7` is `9BFD 02 9a 86 ljmp 0x9a86` | `code` | both are code entries. The relation the sentence asserts runs 0x9AAD → 0x9BFD, not the reverse, so this is a code mention that is **not** a call citation |
| 2 | `bank0,A426 ← bank0,A663` | "The decompiled C for this address is a merge of the bodies at 0xA426 and 0xA00E" | `bank0/A426.asm:9` is `A426 90 08 55 mov DPTR,#0x855` | `code` | the sentence is about a **body**, and the address is a listed body. No transfer from 0xA663 to 0xA426 is claimed or found |
| 3 | `bank0,C49F ← bank0,90FE` | "It ends at 0xC49F when 0x0780 == 0xA2" | `bank0/90FE.asm:57` is `9163 12 c4 9f lcall 0xc49f` | `code` | the listing calls it. Note the shape differs from the sentence: `:56` is `9160 02 c4 97 ljmp 0xc497` for the neighbouring exit, so 0xC49F is a call followed by a `ret`, not a fall-through |
| 4 | `bank0,D673 ← bank0,D091` | "This supersedes the earlier reading of the same bytes as ACALLs to 0xD673, 0xD698, 0xD6C0 and 0xD6EF" | `bank0/D091.asm:101` and `:105` linearly decode `D14B d1 73 - acall 0xd673` and `D151 d1 73 - acall 0xd673`; `python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --at 0x0D148` reports **12 well-formed entries** at 0xD14B-0xD16E | `retracted` | the listing *does* carry the `acall`, and the bytes *are* a table. The comment's own CORRECTION paragraph withdraws the reading, so crediting it would credit a claim its author took back. See the prose below for why the lexicon must not learn the word |
| 5 | `bank0,E033 ← bank0,E02D` | "the continuation at 0xE033 is what writes B and R7 out" | `bank0/E033.asm:9` is `E033 e5 f0 - mov A,B` | `code` | a continuation address, and a listed one. No transfer into it from 0xE02D — it is reached by running off the end of that listing |
| 6 | `bank0,E7B8 ← bank0,E893` | "it is byte-identical to the exits at 0xE7B8 and 0xE7C7" | `bank0/E7B8.asm:9` is `E7B8 7f 00 - mov R7,#0x0` | `code` | the sentence names two **exit stubs** and compares their bytes; 0xE7B8 is one of them |
| 7 | `bank0,E822 ← bank0,E7CA` | "the store that completes the 0x0A56-0x0A5A block and everything after it is the separately listed 0xE822" | `bank0/E7CA.asm` ends at `E820 74 10 - mov A,#0x10`; `bank0/E822.asm:7` is `E822 f0 - - movx @DPTR, A` | `code` | the address is named as the next listing, and that listing's first instruction is exactly the completing store the sentence describes |
| 8 | `bank0,EADA ← bank0,EBD5` | "Fall-through continuation of 0xEADA: calls 0x1510" | `bank0/EADA.asm:9` is `EADA 90 0a 47 mov DPTR,#0xa47` | `code` | a named function body. Same sentence, same shape as the kept `common,1510 ← bank0,EBD5` in it: 0x1510 is a call, 0xEADA is the function the sentence is *about* |
| 9 | `bank0,EADA ← bank0,ED74` | "0xEADA writes the same 0x0A59-0x0A5C block and makes the same 0x445E call" | `bank0/EADA.asm:9` is `EADA 90 0a 47 mov DPTR,#0xa47`; `bank0/ED74.asm:11` is `ED7F 90 0a 59 mov DPTR,#0xa59` followed by four `movx @DPTR,A` with `inc DPTR` between | `code` | a named function body. **The same sentence's `0x0A59`-`0x0A5C` is an XDATA write** and the listing says so at the other end of the pair — one sentence, one code address and one data range, settled the same way and differently |
| 10 | `bank1,2BD5 ← bank1,2C70` | "the ret that 0x2BD5's jumps to 0x2CB3 land on is not in this file" | `bank1/2BD5.asm:9` is `2BD5 90 0a 49 mov DPTR,#0x0a49` | `code` | a named listing, cited for the jumps *out* of it. No transfer into 0x2BD5 from 0x2C70 |
| 11 | `bank1,8ABB ← bank1,8A98` | "Those entries are `LJMP` instructions whose targets are 0x8AA7, … 0x8ABB, …" | eight 3-byte entries at `bank1:0x8A80` (file 0x10A80) read **8AA7 ABE2 ABE9 ABEA 8ABB 8AA7 8AA7 8AA7** | `code` | case 4 is `02 8a bb`. The comment's eight targets match the image exactly, including the four repeats |
| 12 | `bank1,9B3C ← bank1,9B03` | "it ends in an sjmp to 0x9B3C" | `bank1/9B03.asm:31` is `9B33 80 07 - sjmp 0x9b3c` | `code` | **the one tool reclassification.** `sjmp` was added to `CODE_VERB` for this sentence; the listing anchor is the reason it is a transfer and not a coincidence |
| 13 | `bank1,9CE8 ← bank1,9AEA` | "the eight entry targets are the decompiler's reading of them: 0xC6DB, 0x9D45, 0x9B03, 0x9CE8, …" | eight 3-byte entries at `bank1:0x9AD2` (file 0x11AD2) read **C6DB 9D45 9B03 9CE8 A841 9D53 9D4C 9D4C** | `code` | case 3 is `02 9c e8`. The comment hedges that these are "the decompiler's reading" because the table is not in its listing; the bytes confirm the hedge was warranted and the reading was right |
| 14 | `bank1,9D53 ← bank1,9AEA` | the same sentence, sixth item | the same read: case 5 is `02 9d 53` | `code` | as row 13 |
| 15 | `bank1,9FF0 ← bank1,9FCA` | "It is the shared exit for 0x9FCB and 0x9FF0, both of which branch here to return" | `bank1/9FF0.asm:12` is `9FF7 02 9f ca ljmp 0x9fca`; `bank1/9FCB.asm:9` is `9FCF 30 e4 f8 jnb 0xe4, 0x9fca` | `code` | both named sources carry the branch the sentence claims, and 0x9FCA's own listing is a single `ret` as described |
| 16 | `bank1,A24E ← bank1,A2DA` | "Four separate exits in 0xA24E land here" | `bank1/A24E.asm:9` is `A24E 90 09 7c mov DPTR,#0x97c` | `code` | a named function whose four exits the sentence counts. The address is a listed body |
| 17 | `bank1,B33B ← bank1,AD68` | "the .c's switch reads those eight targets as 0xB56C, … 0xB33B, …" | **two hops.** `bank1/AD68.asm:12` is `AD70 90 ad 50 mov DPTR,#0xad50` and `:16` is `AD76 73 - - jmp @A+DPTR`; the entry at 0xAD50 + 5×3 is `ljmp 0xAD85` (`bank1/AD50.asm:6` shows the table's own shape), and `bank1/AD85.asm:6` is `AD85 02 b3 3b ljmp 0xb33b` | `code` | the table at 0xAD50 holds ljmps to the forwarder stubs at 0xAD77-0xAD88, and those stubs are the bytes the `.c` switch read. 0xB33B is case 5, reached through `forwarder_to_b33b`. The comment is right and the eight `forwarder_to_*` rows are the same fact |
| 18 | `bank1,BBA4 ← bank1,B98D` | "branching to 0xBA43 on a borrow and to 0xBBA4 otherwise" | `bank1/B98D.asm:83` is `BA40 02 bb a4 ljmp 0xbba4` | `code` | the listing carries the jump, on the "otherwise" edge the sentence names |
| 19 | `bank1,C931 ← bank1,C924` | "Cases 0-6 land on 0xC931, 0xC979, 0xC9BE, 0xCA1D, 0xCA3E, 0xCAB8 and 0xCB08" | eight 3-byte entries at `bank1:0xC90C` (file 0x1490C) read **C931 C979 C9BE CA1D CA3E CAB8 CB08 CB1E** | `code` | case 0 is `02 c9 31`. `bank1/C924.asm:14` is the `jmp @A+DPTR` that indexes it |
| 20 | `bank1,CAB8 ← bank1,C924` | the same sentence, sixth item | the same read: case 5 is `02 ca b8` | `code` | as row 19. **Both settle against the firmware bytes, not the listing**: `bank1/C90C.asm` carries only case 0, because Ghidra's function boundary cut the table |
| 21 | `bank1,D235 ← bank1,D219` | "its case-1 target 0xD235 is one byte before the 0xD236 listing in this shard" | four 3-byte entries at `bank1:0xD20D` (file 0x1520D) read **D22E D235 D246 D23F**, and `12 cc 2d` follows them | `code` | case 1 is `02 d2 35`, and the byte after the table is the citing function's own `lcall 0xCC2D` — the fall-through that makes a four-entry table well-formed here. 0xD235 has an index row and no listing, which is the boundary the comment already flags |
| 22 | `bank1,E9CE ← bank1,EAC3` | "the linear decode degenerates into the same register-only pattern as 0xE9CE" | `bank1/E9CE.asm:7-10` is `dec R5` / `div AB` / `dec R5` / `clr 0x1b` | `code` | a **comparison to another listing**, not a transfer. The address is a code listing, and the sentence's claim is that the two look the same |
| 23 | `common,07F0 ← common,012F` | "waits on a 0x07F0 poll until it returns 5" | `common/012F.asm:27` is `0157 12 07 f0 lcall 0x07f0`, and `:28` is `015A b4 05 ee cjne A,#0x5,0x014b` | `code` | the listing is the poll the sentence describes: call, compare against 5, branch back |
| 24 | `common,086B ← bank0,9D9B` | "stores the smaller of the running result and the 0x0869 cap into 0x086B. It then clamps 0x086B three times … 0x086B, 0x086C and 0x086E are the three results" | `bank0/9D9B.asm:58-59` is `9DFF 90 08 6b mov DPTR,#0x86b` / `9E02 f0 - - movx @DPTR,A`; twelve such pairs run to `:121` | `data` | all three mentions are the XDATA **result byte** the block computes. 0x086B is also a code address, which is what put the pair in the frame gate at all |
| 25 | `common,086B ← bank0,D28E` | "0x086A to 0x1C39 and 0x086B to 0x1C3A" | `bank0/D28E.asm:27-30` is `D2B6 90 08 6b mov DPTR,#0x86b` / `movx A,@DPTR` / `mov DPTR,#0x1c3a` / `movx @DPTR,A` | `data` | the six-byte copy's sixth element. Source and destination are both XDATA |
| 26 | `common,08E0 ← bank0,821F` | "post-increments the selector at 0x08E0 with 0x0822C-0x0822D" | `bank0/821F.asm:11-14` is `8228 90 08 e0 mov DPTR,#0x8e0` / `movx A,@DPTR` / `inc A` / `movx @DPTR,A` | `data` | the selector is an XDATA counter; the 0x0822C-0x0822D beside it is a Keil bit-address, not a code target either |
| 27 | `common,0F75 ← common,0070` | "calls 0x110A -- the tail half of bl51_bank_select_0 … -- followed by 0x158E, 0x0F75 and 0x1594" | `common/0070.asm:13` is `007F 12 0f 75 lcall 0x0f75` | `code` | the listing carries the call. The window cannot see it because the **aside between the governing verb and the mention is longer than `FILLER_BUDGET`** — the reason this pair is the worked example in `citation-code-vs-data.md` |
| 28 | `common,1504 ← bank0,D5D4` | "0x1500-0x1504 and 0x1510-0x1514 include no entry for these addresses in ec/annotations/registers.yaml" | `bank0/D5D4.asm:7` is `D5D4 90 15 01 mov DPTR,#0x1501` | `data` | a caveat about an **XDATA range in the register map**, and the function's own `DPTR` load sits inside that range |
| 29 | `common,1510 ← bank0,D5D4` | the same caveat, the second range | the same load | `data` | as row 28. **The same callee keeps a real citation** — `common,1510 ← bank0,EBD5` is kept, on "calls 0x1510" — which is the collision table's `common,1510` row in miniature |
| 30 | `common,158E ← common,0070` | the same list as row 27 | `common/0070.asm:12` is `007C 12 15 8e lcall 0x158e` | `code` | as row 27 |
| 31 | `common,1594 ← common,0070` | the same list as row 27 | `common/0070.asm:14` is `0082 12 15 94 lcall 0x1594` | `code` | as row 27 |
| 32 | `common,1C00 ← bank1,E4F9` | "On the fall-through path from 0xE4E9 that means 0xFF to 0x1C00 followed by 4 to 0x0680" | `bank1/E4E9.asm:7` is `E4E9 90 1c 00 mov DPTR,#0x1c00`, `:13` is `E4F6 90 1c 00 mov DPTR,#0x1c00`, and `bank1/E4F9.asm:7` is `E4F9 f0 - - movx @DPTR, A` | `data` | a `movx @DPTR,A` is an **XDATA store**, whatever the value in A. This is the one unsettled member of 0x1C00's 20/19/1, and the listing settles it as data |
| 33 | `common,1E1A ← bank0,AA90` | "then 0x1E1A twice with R7 = 0x5F and R5 = 0 then 1" | `bank0/AA90.asm:16` is `AAA3 12 1e 1a lcall 0x1e1a` and `:19` is `AAAA 12 1e 1a lcall 0x1e1a` | `code` | twice, as the sentence says, with the two R5 values the listing carries at `:14` and `:17` |
| 34 | `common,4B0F ← bank0,445E` | "it repeats the fetch with DPTR incremented once and passes the result through 0x4B0F and 0x4A69" | `bank0/445E.asm:104` is `4510 12 4b 0f lcall 0x4b0f`, immediately before `4513 12 4a 69 lcall 0x4a69` | `code` | both calls of the pair are in the listing, in the order the sentence gives them |
| 35 | `common,4F3E ← bank0,53AF` | "and any other 0x009D takes 0x4F3E" | `bank0/53AF.asm:74` is `5416 12 4f 3e lcall 0x4f3e` | `code` | the third arm of the dispatch, and the listing carries it |
| 36 | `common,4FED ← bank0,53AF` | "0x009D equal to 0xBF alone takes 0x4FED" | `bank0/53AF.asm:59` is `5400 12 4f ed lcall 0x4fed` | `code` | the second arm |
| 37 | `common,50DE ← bank0,53AF` | "0x009D equal to 0xBF together with 0x009E equal to 0x01 takes 0x50DE" | `bank0/53AF.asm:44` is `53EA 12 50 de lcall 0x50de` | `code` | the first arm. All three arms are 8 NOPs past a `lcall 0x1636`, which is the shape the sentence describes |
| 38 | `pd,06EA ← bank0,CEA2` | "none of 0x06E7, 0x06E8/0x06E9 or 0x06EA/0x06EB has an entry in ec/annotations/registers.yaml" | `bank0/CE9E.asm:7` is `CE9E 90 06 e7 mov DPTR,#0x6e7`; `bank0/CA53.asm:13` is `CA5B 90 06 ea mov DPTR,#0x6ea` | `data` | a caveat naming an **XDATA index and its halves**, in an EC-bank comment. The pair resolved to the `pd` row only because the collision handed `bank0` a `pd` row at 0x06EA — see the wrong-program note in row 45 |
| 39 | `pd,06EA ← bank0,CEE9` | the same caveat | `bank0/CEE9.asm:7` is `CEE9 90 06 e7 mov DPTR,#0x6e7` | `data` | as row 38 |
| 40 | `pd,06EA ← pd,D83D` | "calls 0x05A6 with R0 = 0x3F, R1 = 0x4C, R2 = 0xCC, R3 = 0xCD, and 0x06EA" | `pd/D83D.asm:38` is `D86B 12 06 ea lcall 0x06ea` | `code` | **the opposite verdict on the same callee, and the clearest case in the table.** The sentence reads 0x06EA as the last item of an argument list, but the listing has a separate `lcall 0x06EA` at 0xD86B, one instruction after the `lcall 0x05A6` the list belongs to. It is a call, and a `pd` comment calling a `pd` row is in-program |
| 41 | `pd,39E6 ← pd,39E7` | "it is also the fall-through target of 0x39E6, which adds R5 = A" | `pd/39E6.asm:7` is `39E6 fd - - mov R5, A`; `pd/39E7.asm:7` is the next entry | `code` | a one-byte fall-through, and the address is the entry it falls through from |
| 42 | `pd,A0E6 ← pd,7580` | "the shared block at 0x763D then calls 0xD83D …, 0xAD83, 0xA0E6, 0xACE1, …" | `pd/7580.asm:18` is `7599 12 a0 e6 lcall 0xa0e6` and `:108` is `7652 12 a0 e6 lcall 0xa0e6` | `code` | a call list, and the listing carries the item twice |
| 43 | `pd,CBB0 ← pd,EF79` | "Structurally identical to 0xEF59, with 0x716C in place of 0x715E and 0xCBB0 in place of 0xED90" | `pd/EF79.asm:19` is `EF8E 12 cb b0 lcall 0xcbb0`; `pd/EF59.asm:19` is `EF6E 12 ed 90 lcall 0xed90` | `code` | the analogy is exact, down to the line: both listings carry their `lcall` at line 19, in the position after the gated `0x6FAF` call. The mention is a **call site**, not a bare structural comparison |
| 44 | `pd,E6C0 ← pd,7580` | the same call list as row 42 | `pd/7580.asm:106` is `764C 12 e6 c0 lcall 0xe6c0` and `:205` is `7719 12 e6 c0 lcall 0xe6c0` | `code` | a call list, twice in the listing |
| 45 | `pd,E930 ← bank1,E924` | "it ends at 0xE930 and falls through into 0xE931, which is a bare ret" | `bank1/E924.asm:16` is `E930 f9 - - mov R1, A`, the listing's last instruction; the next byte in the image is `22`; `index.csv` carries `bank1,E931` as `shared_return_point` | `code, wrong program` | the mention names a **`bank1` CODE address** — a fall-through, not a call. `index.csv` has **no `bank1` row at 0xE930**, so `Index.resolve` handed the pair the `pd` row at the same address, which is a different program with different bytes there (`pd/E930.asm:7` is `E930 ad 07 - mov R5,0x07`). The reading is *code*; the pair as the resolver formed it is an artifact, and crediting it would put a bank1 fall-through on a PD-image function row |

**Tally: 36 `code`, 8 `data`, 1 `retracted`.** Of the 36, one (row 12) is the
tool reclassification and 35 are recorded readings. Ten of the 45 name a callee
the ranked table carries no row for — rows 1, 8, 9, 10, 11, 12, 13, 14, 20
and 32 — so 27 of the 36 `code` verdicts would enter `cited_by`, 9 of them name
a callee with no row to enter, and the tenth unranked pair is row 32's `data`.

## The lexicon word, and the one it must not learn

`sjmp` is in `CODE_VERB` because of exactly one committed sentence, row 12, and
`ec/tools/test_citation_frames.py::CodeFrames::test_a_short_jump_is_a_code_frame`
carries that sentence with `bank1/9B03.asm:31` as its anchor. It sits with
`lcall`/`ljmp`/`ajmp`/`acall` because a comment can name the listing mnemonic
the way it names `lcall` — "it ends in an sjmp to 0x9B3C" is a claim about
where control goes — and because the three other tools that read these bytes
already list it in their branch families: `audit_call_targets.py`'s
`REL_FAMILIES`, `grade_name_basis.py`'s `BRANCHES` and `disasm8051.py`'s
`REL_OPCODES`. The comment lexicon was the odd one out.

**It is not a wider-reaching form than its neighbours, and nothing here depends
on it being one.** `sjmp` is `80 rel` with a signed 8-bit offset, -128..+127
from the following instruction, so 0x9B3C is 7 bytes past 0x9B35 and the
committed listing's `80 07` is the whole encoding. What the conditional
branches beside it in those three tables lack is **unconditionality**; that,
and the fact that no committed comment claims one as a transfer to an address,
is the only distinction this list is drawing. `acall` is the genuinely
different case — an 11-bit paged target, which is why the module docstring
treats the paged forms as a parser trap of their own.

**`acalls` is the word row 4 must not get.** The 0xD673 pair is undecided
only because the sentence writes "ACALLs" and `CODE_VERB` has `acall` without
the plural. Adding it would credit a reading the same comment retracts, and
the retraction is not a stylistic choice: `ec/tools/decode_index_table.py` reads
those bytes as **12 well-formed table entries**, so the `acall`s are a linear
decode of data. This is the clearest case in the table of why a lexicon word
needs its own evidence sentence, and of what happens when it gets one it has
not earned.

## What this does not establish

- **44 of these are readings, not classifications.** `call_graph.py` still
  reports 44 undecided pairs and still credits 153; nothing here changes a
  count beyond row 12. A settlement of the sentence is not a reclassification,
  and this file does not claim the tool agrees with it.
- **The 36 `code` verdicts are not 36 new edges.** A `code` verdict says the
  mention names a code address. For the 15 rows where the citing listing
  carries a transfer, that is a call the graph could have counted and did not,
  because the window never reached the verb. For the 13 rows naming another
  function's body, an exit or a comparable listing, **no transfer is claimed in
  either direction** — crediting them would put a function on a citing list it
  does not belong on, which is a defect the other way.
- **The dispatch-table rows settle against committed firmware bytes**, read
  with `trace_xdata_refs.offset_for_runtime` and reproducible from the
  re-derivation above. That is a static read of an image. Nothing here was
  executed, no register was read back, and no EC behaviour was observed.
- **One pair in forty-five is a resolver artifact** (row 45), and one is a
  claim its own author withdrew (row 4). Neither is a frame-test question, and
  a wider window would settle neither: the first needs program identity to be
  decided for a `bank0`/`bank1` citation, which `program_reason` deliberately
  refuses to decide; the second needs a human to have read the correction.
- **No register `status:` changed and no listing was re-read.**
  `ec/annotations/registers.yaml`, `ec/ghidra/xdata-symbols.csv` and
  `ec/annotations/ghidra-functions.csv` are untouched, and
  `call-graph-callees.csv` is byte-identical across the change.
