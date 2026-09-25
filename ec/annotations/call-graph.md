# The EC call graph, and the second pass over the edges

Issue #134 asked for a second pass over the *edges* rather than the leaves: a
named function whose comment has to say "calls 0x0EE8" is not explaining
itself until 0x0EE8 has a name. The work list is therefore not the anonymous
functions but the anonymous functions an already-written comment already
depends on.

`../tools/call_graph.py` builds the graph from the committed listings and
`call-graph-callees.csv` is the ranked result, committed so it cannot drift
from the listings it was derived from. This file is the reading: the counts,
what this tranche covered, what is left, and — the part that matters most for
the next agent — **what the numbers do not say**.

Every figure in the census table below is reproduced by
`python3 ec/tools/call_graph.py`, which prints the census and rewrites the
table; `--check` recomputes and fails on any diff, and `--self-test` runs the
tool against `../tools/testdata/call-graph/`. Two sections further down quote
figures from a *different* tree, and each says which: §"Ordering" is measured
before this tranche's 44 rows exist, and §"Corrections" reconciles the several
trees the numbers were taken on.

## The counts, in every framing this repo has for them

| quantity | value |
|---|---|
| function rows in `decompiled/index.csv` | 2,714 |
| of those, still `FUN_*` | 752 |
| transfer instructions in the `.asm` listings | 5,027 |
| — `lcall` / `ljmp` / `ajmp` / `acall` | 3,854 / 1,063 / 74 / 36 |
| — resolving to an index row | 4,924 |
| distinct targets reaching a row | 1,841 |
| transfer sites whose target is no index row | 103, over 80 targets |
| targets still anonymous | 432 |
| inbound sites to those | 598 |
| anonymous rows no direct transfer reaches | 320 |
| distinct `FUN_*` callees the `.c` files name | 760 |
| anonymous callees a comment names | 124 |
| comments that name one | 147 |
| — candidate (callee, comment) pairs, before the frame gate | 353 |
| — kept / rejected / undecided by it | 157 / 165 / 31 |

