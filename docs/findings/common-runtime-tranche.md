# The unannotated `common` pool, ordered, and its first 37 rows (issue #603)

[`../../ec/annotations/subsystems.md`](../../ec/annotations/subsystems.md) §2 measures
the largest single block of undecoded firmware in this repository: 656 of the
753 exported `common`-area functions carry no annotation row, 87% of the
program. A size is not a queue. This file is the queue — a stated, total,
re-derivable ordering over the rows no other open issue has claimed, the named
cut that took the first tranche out of it, and the reading of those 37
listings.

Every figure is reproduced by a command named beside it, over committed inputs
only. **Nothing here is a behavioural claim.** No register was read, written or
read back; no interrupt was delivered; no `registers.yaml` row was added and no
`status:` moved. Naming a function is not a finding about a register
(`../../ec/annotations/call-graph.md` §"What is left"), and the one row in the
tranche that touches a register the map *does* name moved nothing.

```console
$ python3 ec/tools/rank_common_runtime.py --self-test   # the known answers, the refusals
$ python3 ec/tools/rank_common_runtime.py               # prints every figure below
$ python3 ec/tools/rank_common_runtime.py --emit-csv    # the committed ranking, to stdout
```

The ordering is committed as
[`../../ec/annotations/common-runtime-ranking.csv`](../../ec/annotations/common-runtime-ranking.csv),
one row per pool address in rank order, so the next tranche is a cut over that
file rather than a re-derivation. The tool writes no committed file; that CSV is
a redirect of `--emit-csv`, and the self-test holds it to the same numbers.

## The pool: 455 of 656, and the three exclusions that make the difference

The whole 656 was not available. Three open issues own parts of it, and each
exclusion is an address range or a named address list read off the committed
tree — never a hand-typed skip list of the rows a previous run happened to see,
which is the shape that goes stale silently:

| exclusion | owner | measured |
|---|---|---|
| `0x1150`-`0x1ABC` | #574, the 403 BL51 cross-bank trampolines | **201** unannotated rows, excluded by address |
| `bank1:0x8001`-`0x8189` | #555, the 42 seeds that tile it | **0** — the common area ends at `0x7FFF`, so the overlap is zero *by construction*; the census prints the zero as a measurement rather than leaving it to be assumed |
| five boundary rows | #456 | all five already annotated (`0x4A76`, `0x3B4E`, `0x7177`, `0x0200`, `bank0 0xD2BE`), so it currently owns none of the pool |

656 − 201 = **455**. The self-test pins each number and, for #574, pins the
*mechanism*: every in-band address is out and every out-of-band address is in,
checked against the range rather than against a list, so a skip list would pass
the same assertion and a moved or renamed row would not.

One detail of #574's block worth recording, because it is the kind of thing a
range hides: the block's **unannotated** rows run `0x116E` to `0x1800`, not
`0x1150` to `0x1ABC`. `0x1150`-`0x1168` are §4's five annotated thunks and
`0x1806`-`0x1ABC` are annotated trampolines, with the 201 unannotated ones
interleaved between them. So #574's band is not a gap in the map; it is the
remaining two-thirds of one.

## The ordering criterion, and the three limits on what a rank is

Composite, stated once, total order, nothing left to taste:

1. **inbound call-graph degree, descending** — `../../ec/annotations/call-graph-callees.csv`;
2. **XDATA read+write weight, descending** — the `functions` column of
   `../../ec/annotations/xdata-registers.csv`, counting the `common:0xADDR=` tokens
   naming the address, over the registers with `read+write > 0`;
3. **address, ascending** — the tie-break, so the order is reproducible.

Reachability from the vector table is carried as a **column, not a fourth sort
key**. Its roots are `build_ec_decompile.discover_vector_table()`'s own 12
targets, read out of the firmware and not re-derived here; the walk goes
forward over the committed `.asm` listings through `call_graph.Index.resolve`,
the same resolution rule the call graph itself uses. It reaches **13**
unannotated common-area functions, **10** of them outside #574's band.

