# The citing listing is the other half of the citation question (issue #525)

`ec/tools/citation_frames.py` decides whether a comment's `0x` + 4-hex-digit
mention reads as a *call* or as a *data byte*. It is right about the seven
`bank1` comments that end "is not supported by these instructions, and that code
is not present at this address": every mention in every one of them really does
read as a call, to a code address, in a call enumeration. What the frame test
cannot see is what the comment is **attached to**. Those seven are attached to
`0xFF` fill, not to the reset path those calls live in, so the ranking's top
three rested entirely on comments that name callees their own instructions
cannot reach.

`ec/tools/citation_callers.py` asks the citing row's own `.asm` that second
question, and `citations()` consults the answer at the precedence point below.
This file carries the two rules, the measured blast radius of each, the 12
corroborated pairs read one by one, the corrected partition, and the limits.
`docs/findings/citation-code-vs-data.md` is the write-up for the frame half;
`docs/findings.md` §24 and `ec/annotations/call-graph.md` carry the summary.

Every figure below is reproduced by `python3 ec/tools/call_graph.py` and, for
the ones the report does not print, by the four commands in
[§Re-deriving](#re-deriving). **Nothing here is a behavioural claim.** No
register `status:` changed, no listing was re-read, and no live test ran: this is
a text measurement over committed inputs.

## Why the listing, and not `type`, the name, or the prose

The issue named three candidate discriminators and this takes the listings. The
other two were measured on the committed tree and rejected:

- **`type` is not a discriminator.** All twenty-nine annotated fill rows are
  `type=unresolved`, and so are ordinary citing rows that cite genuinely
  (`common,018C`, `common,029B`; `bank0,B5D2`, `bank0,B82E`). Keying on `type`
  would reject real citations.
- **The name prefix is a convention, not evidence.** A future agent renaming a
  row breaks the rule silently, in the quiet direction the tool exists to
  prevent.
- **A prose-denial pattern is a second bag of words.**
  `citation_frames.py`'s own header says the frame test "is a bag of words, and
  it is a guard on a number, not a parser". A rule keyed on "is not supported by
  these instructions" would be another one, and it would have to be re-measured
  for wrong rejections the way `FILLER_BUDGET` was.

The listing is decidable, is the frame `call_graph.py` already trusts over the
`.c`, and makes the gate a fact about code rather than a reading of prose.

## The two rules, and their precedence

Both ask the *citing* row's own listing a question, and `scan()` already walks
every listing and resolves every target, so the facts are collected once there
rather than in a second pass.

1. **The veto — a fill listing cannot make a call.** A citing row whose
   listing's instruction bytes are an unbroken `0xFF` run (`mov R7, A` repeated,
   no transfer, no branch, no `ret`) produces no `rejected`→*dropped*: its pairs
   go to `rejected` with the reason `fill-at-citer`, in the existing `reasons`
   tuple, so `reason_counts()` and `rejected_rows()` render it with no change to
   either. The test is on the bytes because the 8051 map fixes them: `0xFF` is
   `MOV R7, A` and nothing else, so "every instruction's first byte is `ff`"
   already rules out the transfer, branch and `ret` opcodes without this module
   carrying a second opcode table to keep in step.
2. **The credit — a transfer corroborates a mention the window left open.** If a
   pair's frame verdicts are `undecided` and the citing listing carries a
   transfer whose target resolves, through the same `Index.resolve` the inbound
   scan uses, to that same callee key, the pair is kept and counted in a reported
   "settled by the listing" line.

**Precedence, highest first:** program-identity veto → data frame →
`fill-at-citer` → kept by a code frame **or** by listing corroboration →
`undecided`.

Corroboration upgrades `undecided` only, and that is structural rather than
promised: reaching that arm means no mention read as `code` and none as `data`,
so every mention is `undecided`. It never overrides a data frame — the rule the
`common,07D0` correction depends on — and never overrides the program-identity
veto, which is why the fixture's `pd,10E0` stays refused although its own
listing carries the `lcall`.

**A citing row with no listing at all is neither.** No `.asm` found means no
veto and no corroboration, and the pair falls back to the frame alone. That is
the calibration rule applied in both directions: *not found by this method* is
never *absent*. A listing that parses to no instruction line is likewise not
fill — unknown rather than evidence. No committed listing is in that state: all
2707 parse to at least one instruction line (§Re-deriving), so the case is the
defensive path rather than a measured population, and the guard is that
`is_fill` answers `False` for a listing it read nothing from, which is not the
answer it gives one it read and ruled out.