*** CORRECTION 2026-09-25 (issue #470), leaving the table above as it was
written.*** One row stopped being anonymous. `pd 0x11C2` was `FUN_CODE_11c2`
with no `ghidra-functions.csv` row behind it, and is now
`dispatch_code_table_2byte_key`; **`FUN_CODE_11c2` no longer appears anywhere in
`ec/decompiled/`**. It is a target (`pd 0xCB2A` `lcall`s 0x11C2) and a `.c`-named
callee, so all three of those cells lose one: "still `FUN_*`" **790 → 789**,
"targets still anonymous" **470 → 469**, "distinct `FUN_*` callees the `.c` files
name" **798 → 797**. The inbound sites to that one target lose one with it, so
"inbound sites to those" **780 → 779**. Each before-value is the same tool run on
`origin/main`, so both ends of every movement come from `call_graph.py` itself.
(A `grep -c 'FUN_'` over `index.csv` instead reads 813 → 812 for the first cell:
it also counts the `FUN_` tokens sitting in comment columns, which is why that
was the wrong pair to quote.)

**The table's own figures were already behind before this, and each later pass
states its own movement rather than folding it into a new number that would hide
which drift is which.** 807 and 815 were measured on an earlier tree, and the
gap from there is another pass's, not this one's; the table's 470 was the
exception, because it was exactly what `call_graph.py` printed on the tree
*before* #470 landed and so is where the movement above starts. The table has
been re-measured twice since. Issue #603's tranche took the 37 common-area rows
it added off the anonymous side, and #470's one `pd 0x11C2` row is the −1 the
correction above records, so the table now reads the **752 / 432 / 760** of
those three cells — what `call_graph.py` prints on the merged tree. See
[`docs/findings/pd-common-address-spaces.md`](../../docs/findings/pd-common-address-spaces.md)
for #470 and
[`../../docs/findings/common-runtime-tranche.md`](../../docs/findings/common-runtime-tranche.md)
for #603. The tranche-history `FUN_*` figures further down (`829 → 814`) are a
record of what a past pass did and are untouched.

**The 432 and the 760 are two framings of related things, and neither is "the"
count.** The first is decoded out of the committed `.asm` listings; the second
is read off the `.c` export. The `.c` figure is larger because the decompiler
emits calls the listing does not carry directly. It is also the framing that
*cannot* be ranked on: a `.c` names its callees, so the moment 0x05E8 is
annotated the two frames disagree about whether anything reaches it. This
follows the precedent `../tools/audit_call_targets.py` sets by reporting an
upper bound and a decode count for every figure and never one.

**The three † rows were already wrong before issue #456 touched this file. They
were left as they were rather than quietly corrected; the table above now carries
the corrected figures instead, and the movement is recorded here rather than
lost.** The tool measured `still FUN_*` **789** against the table's 807, anonymous
rows no transfer reaches **320** against 337, and `FUN_*` callees in the `.c`
files **797** against 815 — `--check` never caught it because it compares
`call-graph-callees.csv` against the listings and never reads this table, which is
transcribed by hand. Issue #456 then re-measured the four citation rows and the
frame-gate partition against the tool and changed nothing else — on its tree they
read 110 / 136 / 364 / 146 / 188 / 30, rather than the one-low values a +4 delta
applied to `main`'s stale absolutes would have produced. The candidate and
rejected counts were one below what #456 measured on a tree without #470: the
`pd 0x11C2` row is what that comment names, and a named callee is not an
anonymous one, so its one rejected pair left the gate rather than joining it.

**On the tree holding both #456 and #603 the whole table is re-measured, and the
six citation and frame-gate cells are not #456's numbers any more.** Re-running
`../tools/call_graph.py` on this tree prints **124 / 147 / 353 / 157 / 165 / 31**
for those six, and the three † cells **752 / 320 / 760**; that is what the table
above records. The rise is not a measurement moving under us — it is this tree's
own two sets of new comments. #603's 37 rows and #456's twelve retypings between
them name addresses the previous tree's comments did not, so more anonymous
callees are cited and more candidate pairs reach the gate. Each side's own
before-value is preserved above rather than overwritten, so which drift is which
stays readable.

**Parse the `.asm`, not the `.c`.** That is the one thing that will silently
produce a wrong graph, and a future agent re-deriving this will reach for
`grep FUN_` first. The `.asm` listings spell the target as an address
(`lcall 0x05e8`), which survives a rename.

Two parsing traps, both of which undercount *quietly*:

1. The byte columns are whitespace-separated but not fixed-width, and a
   2-byte instruction pads its absent slots with a single `-`. A
   `[0-9a-f-]{2}` column regex matches nothing on those lines and drops all 110
   `ajmp`/`acall` sites. Read the tokens by position instead.
2. All four transfer forms reach a function. A `lcall`-only scan reports
   0x5A43 unreachable — it is reached by 11 `ajmp` and zero `lcall` — and
   0x00CF unreachable behind its single `ljmp`.

## Ordering is citation-first, and the issue's stated ordering does not hold

**The figures in this section are measured before this tranche's 44 rows
exist**, on `origin/main`, because 0x0EE8 is named by this change and so has no
rank on the tree above. To re-derive them, check out `origin/main`, copy
`../tools/call_graph.py` into that tree's `ec/tools/`, and run it there: that
tree reads 519 anonymous targets and 175 cited.

Issue #134 says the natural ordering is by inbound reference count. Inbound
count is a good ranking. It is not, however, the metric the issue's own
sentence uses, and **the issue's correction of itself does not reproduce
either** — worth saying plainly, because a follow-up agent will otherwise take
it as settled:

- 0x0EE8, the address the issue is written around, has 2 direct `lcall` sites
  (0x0EA2 and 0x0ECC). Only 108 anonymous callees have more inbound sites, and
  93 tie at 2, so it sits somewhere in **ranks 109–201 of 519** — a tie band
  rather than a position, and quoting a single rank off it would be false
  precision.
- It is cited by exactly **one** comment, the *lowest positive* count in the
  set. 81 cited callees have more and 94 tie at 1, so it lands in
  **ranks 82–175 of 175** by citations, behind 0x07D0 (25 comments) and 0x0A5A
  (24).

So no metric promotes 0x0EE8. What is true, and is why it is in this tranche,
is that neither metric would have reached it in the first forty rows, and the
issue names it. It is here because the issue asked for it, not because a
count selected it.

The table is sorted **citations descending, then inbound count**, then scope
and address so the order is total and reproducible. A citation is a comment
writing a callee's address in the canonical `0x` + 4-uppercase-hex-digit form.

**The canonical-width rule is the load-bearing part, and it is there to avoid a
specific false positive.** Matched numerically instead, a comment's `0x64` is
almost always a *data* value — `bank0,0xBD5D` reads "subtracts 0x64 (100) from
XDATA 0x0465" — and the short form would credit 43 citations to the 1-byte
function at 0x0064 that the comment never mentions. A comment writing a short
form (`0x5E8` for 0x05E8) is **not found by this method**; that is not
evidence the address is uncited.

**The width rule does not stop a 4-digit data address, so a frame gates the
citation.** On this firmware the same token is a function entry and an XDATA
byte — 0x07D0 is `FUN_CODE_07d0` here and `DBD1` in `registers.yaml` — so
`citations()` asks `../tools/citation_frames.py` whether a code frame governs
the mention, and credits it only if one does. **The window is bounded and local
to the mention, not the sentence and not the comment**, because a data veto
over the whole sentence rejects a genuine list: seven `bank1` comments write
"then calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF", where "to" is a
data marker and all five are real code addresses. A code frame is *necessary*,
a data frame is a *veto*, and **what neither settles is returned as
`undecided`** — 26 pairs today, against the 45 the gate started from — rather
than defaulted either way. The rejected and
undecided populations are printed by the tool and are never dropped, because a
guard that silently discards what it rejects cannot be told apart from one that
rejects too much. **Each of the 45 pairs the frame gate alone returned carries
a recorded verdict in
[`../../docs/findings/citation-undecided-verdicts.md`](../../docs/findings/citation-undecided-verdicts.md)**,
one row each, settled on the listing or on the committed firmware bytes. Those
are readings of the *sentences*, not reclassifications: the tool still reports
a pair as undecided unless a signal settles it, and an undecided line carries
the frame verdicts its mentions drew rather than a bare `--`. **The count has
moved three times, from 45, and each move is accounted for**: `sjmp` joined
`CODE_VERB` for the one committed comment that needed it (`bank1,9B03`'s "it
ends in an sjmp to 0x9B3C"); the citing listing's own transfer took 16 more
(§"The third signal" below), four of which are no longer in the population
because naming the callee took it out of it; and the re-export in issue #558
carried `bank1,9CE8` and `bank1,9D53` into the index, which took two undecided
pairs with them — that re-export is what
[`../../docs/findings/common-07f0-0f75-158e-1594-tranche.md`](../../docs/findings/common-07f0-0f75-158e-1594-tranche.md)
§"The export this change regenerates had been one commit stale" is about.
`sjmp` is **not** a member of `TRANSFERS` above
and must not become one: a PC-relative branch is not a call, and a comment's
lexicon and this tool's transfer set are deliberately different sets.

**Two further signals sit beside the frame, and neither is lexical.** A `pd`
comment cannot cite an EC row at all: the dump holds two 8051 programs
with separate address spaces (`registers.yaml`'s `static-scan` caveat, and
`build_ec_decompile.py` refusing an EC XDATA name on a `pd` row), and 45 of
the 71 `pd`-scoped candidate pairs name one — 25 of them `common,07D0`. Three
of those 45 read as a *code* frame, so the program-identity check is doing
work no lexical rule reaches. The complementary case is deliberately **not**
decided: a `bank0`/`bank1` comment citing a `common` row is legitimate,
because a common-area function is exported once and reached from both banks
(see the `Index` docstring in `../tools/call_graph.py`), so those fall to the
frame test alone. `0x1606` has six citations, all of them `XDATA 0x1606`, and
**no `registers.yaml` row at all** — which is why a lookup against that file
is not the guard, and why the discriminator is lexical plus program identity.
The full write-up, the frame census and the collision set are in
[`../../docs/findings/citation-code-vs-data.md`](../../docs/findings/citation-code-vs-data.md).

**The third signal is the citing listing, and it is the one that reads bytes.**
A frame decides what a *mention* is; it cannot see what the comment is attached
to, and on this firmware that is the whole of the difference between a real
citation and a comment refuting the decompile it was written from.
`../tools/citation_callers.py` asks the citing row's own `.asm`: an unbroken
`0xFF` run **vetoes** the pair as `fill-at-citer`, and a transfer in the listing
that resolves to the named callee **corroborates** a pair the window left
`undecided` — which is how the three `common,0x0070` calls, whose governing verb
is four ordinary words and a dash-aside away, come to be counted. Both sit
below the two vetoes, so neither can override a data frame or the program
identity. Written up in
[`../../docs/findings/citing-listing-evidence.md`](../../docs/findings/citing-listing-evidence.md),
with the 30/12/21 and 979/100 measurements and the one corroborated pair that
turns out not to be a call.

**Two known distortions in the citation count, one fixed in place and one left
in.**

- *A comment that refutes the decompile still writes the address.* Seven rows
  in `bank1` share one sentence ending "is not supported by these
  instructions", and every one of them names 0x110A, 0x158E, 0x0F75, 0x1594
  and 0x00CF inside the body it is rejecting. The frame gate reads each mention
  as a call, and it is right to: each one does read as a call, to a code
  address, in a call enumeration. What was wrong is the **caller** — the
  address the comment is attached to is `0xFF` fill, not the reset path those
  calls live in. 0x110A and 0x00CF have since been named and left the candidate
  set. ~~The three that remain, **0x0F75, 0x158E and 0x1594, are ranks 1–3 with
  7 citations each, all seven of them this artifact**, and the eighth citation
  (`common,0x0070`, which records the calls supportively) is `undecided`,
  because the aside between its governing verb and the mention is longer than
  the window. **So the top of the ranking is now right about the addresses and
  still wrong about who calls them** — the second, distinct defect, and the next
  thing to fix.~~ **Corrected 2026-09-25, issue #525**:
  [`../../docs/findings/citing-listing-evidence.md`](../../docs/findings/citing-listing-evidence.md).
  `../tools/citation_callers.py` asks the citing row's own listing the question
  the frame test could not, and the seven `bank1` listings are an unbroken `0xFF`
  run — `mov R7, A` repeated — that cannot make any call. Those **21 pairs are
  now refused** as `fill-at-citer` and the three rows read **`cited_by=1`
  against their own `inbound=1`**, `citing` reduced to `common:0070`, whose
  listing carries the three `lcall`s. The same listing evidence credits 16 pairs
  the window left `undecided`, so the partition **was** 148 / 206 / 28 — the 28
  rather than the 29 this correction was written against because `sjmp` had
  already taken one of them (the frame-gate paragraph above). That partition has
  moved since; the census table carries the current one and the frame-gate
  paragraph accounts for the difference. The
  comments themselves are **unchanged**: substituting a name there would assert
  the very call the comment denies, and the gate now makes their text irrelevant
  to the count.
- *Naming a function removes it from the count.* `cited_by` is defined over
  anonymous callees only, so a row's count goes to 0 the moment it is
  annotated, whether or not its citing comments changed. The `citing` column is
  the work list; it is empty for a row that has been done.

**The citing comments keep their bare addresses, on purpose.** 1,357 comments
already cite an already-named function by address — recounted on this tree by
the `citations()` match with the `FUN_*` test inverted, and it rises every time a
function is named, because a new row tends to cite helpers that are already
named — so replacing the address with a
name in the tranche's 105 citing comments would leave the export internally
inconsistent for no gain. Where the *point* of a sentence is what the callee
is rather than where it lives, the name is now there too: `bank0,0x0EA2` reads
"calls 0x0EE8 (timer1_load_th1_fd_tl0_clear_tf1_start)", and the matched
critical-section pair name each other.

## What the tranche covered, and why 44

This tranche is the first 40 anonymous callees by inbound count among those a
comment cites, plus every address the issue names, plus three more — **44 rows**
in `../annotations/ghidra-functions.csv`.

- The 40 are the top of the list by the ranking, so they are where a reader
  gets the most per row read.
- **Issue-named:** 0x0EE8, which no count would have selected (§ above), and
  0x05E8, which the 40 would have selected anyway.
- **Added beyond the issue's rule, three addresses the issue itself walks
  through:** 0x5A43 (the `ajmp`-only callee, 11 inbound), 0x00CF (the
  single-`ljmp` callee) and 0x110A (the bank-window helper). The first two are
  the two parser traps this tool exists not to fall for, and 0x00CF and 0x110A
  sit in the table's top ten on the primary key while falling out of the
  tranche on an inbound count of 1 and 2. They are 18 and 10 bytes; leaving the
  issue's own worked examples unnamed to keep a count tidy would have been the
  wrong trade.

The tranche is 33 `common`, 6 `bank0`, 5 `bank1`, carrying 376 inbound sites
from 256 distinct callers. A `common` function's `scope` is `common` and never
the bank that happens to call it most; `also_in` in the table records the bank
the index carries, and no bank is ever guessed from a call site — a
`common/0EA2.asm` and a `bank0/0EA2.asm` reading of the same bytes are
indistinguishable in a listing.

**None of the 44 is `type=unresolved` any more.** All twelve that were have been
retyped from their own bytes by issue #456, and **the row count did not move**:
1877 before it and 1877 after, because the one thing the tranche was missing was
not entries. Each retyping, and the evidence it rests on, is in
[`../../docs/findings/call-graph-unresolved.md`](../../docs/findings/call-graph-unresolved.md);
what follows is what the table above now says because of it.

**The five boundary rows were the load-bearing correction, and it went against
the hypothesis the rows themselves carried.** Four of them said the address might
be the head of straight-line code rather than a function, and `common 0x0200`
said outright that it was "the entry, not the function". **All five are real
entries, and each already had a row** — so none needed a new one. The split
Ghidra cut is real but it is a split *after* the entry: reading forward from the
committed image, 0x4A76 runs twelve bytes past its one-instruction body into
`FUN_CODE_4a77` and returns at 0x4A82; 0x3B4E runs fifteen bytes into
`dptr_3a00_plus_13x_3b51`, which was already a row; 0x7177 runs two bytes into
`FUN_CODE_717B` and ends in `jmp @A+DPTR`; 0x0200 runs 136 bytes into
`FUN_CODE_0213`. What settles each is the caller side, not the boundary:
`lcall 0x4A76` at 0x485B, 0x4868 and 0x492D is each followed by a separate
`lcall 0x4A4D`, which only makes sense if control comes back; `ec/decompiled/index.csv`
gives 0xD2BE and 0x9C47 a size of 1 each, so their single `ret` is the whole
function and not a window. All five are now typed from what the routine does —
`math`, `math`, `dispatch`, `init` and `forwarder`.

**The caller-side question 0x9C47 was opened for has an answer, and 0xD2BE turns
out to be the same shape.** `ec/decompiled/bank0/9AAD.asm` dispatches on XDATA
0x044B with a `dec`/`jz` chain giving cases 0, 1, 2, 3 and 4; `0x9B4A` is the
**default** arm, and the other six `ljmp 0x9C47` sites are bail-outs from inside
a case whose own test failed. So every path into it means "this case's condition
did not hold", and returning untouched is the whole of what the caller expected.
0xD2BE is the same device: all five `ljmp` sites are in `dispatch_on_0860`
(0xD091) and each is a guard — 0x0860 zero, 0x0860 0xFF, or bit 0 of 0x1C00,
0x1C11 or 0x1C29 set. Both are typed `forwarder` and named for the caller, which
is the house shape `bank1 0xA9B3` and `bank0 0x849C` already set.

**The six large bodies each got a type from the rest of the body, and five of
the readings were not what the first pass had written.** 0xD757 is a `state`
machine that re-enters its own head from nine places — its two dispatch operands
are bits 1 and 3 of XDATA 0x1500, not "bit 0 of 0xE1 and bit 1 of 0xE3", and
only the `0x1514 == 0xFC` case reaches 0x0200. 0x8931 is a `gate` over five
independently-enabled blocks that names CPU_TEMP and GPU_TEMP, and its head's
`jz` skips one nine-byte arm rather than the body. 0xDE83 is an `init` that
stages a descriptor at 0x3000-0x3007 and probes it, returning the result in the
carry; the 0x3000 block is **not** outside the EC's XDATA map as the row said.
0xBD45 is a `dispatch` whose 0x0497/0x0403/0x0539 consultation, which its old
text never reached, loads the same DPTR on both sides — a shape that invites the
opposite conclusion.
0xE656 is `math`: a 14-byte-stride walk of one of three CODE tables whose trip
count its own bytes fix at eight entries, and whose `jnb 0xF3` is not a PSW bit
at all but bit 3 of B. 0xCD80 is `state`, and its step is "at least 3" as the row
said: the substitution fires when `0x0397 & 0xFC == 0`, that is when 0x0397 is 0,
1, 2 or 3, and a larger 0x0397 passes through as itself, so nothing gives a step
below 3 — what the mask settles is the condition, not the bound.

**The citation figures moved and the count pin did not.** The four citation rows
and the frame-gate partition above are re-measured; `call-graph-callees.csv` was
regenerated with the tool over the same 1,841 rows, and **four of them gained
their first citation** — `common` 0x4A77, 0x492D, 0x0FE6 and 0x150A, all named in
the new comments — while none lost one, and the twelve rows above carry their new
names. `build_ec_decompile.py`'s record pin stays at 1,877 — a pin, so it moves
with rows a change adds on purpose, and this one added none.

**Naming 0x0EE8 is what closes `bank0,0x0EA2`'s comment.** Its own comment
already said the wait is on Timer 1 overflow; 0x0EE8 is what loads TH1 with
0xFD, clears TL1 and TF1 and sets TR1. The two halves stop being separate
unexplained facts, which is the whole of what issue #134 asked for.

### A note on the shape of the tranche

The ranking is over *callable helpers*, and 0x8863 is the top of it at 58
inbound sites — a 23-byte 16-bit compare that 25 named functions call, the
single highest-leverage row in the tranche. But inbound count does not
guarantee smallness: 0xD757 and 0x8931 are 282 and 474 bytes and reached 9 and
4 times, so the first 40 by this rule is not forty leaves. Expect the next
tranche to be cheaper per row, not more expensive, only because the top of the
inbound distribution is already spent.

## What is left, and the two limits a reader must carry

**The work list is the `annotated=no` rows**, 432 of them, of which **124 are
cited** by a comment and so are the ones a reader can trace to a sentence that
needs them. The rest are reachable but uncited: worth naming, not yet blocking
any explanation. The ranking is the order to work them in, and its top has
moved twice since issue #525 corrected it: the three `0xFF`-fill rows that held
ranks 1–3 fell to `cited_by=1` each, `common,07F0` then led at 3, and issue #558
has since named that one and the three rows behind it
([`../../docs/findings/common-07f0-0f75-158e-1594-tranche.md`](../../docs/findings/common-07f0-0f75-158e-1594-tranche.md)).
**The head of the table is now `bank0,DFA0` at `cited_by=3` against
`inbound=2`** — a row the ranking promotes on citations alone, which is the
ordering this file argues for and the first thing to read about it.

**320 anonymous rows have no direct transfer reaching them at all** — 320 of
the 752 `FUN_*` rows, reached by function pointer, by a dispatch table, or not
reached. **That is a limit of this method and not a claim that they are
unreachable.** The same goes for the 103 transfer sites whose target is no
index row: those are branches into straight-line code, not evidence of a
missing function. They are counted and reported rather than dropped or
guessed, because a target resolving to more than one scope row is left
unresolved rather than assigned to the caller's bank.

**A count is a ranking, not evidence of what a function does.** `bank0,DFA0`
leads on three citations to two `lcall` sites; that says it is cheap to read,
not that it does anything in particular. Each tranche row says what its own
bytes do and no further, and `unresolved` is a row that declines to guess.

**And `cited_by == inbound` can be two columns counting different call sites.**
`cited_by` is a count of comments and `inbound` a count of transfers, so they
agreeing is the two-framings-agree check, not a proof they are counting the
same thing. `../tools/citation_gap_scan.py` measured the case where they are
not: a call at an address the citing row's export stopped short of is in
neither. Over the 99 citing rows and 124 `(callee, citer)` pairs that gate's
corroboration arm cannot reach, **32 pairs** already have a same-scope transfer
to their callee booked to a *different* function, and **15 of the 90**
`cited_by == inbound` agreements in `call-graph-callees.csv` are carried that
way. **Those 15 have now been read one at a time**, and the split is **9 where
the kept comment names the neighbour's own site / 6 where it names a different
one** — the mechanical test for it, whether the `neighbour_edge` address is in
the callee's `citing` list, comes out identical to the verdict on this tree.
The two population callees among the 90 that carry no such signal, `common,451A`
and `pd,06EA`, were read the same way and both agree one-for-one. **Rank 3 of
the table is one of the 32 neighbour-edge pairs but not one of the 15
agreements**, so it is outside that reading: `bank1,E5D6` reads `cited_by=3` /
`inbound=1`, and its single inbound is `bank1,E5A7`'s `lcall` rather than the
boundary-cut `lcall 0xE5D6` at 0xE580 that `bank1,E57E`'s comment names. That
is a limit a reader must carry over the whole ranking, and `call_graph.py` is
unchanged by the measurement — the 1,841-row table is byte-identical either
way. Written up in
[`../../docs/findings/citation-gap-scan.md`](../../docs/findings/citation-gap-scan.md);
the per-row verdicts in
[`../../docs/findings/neighbour-edge-attribution.md`](../../docs/findings/neighbour-edge-attribution.md).

**No register `status:` changed and no behavioural test was run.** Naming a
helper is not a finding about a register, so `registers.yaml` and
`ghidra/xdata-symbols.csv` are untouched. Nothing here was observed on
hardware; where a named helper would need a behavioural check to confirm, the
row stays at what the bytes support.

## Corrections to the figures in the issue and in this change's plan

The plan that produced this work estimated the census before the tool existed.
Re-measuring with the tool moves several figures, and the per-address
readings the plan offered as a starting point all reproduced exactly — 0x05E8 at
14 `lcall`, 0x05EF at 11 `lcall` + 1 `ljmp`, 0x0EE8 at 2 `lcall` from 0x0EA2 and
0x0ECC, 0x8863 at 58 `lcall` from 34 callers, 0x5A43 at 11 `ajmp` and 0 `lcall`,
0x4A69 at 21, 0x3B22 at 13, 0x110A at 2, 0x00CF at 1 `ljmp`. The disagreements
are these. **The "measured" column is the tranche's own tree at the time the
plan was re-measured, before issue #136 landed on main, so it is not the census
table above** — the last paragraph of this section reconciles the two:

| quantity | plan's estimate | measured |
|---|---|---|
| function rows in `index.csv` | 2,708 | 2,710 |
| still `FUN_*` | 885 | 873 |
| transfer sites | 5,022 (3,849 `lcall`) | 5,027 (3,854 `lcall`) |
| distinct targets | 1,906 | 1,841 |
| anonymous targets / sites | 537 / 1,184 | 530 / 1,174 |
| `FUN_*` callees in the `.c` files | 891 | 880 |
| anonymous callees a comment names | 228 | 179 (530 anonymous callees, pre-annotation) |
| 0x0EE8 "first on the citation count" | — | cited once, in the bottom of the field — see §"Ordering" |

The `.asm`-side gaps come from resolution: a target with no index row (80 of
them, 103 sites) and a target that resolves to more than one scope row are left
unresolved rather than guessed. The citation gap is the canonical-width rule
above. And the last row is the correction that matters most — see §"Ordering is
citation-first".

The tranche's own effect on those figures, so the post-annotation numbers above
can be re-derived: of the 44 rows, **43 were cited** and left the cited set
(0x5A43 was not), and the 44 new comments newly cite **9** addresses that are
still anonymous. 179 − 43 + 9 = 145, and the merged tree reads **146** because
issue #262's rewrite of the `bank1,19A8` comment — landed on main while this
tranche was open — names one more anonymous callee, `bank1 0xC0A8`, which is the
whole of the difference. The inbound figure moves the same way — 530 − 44 = 486
anonymous callees, and 1,174 − 798 = 376 inbound sites carried by the tranche.
The function-row count moves for the same reason from the other side: #262 seeds
`bank1 0xC1E7`, so the merged tree carries 2,710 index rows where the tranche's
own tree carried 2,709.

**And the table above moved again when this branch was rebuilt on a main that
carries issue #136.** #136 names 21 common-area interrupt entry points, so the
figures above are the merged tree's, not the tranche's own: the arithmetic in
the previous paragraph (146 cited, 486 anonymous callees, 798 inbound sites)
is the tranche on the tree before #136, and #136 takes the table to 141, 475
and 787, with `FUN_*` rows 829 → 814, unreached anonymous rows 343 → 339,
`.c`-named `FUN_*` callees 836 → 822 and citing comments 314 → 315. **Those
two citation figures — 141 callees and 314 → 315 comments — are pre-frame-gate
counts**, measured under the canonical-width rule alone; the guard described
below is what takes them to the census table's **99** and **142**, and they are
left in pre-gate units here so the paragraph still records what #136 did. The
already-named citation count in §"The citing comments" is 1,279 on the tranche's
tree and 1,300 on the merged one — a comment row citing at least one named
index row by canonical-width address, its own included, which is the
`citations()` match in `../tools/call_graph.py` with the `FUN_*` test inverted.
The one between them is the tranche's own `bank0,0x0EA2`: naming 0x05E8, 0x0EE8
and 0x05EF turned a comment that cited nothing already-named into one that cites
three, and it is counted here like any other. The 1,299 this section first
carried was the figure before that row was annotated; re-derive it with the
`citations()` match rather than carrying either number forward.

### The frame gate's own correction: 0x07D0 is 2, not 0 and not 27

Issue #453 argued that the top of this table was XDATA, and that is right —
`common,07D0` carried 27 citations and only 2 of them are calls. What it also
said, that *no* comment citing 0x07D0 is citing that code function, is too
strong, and the wrong version is left here rather than quietly fixed.
`common,018C` reads "The other arm calls 0x07D0" and `common,029B` reads "The
other arm writes 0x11 to 0x1700, calls 0x07D0" — and both listings carry the
transfer: `../decompiled/common/018C.asm:40` and `029B.asm:50` are
`lcall 0x07d0`. So `cited_by` for that row is **2**, which is also its
`inbound`, and the two framings agreeing is the check that a guard which
zeroed all 27 would have failed. The 25 that are gone are all `pd` comments
naming the PD image's own byte, every one of them carrying the
`cross-program` reason.

**0x1C00 is the limit worth carrying, not an absence.** Twenty-one comments name
it, 20 in a data frame and 1 unsettled — but it has **no row in this table at
all**, because no transfer reaches it, so it was never in the ranking to be
wrong in. That is the shape to watch for in any other count
here: not ranked is not absent, and 74 candidate pairs name a callee the table
carries no row for. The tool prints that number beside the gate's.

## Adding the next tranche

Same path as the first sweep, documented in `README.md`: slice the
`annotated=no` rows, annotate one shard at a time, verify each shard against
its own `.asm`, and merge. `../tools/call_graph.py --check` then confirms the
table still matches the listings, and the build confirms every new
`(scope, addr)` resolves to an exported function with a non-empty `evidence`
cell.

**Correction (2026-09-24, issue #454): "not wired" was wrong — the check
runs per commit now.** This paragraph previously said `call_graph.py --check`
was not in `agent-gates.sh` and was a one-line follow-through for a human,
on the reasoning that the pipeline's push token has no `workflow` scope. That
reasoning holds for `.github/workflows/` and did not reach this file; both
`--check` and `--self-test` now run per commit from `check_ghidra_tooling` in
`.github/scripts/agent-gates.sh`. The two constraints the old text named are
still why the arm is separate: the tool takes no `--work` and has no scratch
directory, so it does not fit the loop's default branch, which passes
`--work "$scratch" --check && --work "$scratch" --self-test`; and both modes
need no Ghidra and no network, which is what lets the check live in the cheap
gate at all. The self-test's own fixture assertions are what prove the check
still rejects — a table with one cell altered and one with its last row
dropped both come back rejected, over the same comparison `--check` runs. A
template re-copy of `agent-gates.sh` drops the tool and its arm again;
`docs/agent-pipeline.md` item 6 carries both for re-applying.