That last choice is about what a reader has to hold in their head. As a sort
key, one vector-reached address with a single inbound call would outrank one
with twelve, for a reason the ordering never states. As a column it is a fact
about thirteen rows — and it is what makes the cut below a union rather than a
threshold. Measured: **0** of the 10 clear the inbound cut on their own.

**Three limits, in the order they bite.**

- A count is a **ranking, not evidence of what a function does.** `inbound` is
  how many resolved transfers reach an address. `common 0x355E` ranks first in
  the pool on twelve — and its listing is **one `ret` byte**, reached by twelve
  `ljmp` from exactly two callers. It is a shared epilogue. A 12-inbound
  runtime helper is not thereby a mechanism, and the row says so in its comment
  rather than letting the rank stand in for a reading.
- The **291 of the 656 that no transfer reaches are "not found by this
  method", never "unreachable"** — 153 of the pool's 455. A row absent from the
  call graph is a row the listing walk placed nowhere: the boundary may cut the
  transfer, the caller may be reached only through data, and the common area is
  exported on a call-target byte scan that is an upper bound by construction
  (`../../ec/annotations/bank-call-audit.md` §1). `../../ec/annotations/registers.yaml`
  states the same rule for its own census and it is the same rule.
- The XDATA weight is a **census of decompiled text** and shares the C-level
  blind spot `registers.yaml` documents, so it is not independent confirmation
  of anything a row's comment says. It is a tie-break. 120 of the 455 have a
  non-zero weight, 206 tokens over all of them, and the heaviest pool row is
  `0x0D4A` at six.

## The column-name trap, and why the self-test pins it

The XDATA weight has to be read from `xdata-registers.csv`'s **`functions`**
column. `functions_touched` is a *count*; `functions` is the token list. Reading
the count as a list matches nothing, and the ranking that comes out has a weight
of exactly **0 for all 455 rows** — which looks like a measurement, and sorts
the whole pool on its address alone while appearing to have consulted a second
signal. The self-test runs the same counting over both columns and asserts the
wrong one yields zero, so the check that has quietly stopped rejecting is the
one that goes red.

The same trap exists in the other input, one column over:
`call-graph-callees.csv`'s **`callers`** is a count and its **`citing`** column
is the token list. So a comment cannot quote a caller address out of
`callers`, and none of the 37 rows does. The rows that name their callers —
`0x355E`, and the three Timer 1 epilogues — got them by walking the committed
listings, which is also how the caller *sets* rather than the caller *counts*
were established.

## The cut, and the tranche

**`inbound >= 4`, unioned with forward reachability from the vector table,
over the pool.** A predicate over the ranking rather than a round number — the
same discipline `../../ec/annotations/README.md` §"The second batch" used when it
cut on a measurable boundary instead of a count.

**37 rows, 999 bytes of committed listing, 28 of them 16 bytes or fewer — and
the cut is now exhausted.** Every row that qualified carries an annotation row,
so a run today selects none and the remainder's top is 30 rows tied at
`inbound=3`. The next tranche's cut has to move down the ranking; that is a fact
about the cut, not a fault in it, and the tool's report says so rather than
printing an empty tranche under a heading that reads like a failure.

**The committed CSV is the tranche's record and is deliberately not the tool's
current output.** Those 37 are annotated, so a fresh run cannot re-rank them
and regenerating the file would erase which rank each landed at — the one thing
a reader needs to judge the next cut. The self-test holds the two apart: it pins
the live population (618 unannotated, a **417**-row pool) *and* asserts that all
37 `in_tranche` rows carry an annotation row, that the 418 below them are the
rest of the pool, and that the one row the tranche annotated with no CSV row of
its own is `0x10FA`. `--emit-csv` emits the live ranking; it is how the file was
created once, not a regeneration of it.

| figure | before | after |
|---|---|---|
| `common` unannotated | 656 (87%) | **618 (82%)** |
| `common` annotated | 97 | **135** |
| rows the index marks annotated | 1902 | **1940** |
| annotated function rows | 1877 | **1914** |
| `unresolved` rows | 157 | **160** |