## The veto's blast radius: 30 listings, 29 annotated, 1 pair

**30** listings in `ec/decompiled` are an all-`0xFF` run. **29** of them carry
an annotation row: the seven `unimplemented_ff_fill_*` in `bank1`, the five
`ff_filler_not_a_function_*` in `bank0`, and — since issue #561 — seventeen more
`ff_filler_not_a_function_*` in `common`, the unprogrammed `0x728F`-`0x7FFF` band
`docs/findings/ff-fill-census.md` censuses. The five `bank0` rows name no
anonymous callee at all, so the rule changes nothing for them, and the
seventeen `common` rows name exactly one between them (below).

That leaves **exactly 1 pair**, and it is `common,375E` ← `common,7DF2`. It is a
consequence of #561's new rows rather than of the rule changing: the
`common,7DF2` comment names the `mov R3, #0x2` at `0x375E` that its own
call-target byte match sits inside, which is the evidence for "not an entry
point", and `0x375E` is an unannotated anonymous export. The comment does not
claim a call there, and the veto rejects the pair anyway — the citing listing is
fill — so no credit moves. It is here because the guard's audit trail is the
record of what it saw, and a rejection that is silently dropped could not be
told apart from one that never happened.

**The twenty-one pairs the issue named are not in this count, and their absence
is not the rule working.** Those were the seven `bank1` rows × `common,0F75`,
`common,158E` and `common,1594`, and this branch's own tree measured 21 → 22
with them in. Issue #558 then annotated all three `common` callees, and
`citations()` only ever considers a `FUN_`-prefixed index row — so the twenty-one
left the candidate set because their callees stopped being anonymous, not
because the veto got better. Three rows is all it took. Nothing else on this
tree moves, and the rejection is reported rather than dropped — it appears in the
existing `rejected on fill-at-citer` tally.

The result the issue wanted: `common,0F75`, `common,158E` and `common,1594` each
read **`cited_by=1` / `inbound=1` / `named_callers=1`**, with `citing` reduced to
`common:0070`, and the seven `bank1:F5xx` addresses are gone from every `citing`
column in the table. That is the same `cited_by == inbound` agreement
`--self-test` pins for `common,07D0` — two independent framings landing on the
same number, which is what makes it a check rather than a coincidence.

**The seven comments are not rewritten.** Substituting a name for an address
there would assert the very call the comment denies, and the gate now makes
their text irrelevant to the count, so their own text is left alone. The file is
no longer untouched in the literal sense: its **1,872** rows are the 1,851 this
section was written against, plus issue #558's four and the seventeen `common`
fill rows issue #561 added. Neither set touches these seven.

*(**Correction, 2026-09-25, issue #558.** The 1,851 is what the CSV held when
this was written, and the "untouched" is this issue's, not the tree's. #558 has
since added four rows, so the CSV is 1,855 — and it annotated `common,0F75`,
`0x158E` and `0x1594`, three of the four addresses the 21 pairs above name.
`cited_by` counts anonymous callees only, so annotating them takes all 21 out
of the table instead of moving their counts, which is why the ranking they used
to top is a different set of addresses now. `../findings.md` §27 is the reading.
Every figure in this file is this issue's, measured then, and is left as
measured rather than silently re-run — the numbers are the record of what #525
did, not a census of the tree today.)*