Both columns are this tranche's own before-and-after. The `before` column is the
tree this branch forked from, and it **already** carries issue #456's twelve
`unresolved` retypings and issue #470's one `pd 0x11C2` row — those are 157 and
1,877 here, not the 169 and 1,872 an earlier draft of this table carried, which
measured a base older than the branch point. The `after` column is the tree this
landed on, re-measured rather than added up. The tranche's own movement is
**+37** annotation rows, **+3** `unresolved` (157 -> 160) and **+38** index rows,
the last because `0x10FA` took a name without a CSV row of its own.

**38 index rows moved, not 37, and the 38th is the interesting one.**
`common 0x10FA` is a bare `ljmp 0x0A74` — three bytes, `seed_basis=call-target`
— and the exporter renamed it `rearm_timer1_then_set_bit_4_of_internal_41`
when the tranche named its target. So naming one function moved a second index
row with it, which is why the per-program annotated count rises by 38 while the
CSV gained 37 rows. It is the twelfth "second copy of a name" §2 enumerates
(`second_copy_census.py` reads 12 target-of-a-transfer rows out of 26), and the
only one this tranche created.

The tranche's own shape: 35 rows seeded by a call-target byte scan, one by the
vector-target walk, one by Ghidra's auto-seeding; all 37 `also_in=bank1`, which
is what the common area being byte-identical in both banks predicts and is
therefore not evidence of anything. By `type`: 14 `writer`, 11 `state`, 3
`reader`, 3 `math`, 2 `forwarder`, 1 `dispatch`, 3 `unresolved`. By
`name_basis`: 29 `code-shape`, 6 `register-map`, 1 `abi-symbol`, 1
`unresolved`.

**Inbound count does not guarantee smallness.** Nine rows are over 16 bytes, and
five of them are large: `0x0C86` (195), `0x43A5` (180), `0x2E9C` (129),
`0x2F1D` (104), `0x2B6C` (85). `../../ec/annotations/call-graph.md`
§"What the tranche covered" says so about its own cut and it holds here. What
does *not* follow is that a large row is an unread one: four of the five carry
a mechanism — `0x0C86` is the `dispatch` and the other three are `state` — and
only `0x43A5` lands `type: unresolved` where the bytes do not carry one, which
is a correct outcome rather than a failure. `unresolved` is in the vocabulary
precisely so that saying "the bytes do not say" costs nothing, and `0x43A5` —
seven transfers, 180 bytes, one of the tranche's three `unresolved` rows — is
the clearest case in it of a rank selecting a row whose decoding is much bigger
work than its rank suggests.

## What the 37 rows turned out to be

They are not 37 unrelated helpers. Read together they resolve into five
families, and the two the ranking could not have predicted are the most
interesting:

**A background dispatcher, 195 bytes, at `0x0C86`.** The largest row in the
tranche and the only `dispatch`. It polls eleven direct bit addresses
`0x30`-`0x39` and `0x3B` — under the convention the tranche uses, the byte the
`.c` prints for each, `_6_0` to `_6_7` plus `_7_0`, `_7_1` and `_7_3`, so **two**
byte groups read as eleven task flags — and for each one that is set, clears it,
calls one routine, and jumps back to `0x0C86`. The listing has **fourteen**
branches back to its own entry (8 `ljmp`, 5 `sjmp`, 1 `jc`), which is what make
it a loop rather than a straight-line sequence; the call graph's inbound 9 is a
different count — 1 `lcall` plus 8 `ljmp` reaching `0x0C86` from its two callers
— and is not a count of the branches from inside. Each of the eleven callees is
called once, from `0x0C86`, so there is no most-called among them. This is the
EC's main polling loop, and it was sitting in the 87% with no row.

> **The one convention this tranche uses for a bit address.** A direct bit
> address is quoted with the byte its own `.c` prints for it — `0x18` as
> `_3_0`, `0x32` as `_6_2` — which is the form the pre-existing `0x05B6` row
> already used. That `.c` label is *not* the internal RAM byte the bit lives in
> (`ec/tools/disasm8051.py`'s `bit_name()` puts `0x18` at `0x23.0`), and for a
> handful of operands — `0x30B5`'s `0xE7` — neither convention establishes one.
> Those rows say the bit address and stop rather than name a byte.

**A timed window, and the Timer 1 SFR identities it pins.** `0x0E72` loads
`TL1` with `0x01` and `TH1` with `0xFA`, clears `TF1` and sets `TR1`;
`0x0E7D` clears `TR1` and `TF1` and clears direct bit address `0x32`, the bit
the `.c` prints as `_6_2`. Both are called from the Timer 1 handler at `0x05B6` —
`0x0E7D` on entry, `0x0E72` on exit — so that handler runs its body **inside a
window Timer 1 times**, and the
only value the handler leaves that could hold the result is internal byte
`0x41`, which it splits on carry. `0x0A74` is the third leg: it calls `0x0E72`
and then *raises* bit 4 of `0x41`, the bit the handler *clears*. So `0x41`
bit 4 is a flag the two of them set and clear, and `0x0A74` is what a reader
would have called a five-byte bit setter.

**Three byte-identical Timer 1 epilogues, and they are three.** `0x3BDD`,
`0x4368` and `0x4AFB` are all `c2 8e c2 8f d2 ab 22` out of the **firmware**,
not merely out of the decompilation: clear `TR1`, clear `TF1`, set `ET1`, return.
Their caller sets are disjoint — `{0x30DF, 0x3609, 0x383D, 0x3A0D}`,
`{0x3DCE, 0x3DFC}`, `{0x451A, 0x4666, 0x46F9, 0x4825, 0x4921}` — so these are
three separate routines that agree, not one routine framed three times. Their
combined 15 `lcall` sites, from 11 callers, are why the ranking's inbound column
reads 4, 4 and 7 for all three of them: **that column counts transfers, and
these rank high per site rather than per caller** — `0x4368`'s four sites come
from two callers and `0x4AFB`'s seven from five. The address is in each of the
three names because the bytes cannot tell them apart.

**A pseudo-register accessor family in the upper internal RAM.** `0x3835`,
`0x3983`, `0x3ACC` and `0x3AD1` are the same shape — `mov R0,#imm`, `mov A,R7`,
`mov @R0,A`, `ret`, with `0x3AD1` clearing A first — writing upper internal RAM
`0x9D`, `0x85`, `0x9F` and `0xA0`. The 8051 cannot address `0x80`-`0xFF`
directly, so a compiler emits exactly this, and `0x2E9C` reading `0x85` (and
`0x9D` only when `0x85` is zero) and `0x2B6C` reading `0x87` are the same
firmware treating those bytes as variables. Four setters, three internal
addresses read inline, and one caller using the setter with zero to clear.

**The rest** is the XDATA-helper layer: `0x3B20` is a two-byte getter taking its
address in the caller's `DPTR` and returning in `R7`, which is the convention
`0x2E9C` and `0x2F1D` both use, so it is a getter they are built on rather than
one that knows an address. `0x3B32` and `0x3BAE` turn a packed two-byte code
constant into a `DPTR` — `(A << 8) | code[DPTR+1]` — which is how this firmware
loads a 16-bit value without a 16-bit immediate. `0x4A42` computes
`0x4900 + 0x54 + (A * 21)` and `0x43A5` computes `0x4900 + 0xCC + (R6 * 15)`:
two table-walk stride constructions over the same `0x4900` base, 21 and 15
bytes apart.

**One finding the ranking did not order, because it took two rows to see it.**
`0x2E9C` and `0x2F1D` both store three register arguments into three
consecutive XDATA bytes, call `0x2DE3`, clear direct bit `0x61` and set `0x60`,
and then run a **shared helper sequence** — five items from `0x2EE9` on the
first, six from `0x2F33` on the second. One template, written twice, and the
counts are not the same: `0x2E9C` runs `0x3BD0`, `0x3B8A`, `0x3B20`, `0x3B70`,
`A=0x1E`, where `0x2F1D` runs `0x3B1D`, `0x3BD0`, `0x3B8A`, `0x3B1D`, `0x3B70`,
`A=0x1E` — `0x3B1D` leads where `0x2E9C` has no lead, and `0x3B1D` stands in the
fourth position where `0x2E9C` has `0x3B20`. They also diverge after `A=0x1E`:
`0x2E9C` calls `0x3B3C` and `0x3BAE`, ORs a code-table byte into a
saved-and-restored `DPTR` and tail-jumps to `0x3A0D`; `0x2F1D` *writes* the
`0x1E`, calls `0x3609`, and enters a retry loop whose counter is XDATA `0x0A52`
and whose compare at `0x2F52` is that byte against XDATA `0x0A51`.

**It is one template and not one routine, and the 45 bytes settle it** — the
byte runs at `0x2EED`-`0x2F19` and `0x2F33`-`0x2F5F` are *not* identical, so a
first reading of these two as "the same routine's entry and its retry half" was
an overclaim and is corrected in both rows. The first bytes of the two runs
already differ, which is also why the shared sequence starts at `0x3BD0` in both
and not one instruction earlier.

`0x05E7` is in the tranche **by the reachability arm** — it is reached by being
a vector target and by no transfer — and it is the one vector target
[`subsystems.md`](../../ec/annotations/subsystems.md) §3 recorded as carrying no
row at all and no citation reaching it. That is now closed, and §3 says so.

## Two defects in the annotation layer's own grading, this tranche's rows had to work around

Both are pre-existing, both are in `../../ec/tools/grade_name_basis.py`, and
neither is fixed here: both would re-grade rows across the whole file, which is
a merge-hostile edit to a shared tool and not this issue's work. They are
recorded because the 37 rows' names are shaped around them, and a later reader
who "simplifies" a name back would silently introduce a wrong grade.

**1. `SFR_WORDS` pairs the Timer 0 words with the wrong bit addresses.**

```
("timer1", 0x8E),      # TCON.6 = TR1
("tf1",    0x8F),      # TCON.7 = TF1
("timer0", 0x89),      # TCON.5 = TF0
("tr0",    0x89),
("tf0",    0x8A),      # TCON.5 = TF0
```

`TR0` and `TF0` are `TCON.4` and `TCON.5`, which are bit addresses `0x8C` and
`0x8D`. `0x89` and `0x8A` are `TMOD` and `TL0` as *byte* addresses, and the
inline comments repeat each other, so the table looks like the second and third
rows were meant to be `0x8C` and `0x8D`. The consequence is narrow: a Timer 0
row cannot be corroborated by the *word* `timer0`, because the listing does not
touch `0x89`. So `0x0E5E`'s name cites its byte operands —
`timer0_reload_8a_06_8c_f1_clear_8d` — which is both more informative and the
only thing that earns its `register-map` grade. The fix is three bytes in one
tuple.

**2. `listing_facts` reads a `mov R0,#0xNN` immediate as an SFR bit operand.**

`listing_facts` adds any two-hex-digit operand whose `value & 0xF8` is in
`BIT_SFR` to the listing's `sfr` set, and that regex reads the immediate of
`mov R0,#0x9D` as readily as the operand of `clr 0x8E`. The two are different
addressing modes: `0x9D` through R0 is upper internal RAM, and no BIT_SFR entry
describes it. So a name citing an indirect base can be graded `register-map` on
a value the architecture says is not an SFR — the same class of error the
`listing_facts` docstring already refuses to make for a 16-bit CODE address
masked down to a low byte, and for a `pd`-scoped `mov DPTR,#0x07E2` that is the
PD program's own map.

That is why the four pseudo-register setters are named
`store_r7_to_upper_internal_ram_byte_3835` and not
`store_r7_to_internal_ram_9d`: the address is in the name, and putting the
*byte* in the name would earn a `register-map` grade off an `mov R0,#imm`.
`0x3AD1`'s is the sharpest case, because `BIT_SFR` literally names `0xA0` as
`p2` and the instruction does not touch the port.

## What this does not establish

Stated as a list, because the limit is the point.

1. **A rank is not a reading.** The ordering says which 455 rows to read first
   and nothing about what any of them does. `0x43A5` landing `unresolved` on
   180 bytes and seven inbound is the ranking being right about what it
   measures and wrong about how much reading the row takes.
2. **No register `status:` moved, and none could have.** The tranche's 37
   listings reach **25** distinct XDATA addresses and **not one** of them has
   an `addr:` row in `registers.yaml`: **24** loaded by a `mov DPTR,#imm` in at
   least one of the 37 listings, plus one that no immediate names — `0x0A4E`,
   which `0x2E9C` reaches by its second `inc DPTR` after starting the triplet
   at `0x0A4C`. (`0x0A4D`, `0x0A50` and `0x0A51` are `inc DPTR` successors too,
   but each is a `mov DPTR,#imm` in its own right, so counting them as inc-only
   double-counted them.) `0x007E` and `0x00F5` are among the 24: `0x0C86` loads
   them itself, `mov DPTR,#0x7e` at `0x0CF8` and `mov DPTR,#0xf5` at `0x0CA4`,
   not through a callee. The generated `ec/ghidra/xdata-symbols.csv` is
   therefore untouched: there is no register to rename. It is also why the
   tranche's XDATA-weight signal is weak *here* -- it is a census of
   decompiled text over a region the register map does not reach at all, so it
   cannot confirm a row's comment and does not try to.
3. **The 291 unplaced rows are not unreachable**, and the 418 below the cut are
   not unimportant. They are the next tranche.
4. **Reachability is from `discover_vector_table()`'s walk, not from a textbook
   vector table.** §3 already records that this firmware's table defeats the
   textbook layout; `0x05E7` is reached from the table's eight-byte stride and
   which vector the `0x002B` slot serves is not established.
5. **Nothing was observed on hardware.** No register behaviour, no interrupt
   delivery, no timer period. Where the bytes leave a question — what the
   `0x0C86` dispatcher decides, what the `0x43A5` state sequence switches
   between, whether Timer 0's mode is 1 — the row says so and stops.
6. **The three identical epilogues' callers are 15 `lcall` sites from 11 caller
   routines in the committed listings, and nothing else.** Which routines those
   callers are, and whether the vendor emitted the sequence three times or a
   compiler did, is not established.
7. **One row is not a function.** `0x5A55` is five bytes inside a table that two
   decodings disagree about — the eight bytes at `0x5A5A`-`0x5A61` are `8c aa`
   then six `c8` (`xch A, R0`), with a `reti` at `0x5A62`, which a data reading
   takes and a code reading cannot make say anything, and `0x5A43`'s row leaves
   the run undecided — and it takes `unresolved` in both columns with a
   placeholder name on purpose.

## What a follow-up issue should pick up

Named here rather than filed, per this repository's rule that a finding which
opens a question says so in the PR.

- **The two `grade_name_basis.py` defects above.** Three bytes in `SFR_WORDS`
  and one predicate in `listing_facts`; each would re-grade existing rows, so
  each needs its own PR with the re-grade in the diff.
- **The next tranche's cut.** `inbound >= 4` is spent; the 417-row remainder
  starts at 30 rows tied at `inbound=3`, and whether the next cut is
  `inbound >= 2`, a size ceiling, or a family boundary is a judgement the next
  agent should make explicitly rather than by nudging the same predicate down.
- **The `0x0C86` dispatcher's eleven callees.** The flags are named; the eleven
  routines they reach are not, and they are where the firmware's actual
  behaviour is.
- **The `0x4A42` / `0x43A5` stride tables at `0x4900`.** Two constructions, 21-
  and 15-byte strides, over a base neither names. A table dump would close
  both.
- **`0x0EE8`'s name reads `tl0` where its own comment reads `TL1`.** A
  pre-existing typo in a row this tranche cites three times. Correcting it is
  an edit to a shared file for an unrelated reason, so it is named here rather
  than made in this PR.