*(**Second correction, 2026-09-25, issue #561.** The 1,855 is the same kind of
snapshot: #561's seventeen `common` fill rows took the CSV to 1,872, and the
blast-radius and partition figures above are re-derived on the merged tree, which
carries both sets of rows. That re-derivation is why they no longer agree with
this file's original 21-pair reading — see
[§The veto's blast radius](#the-vetos-blast-radius-30-listings-29-annotated-1-pair)
for which of the two causes each figure moved for.)*

### Why the narrow fill test and not "this listing has no transfer at all"

Measured on the merged tree: **998** commented annotation rows sit on a listing
with zero transfer instructions, and **100** of them are a citer on some
candidate pair. One of those 100 is the fill listing above, `common,7DF2`.
**The other 99 are not fill**, and many of them are real calls
the listing does not carry because Ghidra's function boundary cut the call into
a neighbouring export — `bank1,E57E` is the clearest: its own comment reads "the
listing for this address is a single instruction, `PUSH direct 0x07`, which saves
bank-0 R7 … `ec/annotations/bank-call-targets.csv` records an `lcall` to 0xE5D6 at
0xE580 … and the matching `POP`".

The citer count falls from 108 to 100 for the same reason the twenty-one pairs
did: the seven `bank1` fill rows were citers only through `common,0F75`,
`common,158E` and `common,1594`, and #558 named all three.

So the broad form would reject **99 real pairs** to save 1 fake one. The
`0xFF`-run form cannot: it fires only where the bytes positively show a listing
with no code. **That asymmetry is the whole reason for the narrow form**, and it
is why no narrower-or-broader variant was tried — the numbers above are the
argument, not a preference.

## The credit's blast radius: 12 pairs, read one by one

**12** pairs are kept on a listing transfer rather than on a frame, and all 12
are below. This branch's own tree held 16, and the four that left are the ones
whose callee issue #558 named: `common,0F75`, `common,158E` and `common,1594`
(the `common,0070` reset-path list) and `common,07F0` (the `common,012F` poll).
Each is listed
with the citing listing, the transfer line that settles it, and a verdict from
reading the sentence. `common,1E1A` is one of the pairs
`citation-code-vs-data.md` names among those a `FILLER_BUDGET` of 2 would have
rejected *wrongly*; `common,07F0` was the other, and it left the set by being
annotated rather than by being reclassified.

| callee | cited by | listing line | verdict |
|---|---|---|---|
| `common,1E1A` | `bank0,AA90` | `AA90.asm:16` `lcall 0x1e1a` | real. "0x1E1A twice with R7 = 0x5F and R5 = 0 then 1" |
| `common,4B0F` | `bank0,445E` | `445E.asm:104` `lcall 0x4b0f` | real. "passes the result through 0x4B0F and 0x4A69"; the listing's closing `sjmp` is *after* this site, so the comment's "the listing stops at an sjmp to 0x4534" is not in tension with it |
| `common,4F3E` | `bank0,53AF` | `53AF.asm:74` `lcall 0x4f3e` | real. One of three compare-chain arms, each `lcall` then `sjmp` to the common tail |
| `common,4FED` | `bank0,53AF` | `53AF.asm:59` `lcall 0x4fed` | real, same three arms |
| `common,50DE` | `bank0,53AF` | `53AF.asm:44` `lcall 0x50de` | real, same three arms |
| `bank0,C49F` | `bank0,90FE` | `90FE.asm:57` `lcall 0xc49f` | real. "It ends at 0xC49F when 0x0780 == 0xA2" — the comment says *ends at* (a tail-jump) where the listing decodes `lcall`; both reach the function, and the form is not what the citation claims |
| `bank1,BBA4` | `bank1,B98D` | `B98D.asm:83` `ljmp 0xbba4` | real. "branching … to 0xBBA4 otherwise"; the listing does stop at 0xBA40, and that last line is the branch it names |
| `bank0,D673` | `bank0,D091` | `D091.asm:101` `acall 0xd673` | **wrong.** See the limits below |
| `pd,A0E6` | `pd,7580` | `7580.asm:18` `lcall 0xa0e6` | real, in a "then calls" enumeration |
| `pd,E6C0` | `pd,7580` | `7580.asm:106` `lcall 0xe6c0` | real, same enumeration |
| `pd,06EA` | `pd,D83D` | `D83D.asm:38` `lcall 0x06ea` | real, in a call list with register arguments |
| `pd,CBB0` | `pd,EF79` | `EF79.asm:19` `lcall 0xcbb0` | real. "with 0x716C in place of 0x715E and 0xCBB0 in place of 0xED90" — the substituted call target in a structurally identical twin |

**Eleven of the twelve are right; one is not, and it is not narrowed away.**
`bank0,D091`'s own comment carries `CORRECTION 2026-09-24, issue #180`: the 40
bytes from 0xD14B are a CODE table, not code, and "this supersedes the earlier
reading of the same bytes as ACALLs to 0xD673, 0xD698, 0xD6C0 and 0xD6EF
interleaved with INC and DEC". `D091.asm:101` is at address 0xD14B — the first
byte of that table — and the `acall 0xd673` there is the data read as an
instruction. The corroboration rule cannot see the difference: a listing is a
*linear* disassembly, and a data island inside a function's range decodes
exactly as convincingly as code. Of the other three superseded targets, two
(`bank0,D6C0`, `bank0,D6EF`) are already named and `bank0,D698` has no index
row, so this one pair is the whole of the damage.

The fix for that is **not** a carve-out by address, and it is not a narrower
mechanical condition either: the obvious candidates (require a 3-byte `lcall`/
`ljmp`, or skip any site in a region some annotation calls a table) were each
fitted to this one known wrong answer, and the first would drop the `ajmp` and
`acall` corroborations the tool exists to keep — 0x5A43 is reached by 11 `ajmp`
and zero `lcall` in the real census. **So the rule stays as it is and the
miscount is reported**: 1 wrong credit in 12, against 11 right ones. On this
branch's own tree the same trade read 1 in 16 against 15 right ones and against
the alternative of leaving three real `common,0070` calls uncounted; #558 named
those three, so they are credited by name now and the trade is the narrower one.
A wrong
credit costs a naming agent one unnecessary read of `bank0,D673` — a real
76-byte function that is worth reading anyway — and does not reach the top of
the ranking. That trade is recorded here rather than tuned away, and
re-measuring it is a one-line check (§Re-deriving).

## The corrected partition

| | before | after |
|---|---:|---:|
| candidate (callee, comment) pairs | 382 | 352 |
| kept | 153 | **140** |
| — of those, settled by the citing listing's transfer | — | **12** |
| rejected | 185 | **186** |
| — of those, on `fill-at-citer` | — | **1** |
| undecided | 44 | **26** |
| anonymous callees a comment names | 99 | **105** |
| comments that name one | 142 | **131** |

140 + 186 + 26 = 352, so the three buckets still partition the candidates and
no comment is both credited and reported against — the assertion `--self-test`
makes. **The `before` column is 153 / 185 / 44 rather than the 152 / 185 / 45
this rule was written against**, because issue #526 landed `sjmp` in
`CODE_VERB` and took one pair out of `undecided` first. Both rules are in the
merged tree, so the tree moved 152 → 153 (one `sjmp` credit) → 140 (+12
corroborated); the single remaining `fill-at-citer` rejection is #561's
`common,7DF2` naming the instruction its own byte match sits inside, named in
the blast-radius section above.

**Where the candidate count's move came from, measured rather than guessed.**
This is a separate measurement from the table above — every row is a *real* tree
with **both** rules already in, each read with one side's change held out, so the
`382` in the first row is this section's base tree and not the `before` column
above:

| tree | candidates | kept | settled by listing | rejected | `fill-at-citer` | undecided |
|---|---:|---:|---:|---:|---:|---:|
| this section's base tree, neither change | 382 | 148 | 16 | 206 | 21 | 28 |
| #561 alone | 383 | 148 | 16 | 207 | 22 | 28 |
| #558 alone | 351 | 140 | 12 | 185 | 0 | 26 |
| **the merged tree** | **352** | **140** | **12** | **186** | **1** | **26** |

**All 31 pairs the re-export removed are accounted for, and they are all the same
cause.** #570's re-export renamed seven `FUN_CODE_*` index rows, and
`citations()` only ever considers a `FUN_`-prefixed target, so those pairs left
candidacy because their callee stopped being anonymous: `common,0F75`,
`common,158E` and `common,1594` 8 each, `common,07F0` 3, `bank1,9CE8` 3,
`bank1,9D53` 1, `bank1,E2D3` 0 — 31, with **zero** lost pairs pointing at
anything else. That single rename is also what took the issue's 21 fill
rejections to 0; the rule did not improve. #561's side moves one pair the other
way (`common,375E` ← `common,7DF2`), which the veto still rejects.

**This branch's own version of the table above put 382 in the candidate row
against 148 / 207 / 28, and those sum to 383. The 383 is the measured value; the
382 was a slip.** The row figures themselves were right, and #561 moved no other
column. Corrected in place rather than carried forward.

Both moves widen the work list rather than narrowing it. Six more callees are
cited now (99 → 105) and eleven fewer comments (142 → 131), because a single fill
comment used to carry three of a callee's citations and each real one now counts
once; the ranking is a work list of *addresses* to name, and the addresses went
up, not down.

**The new rank 1 is `common,07F0` at `cited_by=3` / `inbound=3` /
`named_callers=3`, and it does not rest on a weak frame marker.** Two of its
three comments read "polls 0x07F0 until it returns 5" — a strong code verb — and
`common/018C.asm:27`, `common/029B.asm:27` and `common/012F.asm:27` each carry
`lcall 0x07f0`. Three comments, three transfer sites, and the one that needed the
listing (`common,012F`, "waits on a 0x07F0 poll") is the arm the other two
describe. This was **not** predicted and no gate was tuned to produce it; it is
where the extra credits landed. **It is history in the merged tree**: #558
annotated `common,07F0` and re-exported it, so it is no longer an anonymous
callee and no longer ranks here at all. What the reading established — that a
callee cited three times by three comments that each name a transfer is a real
dependency, not a frame artefact — carries over to whatever ranks first now, and
`../findings.md` §27 is the reading of the four addresses this change named.

## What the rule still cannot decide

- **A data island inside a function reads as code.** The `bank0,D091` case
  above. Corroboration can only see that the listing carries a transfer to the
  address; it cannot see whether those bytes are instructions. The same blind
  spot is why the module's rule is a corroboration and never a *proof*: the
  comment still has to be read, and 1 in 12 needed it.
- **A call the listing does not carry is invisible here.** 998 commented rows sit
  on a transfer-free listing, 100 of them citing something. `bank1,E57E`'s
  `lcall 0xE5D6` at 0xE580 is in a neighbouring export. A pair like that is
  still decided by the frame alone, and the `undecided` population is where it
  lands.

  **That population now has a committed measurement**, so the bullet above is no
  longer a dead end even though every word of it still holds *of
  `citation_callers.py`* — the call is still invisible to that tool and the
  frame still decides it alone. `../findings.md` §35 calls this page the one
  that "measured and could not classify"; the measurement is
  [`citation-gap-scan.md`](citation-gap-scan.md), writing
  `ec/ghidra/gap-citation-scan.csv`: **99 citing rows / 124 `(callee, citer)`
  pairs, split 2 `boundary-cut` / 121 `no-transfer` / 1 `not-code`**. One of the
  two `boundary-cut` pairs is this exact example — callee `bank1,E5D6`, citer
  `bank1,E57E` — so the address this page names by name is one of the two the
  other page resolved. What moved is what is *known* about what
  `citation_callers.py` cannot see, not what the tool can see.
- **A listing that parses to nothing is not fill.** It would be unknown to this
  rule, not evidence of anything, and a citing row on one would get no veto and
  no credit. No committed listing is in that state, so the branch is here as a
  guard; the near miss is the opposite shape, and it is a real population — the
  **83** listings made up only of operand-less instructions (`ret`, `nop`,
  `reti`) *are* read, and ruled out on their first byte. See
  `ec/tools/test_citation_callers.py`.
- **`fill-at-citer` is a mechanical test on one byte column.** A listing that
  begins in a fill region but contains real code is not fill, because its
  non-`ff` bytes say so — and the five `bank0` `ff_filler_not_a_function_*` rows
  show the tool already draws that distinction upstream of this gate. The
  seventeen `common` rows of #561 draw it in the other direction: they are
  annotated *as* fill, and the veto fires on the one of them that names an
  address, so a row added to say "this is not a function" is subject to the same
  rule as a row added to say what a function does.
- **Neither rule touches a register, a hardware register, or the `.c` files.**
  `ec/annotations/registers.yaml` and `ec/ghidra/xdata-symbols.csv` are
  untouched: no register `status:` changed, no listing was re-read, and nothing
  here was observed on hardware. The `fill-at-citer` name is a *reason string in
  a report*, not a claim about what the EC does.

## Re-deriving

Four commands, run from the repository root. The first and second come from the
`call_graph.py` report; the third re-counts the case against the broad form,
and the fourth is the listing census behind the two defensive cases — that no
committed listing parses to nothing, and what the near miss looks like instead.

```sh
python3 -c "import sys,csv; sys.path.insert(0,'ec/tools'); import call_graph as cg; i=cg.load_index(); e,u,o,t,l=cg.scan(i); a={(r['scope'],cg.norm_addr(r['addr'])) for r in csv.DictReader(open(cg.ANNOTATIONS))}; print('fill listings', sum(1 for v in l.values() if v.fill), 'of which annotated', sum(1 for k,v in l.items() if v.fill and k in a))"
```

```
fill listings 30 of which annotated 29
```

```sh
python3 -c "import sys; sys.path.insert(0,'ec/tools'); import call_graph as cg; i=cg.load_index(); e,u,o,t,l=cg.scan(i); k,r,d,x=cg.citations(i,l); print('fill rejections', sum(1 for c in r if 'fill-at-citer' in c.reasons), '| kept on a listing', len(x), '| partition', sum(len(v) for v in k.values()), len(r), len(d))"
```

```
fill rejections 1 | kept on a listing 12 | partition 140 186 26
```

```sh
python3 -c "import sys,csv; sys.path.insert(0,'ec/tools'); import call_graph as cg; i=cg.load_index(); e,u,o,t,l=cg.scan(i); k,r,d,x=cg.citations(i,l); a=[(q['scope'],cg.norm_addr(q['addr'])) for q in csv.DictReader(open(cg.ANNOTATIONS)) if q.get('comment')]; nf={q for q in a if not list(cg.parse_listing(cg.DECOMPILED+'/'+q[0]+'/'+q[1]+'.asm'))}; p={(key,c[:2]) for key,v in k.items() for c in v}|{(c.callee,c.citer) for c in r+d}; citers={c for _callee,c in p}; print('commented rows', len(a), '| transfer-free listings', len(nf), '| of those citing', sum(1 for q in nf if q in citers), '| of those not fill', sum(1 for q in nf if q in citers and not (q in l and l[q].fill)))"
```

```
commented rows 1872 | transfer-free listings 998 | of those citing 100 | of those not fill 99
```

The trailing **99** is the same **99** `citation-gap-scan.md` measures, in a
different unit — the two are not two disagreeing figures. This census counts
**citing rows**, one per comment, so a comment naming three callees is one row
here. The gap scan takes those same 99 rows and expands each into one pair per
named callee, which is where its **124** comes from: the two row sets are equal,
not merely the same size, and of the 99 rows 83 carry a single pair while the
other 16 carry 2 to 5 — the 25 extra pairs. The 2 / 121 / 1 split is over those
124 pairs, so it is a verdict per pair and never per row, and a reader comparing
the two pages should read "99" and "99 rows / 124 pairs" as the same rows
counted before and after the expansion.

```sh
python3 -c "import sys,glob; sys.path.insert(0,'ec/tools'); import citation_callers as cc; p=sorted(glob.glob('ec/decompiled/*/*.asm')); i=lambda x: list(cc.iter_instructions(x)); nt=[x for x in p if not list(cc.transfers(x))]; print('listings', len(p), '| no instruction line', sum(1 for x in p if not i(x)), '| no transfer', len(nt), '| of those not fill', sum(1 for x in nt if not cc.is_fill(x)), '| operand-less only', sum(1 for x in p if i(x) and all(len(y)<6 for y in i(x))))"
```

```
listings 2707 | no instruction line 0 | no transfer 1283 | of those not fill 1253 | operand-less only 83
```

The first column of that line is the whole of the no-evidence-gathered case:
**zero** listings parse to nothing, so the "a listing that yields no instruction
line is not fill" rule guards a path this tree does not reach. The last column
is the near miss, and it is the opposite case — 83 listings whose instruction
lines are all five tokens (`ret`, `nop`, `reti`, no operand), which
`iter_instructions` reads and `is_fill` rules out on the first byte, 78 `22`, 26
`00` and 3 `32` across their lines.

**The tests that hold the rule in place.** `python3 ec/tools/call_graph.py
--self-test` pins all three shapes on a fixture whose fill listing is at
`bank1,F6A0` — deliberately not one of the seven real addresses, so the
assertion is about the shape — plus the corroborated pair at `common,1400`/
`common,1410` and the precedence case at `pd,10E0`. `--check` recomputes
`ec/annotations/call-graph-callees.csv` and fails on any byte difference.
`ec/tools/test_citation_callers.py` covers the two predicates alone, including
the `-`-pad case that a fixed-width column regex drops, and holds
`call_graph.parse_listing` and `citation_callers.transfers` to the same parse.
All three run from `.github/scripts/agent-gates.sh` except the unit suite, which
`bash tools/run-tests.sh` collects and which no per-commit gate calls — the same
pre-existing state `citation-code-vs-data.md` §Follow-ups item 4 records.
