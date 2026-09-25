# The bytes a function boundary cut out of a citing listing (issue #560)

`citation_callers.py` asks a citing row's own `.asm` whether it can make the
call its comment names, and `docs/findings/citing-listing-evidence.md` measured
where that works. It does not work for one population, and the population is
named there: a real call at an address the export stops short of is not in that
export, so neither the veto nor the corroboration can see it. This file is the
measurement of that population — **99 citing rows, 124 (callee, citer) pairs,
three verdicts: 2 `boundary-cut`, 121 `no-transfer`, 1 `not-code`** — and what
the split means for the ranking.

`ec/tools/citation_gap_scan.py` is the tool. It walks, per pair, the image bytes
from the end of the citing listing's last instruction to three bytes past the
next exported entry in that row's own scope, decodes that window with
`disasm8051.py` (which shares no code with Ghidra's SLEIGH), resolves any
transfer through the same `call_graph.Index.resolve` the graph uses, and writes
one row per pair to `ec/ghidra/gap-citation-scan.csv`.

Every figure below is reproduced by `python3 ec/tools/citation_gap_scan.py`, and
the ones the report does not print are in
[§Re-deriving](#re-deriving). **Nothing here is a behavioural claim.** No
register `status:` changed, no listing was re-read, no live test ran, and
nothing was observed on hardware: this is a text measurement over the committed
listings and the committed image.

## The lead: 86 of the 99 rows have no gap at all

**The issue's premise is the exception.** It describes "bytes stranded between
exports" and gives `bank1,E57E`'s 2-byte gap as the worked example. Measured on
this tree, **86 of the 99 citing rows have a zero-byte window**: the next
exported entry in the citing row's own scope begins at exactly the address
where that listing ends. The "gap" is empty, and the window is really the
**head of the neighbouring export** — 3 bytes of slack over the next function's
own first instruction.

That reframes what is being asked. For 86 rows the question is not "is a call
stranded between two functions" but "is the function that starts where this one
stops a caller of the named callee". For the other **13** it is the issue's
question, and the split below is over the pairs (110 of 124 zero-byte, 14 not)
because one comment naming three callees is three pairs over one row.

The 13 non-zero rows are worth naming in full, because the gap is usually far
larger than the issue's 2-byte example — the median is 24 bytes, and only two
are as short as the example. The `verdict` column is the one this file's own
split produced, and it is the reason two of these thirteen read differently from
the other eleven:

| citing row | gap (bytes) | next entry | verdict |
|---|---:|---|---|
| `bank1,F02C` | 1 | `bank1,F030` | `no-transfer` |
| `bank1,E57E` | 2 | `bank1,E582` | `boundary-cut` |
| `bank0,C31F` | 7 | `bank0,C333` | `no-transfer` |
| `pd,39E7` | 11 | `pd,39F9` | `no-transfer` |
| `bank0,C15C` | 16 | `bank0,C174` | `no-transfer` |
| `bank0,C278` | 16 | `bank0,C295` | `no-transfer` |
| `bank1,A2DA` | 24 | `bank1,A2F3` | `no-transfer` |
| `common,355E` | 25 | `common,3578` | `boundary-cut` |
| `bank0,C12C` | 32 | `bank0,C154` | `no-transfer` |
| `bank1,EFDA` | 42 | `bank1,F012` | `no-transfer` |
| `bank1,9A78` | 45 | `bank1,9AD2` | `no-transfer` |
| `bank0,9C47` | 94 | `bank0,9CA6` | `no-transfer` |
| `bank0,3AD6` | 2,414 | `bank0,445E` | `not-code` |

`bank0,3AD6` is the one that is not a boundary slip at all: its listing is 26
bytes ending at 0x3AF0, and the next `bank0` export is 2,414 bytes later. That
window is a whole unexported region, and it is the `not-code` case below.

## The three verdicts

| verdict | pairs | what it means |
|---|---:|---|
| `boundary-cut` | **2** | a window transfer resolves to this pair's callee — the comment is right about a call the export stopped short of |
| `no-transfer` | **121** | this window carries no transfer to the named callee |
| `not-code` | **1** | the window's walk lands on a byte the MCS-51 map assigns to no instruction |

The three partition the 124 pairs, and the per-pair columns
(`at_next`, `neighbour_edge`, `db`, `unassigned`, `truncated`, `frame_onto`,
`frame_over`) are columns rather than a fourth bucket, so the split still adds
up. `--self-test` asserts the partition.

**`no-transfer` is not a verdict on the comment.** It says this window carries
no transfer to the named callee. The call may be somewhere the export does not
reach at all — most likely inside a function the graph has already booked, which
is the `neighbour_edge` column. 112 of the 124 windows carry **no transfer of
any kind**; the other **12** carry one that lands somewhere else. The two are
reported per pair and are not pooled, because "a transfer is there, but not the
one named" is a different reading from "no transfer at all".

### The boundary-cut pairs, read one by one

There are two. One is the issue's worked example; the other arrived with
issue #603's tranche and is the zero-gap case above, turning out to carry a
real transfer.

| citing row | listing ends | next entry | gap | window | instruction line | target |
|---|---|---|---:|---|---|---|
| `bank1,E57E` | 0xE580 | 0xE582 | 2 | `[0xE580, 0xE585)` | `0xE580  12 e5 d6  lcall 0xE5D6` | `bank1,E5D6` |
| `common,355E` | 0x355F | 0x3578 | 25 | `[0x355F, 0x357B)` | `0x3578  02 34 59  ljmp 0x3459` | `common,3459` |

**The oracle is committed and independent.** `ec/decompiled/bank1/E57E.asm` is a
single `c0 07` — `push 0x07` — so the listing ends at 0xE580;
`ec/annotations/bank-call-targets.csv:5766` reads
`0x16580,bank1,0xE580,lcall,0xE5D6,B,24,0,,,entry,entry`. The window's five
bytes are `12 e5 d6 d0 07`, and the walk reads them as the `lcall` plus the
matching `pop 0x07` at 0xE583.

**The 3 bytes of slack are load-bearing, and this case proves it.** `lcall` is
3 bytes, so a transfer starting at 0xE580 only completes by reading into
0xE582 — the byte the `bank1,E582` annotation row itself calls contested. A
window stopping at the boundary is 2 bytes and decodes **nothing at all**. The
tool's `--self-test` asserts both, so the slack cannot be quietly dropped.

**What the verdict is, and what it is not.** The row's own comment already reads
this way and already hedges it: *"The next two bytes are in no listing, but
`ec/annotations/bank-call-targets.csv` records an `lcall` to 0xE5D6 at 0xE580 … the
matching `POP` direct 0x07 sits at 0xE583 in the 0xE582 listing"*, and the
`bank1,E582` row adds that 0xE582 is *"both the target byte of that lcall and a
decodable `XCHD A,@R0`, so 0xE582 cannot be an instruction boundary at the same
time"*. The tool's verdict is **consistent with a comment that is already
careful**; it does not correct anything here.

**The second cut is the shape this file's lead section describes, resolving.**
`ec/decompiled/common/355E.asm` is a single `22` — one `ret` byte — so the
listing ends at 0x355F, and the next `common` entry is 25 bytes later at 0x3578.
The 28-byte window is `30 63 15 c2 63 78 ad e6 64 33 60 0c 12 35 f6 78 80 e6
70 04 78 a1 e6 22 22 02 34 59`, and it carries **two** transfers: `0x356B lcall
0x35f6`, which lands somewhere else, and `0x3578 ljmp 0x3459`, which lands on
this pair's callee. So the transfer the comment names is real, is 3 bytes of it
at the head of the neighbouring export, and is booked to that neighbour.

That is a different finding from the first cut, and it is worth keeping apart.
`0x3578` is itself exported — `thunk_FUN_CODE_3459` — so this is not bytes
stranded in a hole; it is a real function, a real `ljmp`, and a real target, with
the only question being **whose** call site the comment means. The row is
`shared_tail_return_of_3459_and_34c6`, #603's rank-1 tranche row, and the
neighbouring thunk is named for the very routine one of its two names is. The
tool does not adjudicate that: by this file's own limit below, `boundary-cut` is
evidence about framing, and the second cut is the case where the framing looks
right and the attribution is what a reader has to check.

Its sibling pair is the counter-example in the same window: `common,34C6` is
named by the same comment, and the same window's `ljmp` goes to 0x3459, not to
0x34C6 — a `no-transfer` beside a `boundary-cut`, out of one comment and one
window.

And a boundary cut is **not** proof that a function entry belongs at the site.
`bank0,D091` — the 40 bytes from 0xD14B that are a CODE table, not code —
decodes exactly as convincingly as code, and `citing-listing-evidence.md` is the
standing warning. `boundary-cut` is evidence about framing and about the
comment's accuracy.

### The not-code pair, and the criterion

`bank0,3AD6`'s window is 2,417 bytes, 0x3AF0 to the next `bank0` entry at
0x445E, and it opens:

```
3AF0  17 00 17 04 17 08 17 0c 11 06 11 02 ...
```

`0x17` and `0x16` are two of the **four byte values the MCS-51 map assigns to
no instruction** — `0x06`, `0x07`, `0x16` and `0x17`, the two gaps in the
0x00–0x1F row. Nine of that window's instruction starts land on one.

**The criterion is that byte test, and it is not a `db` count.** Two reasons, and
the second is the one that matters:

1. The precedent is `citation_callers.is_fill`, which tests bytes because the
   8051 map fixes them. The map also fixes which byte values are not opcodes, so
   a test on those is the same kind of statement.
2. `disasm8051`'s **mnemonic** table is partial by design, so a `db` count
   threshold would be a number fitted to this tree rather than a fact about the
   bytes. `verify_gap_text.verdict_of` already encodes the rule — *a `db` on
   either side is undecodable, never agree* — and this is that rule applied
   here: `not-code` is checked **first**, because a window that did not decode
   cannot support a verdict about a transfer read out of it.

The `db` count is reported as a column and the two counts are **not** the same
number: the `bank0,3AD6` window has `unassigned=9` and `db=74`. On this tree
the looser `db` form happens to select the same single pair, because no other
window in the population lands on an opcode the map assigns but the table does
not — `--self-test` asserts that, so the agreement is a measured fact and not an
assumption. It is still the wrong rule to ship: `0xD4` (`da A`) is assigned by the
8052 map and absent from the table, and a window landing on one would be
"unknown to this decoder", which is not the same answer as "not code".
`ec/tools/test_citation_gap_scan.py` asserts that the two rules disagree there.

**Stricter and looser forms, measured.** A stricter form — the whole window
unassigned, or an unbroken `0xFF` run, the `is_fill` precedent applied to the
window — selects **0** pairs: no window in the population is an `0xFF` run at
all, so the narrowest available byte test is degenerate here. The chosen form
selects **1**, and the looser `db` form also selects **1**. The `not-code`
count is therefore not sensitive to where the threshold is put, which is the
point of stating it: the rule is a fact about the map, and the one pair it
finds is the one whose window is visibly a data region.

**Is it #543's shape?** Issue #543 is about the one corroborated pair that is a
data table read as code, and this is the same failure mode one address over: the
`17 00 17 04 17 08 17 0c 11 06 11 02` run is the MCS-51 switch-table idiom
(`dec @r0` / `jmp @a+dptr` pairs), not a function head. This file **names that
and claims nothing further** — whether the whole 0x3AF0–0x445D region is a
dispatch table, a data table or unexported code is a reading question about
each address, and this tool's job is to identify the population and report
per-pair verdicts. It is left to the same follow-up #543 carries.

## What the split means for the ranking

**The issue's question: is any `cited_by == inbound` agreement being carried by
a call the graph attributes elsewhere?** Yes, and the answer is countable.

90 of the 124 ranked rows read `cited_by == inbound`; that is the
two-framings-agree check `call_graph.py --self-test` pins. **17 of those 90 are
the callee of some pair in this population**, and **15 of the 17** already have a
same-scope
transfer to them booked to a *different* function — the `neighbour_edge` column.
Over the whole population, **32 of the 124 pairs** (31 distinct callees) show
that signal: the graph is already attributing to a neighbour what the comment
attaches to the citing row.

The fifteen, with the attribution the graph currently has:

| callee | `cited_by`/`inbound` | graph's inbound is from | window gap |
|---|---|---|---:|
| `bank0,D5DB` | 1 / 1 | `bank0,D5DB` `ljmp` | 0 |
| `bank0,E033` | 1 / 1 | `bank0,DF78` `lcall` | 0 |
| `bank1,9FF0` | 1 / 1 | `bank1,9FC1` `lcall` | 0 |
| `bank1,A24E` | 1 / 1 | `bank1,AB64` `lcall` | 24 |
| `bank1,A8C5` | 1 / 1 | `bank1,A841` `ljmp` | 0 |
| `bank1,B33B` | 1 / 1 | `bank1,AD85` `ljmp` | 0 |
| `bank1,B43B` | 1 / 1 | `bank1,B33B` `ljmp` | 0 |
| `bank1,DEC4` | 2 / 2 | `bank1,9A41` `lcall` | 45 |
| `common,30DF` | 1 / 1 | `common,2DE3` `lcall` | 0 |
| `common,3459` | 1 / 1 | `common,3578` `ljmp` | 25 |
| `common,34C6` | 1 / 1 | `common,3555` `ljmp` | 25 |
| `common,3A0D` | 1 / 1 | `common,2E9C` `ljmp` | 0 |
| `common,492D` | 1 / 1 | `common,4825` `ljmp` | 0 |
| `common,4A77` | 2 / 2 | `common,43A5` `lcall` | 0 |
| `common,5A5A` | 1 / 1 | `common,0046` `lcall` | 0 |

**The other 73 `cited_by == inbound` agreements are not affected.** The two
population callees in that set without the signal — `common,451A` and `pd,06EA`
— are rows where the citing listing does carry the transfer, so
the two columns are counting the same call sites. That is the check working, and
it is the majority case.

**One `boundary-cut` is the ranking's rank 3.** `bank1,E5D6` reads
**`cited_by=3` / `inbound=1`**, with `citing` = `bank1:E57E bank1:E582
bank1:E5A7`. Three comments name it; one transfer reaches it; and that one
transfer is the `bank1,E5A7` `lcall`, **not** the boundary-cut `lcall` at 0xE580
in the `bank1,E57E` gap. So this row of the work list is, in this one case,
exactly the failure the issue describes: `cited_by` and `inbound` are counting
different call sites, and the call the comment names is booked nowhere.

**The other `boundary-cut` is a different shape, and it is lower in the
ranking.** `common,3459` reads `cited_by=1` / `inbound=1` and ranks 92 of 124;
its single inbound is the `common,3578` `ljmp` — the transfer the window above
reads, sitting at the head of the neighbouring export. So this one is *not* the
issue's failure: the two columns agree, the transfer is real, and the open
question is only which row of the work list the call site belongs to. It is in
the table above for the same reason the other fourteen are — the graph is
already booking a transfer under a name other than the citing row's, and the
comment is what says otherwise.

**What this does not move.** `call_graph.py` is not changed by this tool, and
`ec/annotations/call-graph-callees.csv` is **byte-identical** before and after —
`python3 ec/tools/call_graph.py --check` reports 1,841 rows and no diff.
Crediting a boundary-cut edge would move `cited_by`, `inbound`, `callers` and
the ranking's order, and the `bank0,D091` wrong-credit precedent is the reason
that is a separate change with its own re-measurement. The issue asks for a
statement about the ranking, and this is the statement.

**Does any recovered edge want a seed row?** One candidate, and it is the one
`ghidra-functions.csv` already argues about against itself. Seeding a function
entry for the `lcall` at 0xE580 would mean adding a row to
`ec/annotations/ghidra-functions.csv` between 0xE57E and 0xE582 — and the
`bank1,E582` row says 0xE582's own first instruction is **contested** for
exactly that reason, so the seed is not merely unproven, it is the other half of
an argument already in the file. That is a `ghidra-functions.csv` edit and a
`--mode rebuild-project` re-export, and CLAUDE.md is explicit that two branches
which both rebuild the project cannot merge. It is listed for a follow-up issue,
not done here.

## The population: 99 rows, 124 pairs

The tool rebuilds the population with the **same predicate**
`docs/findings/citing-listing-evidence.md` used — a citing row whose listing
yields nothing from `citation_callers.transfers()`, minus the rows the
`is_fill` veto already refuses — over the same three buckets `citations()`
partitions, and **fails `--self-test` if the count is not 99 / 124**.

**The predicate is a transfer-line test and it has to be.** Keying instead on
the *resolved* target set — a listing whose transfers resolve to nothing — gives
**101 rows / 126 pairs**, and the two extra rows are `bank1,8802` and
`bank1,E954`, each of which carries a transfer line whose target resolves to no
index row. The two predicates cannot be used interchangeably, and the tool
prints both so the choice is not implicit.

**The unit is the pair, so there are more pairs than rows.** The gate enumerates
`(callee, citer)`, so one comment naming three callees is three pairs over one
row. Both numbers are printed and both are pinned, so a reader comparing against
the 100 the previous write-up measured is not looking at a contradiction.

**Correction to the plan's figures, and then a second correction.** The plan
stage measured **100 rows / 114 pairs**, and the issue's own text says 100. The
predicate is unchanged and the tool is the one the plan specified. Two merges
have moved the figure since, and both are recorded here rather than one being
absorbed into the other:

1. **105 / 123** — five more comments merged into
   `ec/annotations/ghidra-functions.csv` since the plan ran (#632's twelve
   retyped rows, #633's, and the other tranche work in the same window).
2. **99 / 124** — issue #603's 37-row common-runtime tranche (PR #620). This one
   moves *both* ways, which is why it is stated rather than presented as a
   drift. The tranche re-derived `ec/annotations/call-graph-callees.csv`, and its
   version no longer lists twelve rows as citing anything — eleven `pd` rows
   (`10BC`, `34D6`, `357E`, `37AE`, `39AC`, `98A1`, `98A4`, `A681`, `ACCE`,
   `ACE1`, `AD3C`) and `common,05E6` — so those leave the population. Six rows
   join it: `common,2B6C`, `355E`, `3BDD`, `4368`, `4AFB` and `5A55` are tranche
   listings that, newly carrying a comment, name a callee over a listing that
   transfers to nothing — which is the predicate. A new comment on a function
   that reaches nothing is exactly a population row.

`EXPECT_ROWS`/`EXPECT_PAIRS` in the tool are pinned to **this** tree, and
that is the number every figure in this file uses. Corrected in place rather
than carried forward, for the reason `citing-listing-evidence.md` carries two
corrections of its own.

**`common` citers, and the one consequence of reading "that program" as the
citing row's own scope.** 10 of the 99 rows are `common` citers (`common,0EF3`,
`2B6C`, `355E`, `3B4E`, `3BDD`, `3F9D`, `4368`, `4A76`, `4AFB`, `5A55` — six of
them the tranche's own).
A `common` function is exported once for both banks, so at runtime the executing
bank's boundary is the one that exists and a nearer bank-scope entry can. The
tool counts and reports this rather than silently picking a scope — and on this
tree the count is **0**.

**That 0 no longer has the reason it used to, and the difference matters.** When
this file was first written the count was 0 *because* every `common` citer was
zero-gap, so the common boundary was trivially the nearest one. Nine of the ten
still are; `common,355E` is not, and its 25-byte gap is where the second
`boundary-cut` above comes from. So the count is 0 on this tree for a different
and weaker reason — the one non-zero-gap `common` citer happens to have no
bank-scope entry inside its gap — and `--self-test` now pins the 9-and-one split
by name rather than asserting a blanket that no longer holds. The branch is
still there for a re-export that changes it.

## The neighbouring open issues, and what is claimed for none of them

| issue | overlap with this population | claimed here |
|---|---|---|
| #456, real entries for the tranche's boundary rows | 4 of the six rows `call-graph-unresolved.md`'s table lists are population citers: `bank0,D2BE`, `bank0,9C47`, `common,3B4E`, `common,4A76` | nothing. All four are zero-gap except `bank0,9C47` (94 bytes), and the tool reports what the window carries; it does not re-adjudicate whether an entry belongs there. |
| #522, the nine `0x1C01`–`0x1C03` store sites in unexported gaps | **none** — no `0x1C01`, `0x1C02` or `0x1C03` row is in the population | nothing |
| #465, the 48-forwarder family | 6 population citers are `type=forwarder` in `index.csv`: `bank0,9C47`, `bank0,D2BE`, `bank1,9FCA`, `bank1,A8DA`, `bank1,E57E`, `common,355E` | nothing. Named so a reader of either write-up knows the sets overlap. The sixth is #603's rank-1 tranche row, and it is the second `boundary-cut` above — a one-`ret` shared tail whose only reaching transfer is a neighbouring thunk's `ljmp`. |
| #543, the corroborated pair that is a data table read as code | the one `not-code` window (`bank0,3AD6`) is the same failure mode one address over, and its head is a switch table | that it is the same *shape*. Not which it is — see above |

## What the tool cannot decide

- **A window is a slice, not a function.** For the 86 zero-gap rows the window
  is the next export's first 3 bytes plus a linear walk into it. A `no-transfer`
  there says the neighbour's head does not call the named callee; it says
  nothing about the neighbour's body, which is the citing row's own listing in
  most cases and is read by the tools that already have it.
- **A linear walk is not a parser.** It does not follow branches, does not
  recover function boundaries and cannot tell code from a jump table — the
  `bank0,3AD6` window is the case. `frame_onto`/`frame_over` carry
  `disasm8051.converges_from` so a reader can see how many nearby anchors decode
  onto the window's first byte, but that is evidence about framing, not proof of
  it.
- **The window is 3 bytes past the boundary and no further.** A transfer starting
  4 or more bytes into the next export is in that export's own listing, not in
  the gap, and is the graph's business rather than this tool's.
- **No hardware, no Windows, no live observation.** Nothing here needs a run at
  the machine, so nothing is deferred to a human who has one.
- **No register `status:` changed.** `ec/annotations/registers.yaml` and
  `ec/ghidra/xdata-symbols.csv` are untouched; this tool reads neither.
- **`disasm8051.decode()` is not called in a loop, and that is a workaround.**
  `decode()` evaluates `OPCODE_LEN[d[i]]` *before* its own `i + n > len(d)` guard,
  so a window whose last byte is a 1-byte opcode raises `IndexError` — and a gap
  window ends on one routinely (`bank0,B5D2` is a bare `ret`). `walk()` does the
  same linear decode over the same committed tables and stops when the
  instruction does not fit, so there is no second opcode or mnemonic table here
  to keep in step. **The one-line upstream fix (`if i >= len(d): return` in
  `decode()`) is recorded as a follow-up rather than done here**, to keep this a
  new-file change and off a file another agent may be touching. The self-test
  asserts that `decode()` still raises, so if it is fixed the guard's reason
  disappears loudly rather than silently.
- **`call_graph.py` is not changed, and neither is its table.**
  `ec/annotations/call-graph-callees.csv` is byte-identical across this change,
  which is the proof that no number in the ranking moved.

## Re-deriving

Three commands, run from the repository root. The first is the census; the
second is `--check`, which recomputes every per-pair verdict from the current
bytes, the current listings and the current `disasm8051.py` tables; the third
re-derives the ranking consequence from the committed
`call-graph-callees.csv` without going through the tool.

```sh
python3 ec/tools/citation_gap_scan.py
```

```
citation_gap_scan.py -- the bytes a function boundary cut out of a citing listing

  citing rows in the population                            99
    (callee, citer) pairs                                 124
    pairs whose citing row is one of those rows            99
    the resolved-target predicate instead: rows           101
    ... and its pairs                                     126

  citers by scope: bank0 63, bank1 22, common 10, pd 4      4
    of those, a `common` citer                             10
      with a bank-scope entry nearer than the common one      0

  window, zero bytes (the next export starts where this one stops)    110
    rows                                                   86
    window, non-zero                                       14
  window carries some transfer at all                      12
    carries none                                          112

  verdict boundary-cut                                      2
  verdict no-transfer                                     121
  verdict not-code                                          1
    the three verdicts add up to the pair count           124

  pairs whose callee is already reached from the same scope by another function     32
  windows whose linear walk did not tile the buffer        28
    windows with a `db` at an instruction start             1
    windows landing on a map-unassigned byte                1
```

```sh
python3 ec/tools/citation_gap_scan.py --check && python3 ec/tools/citation_gap_scan.py --self-test
```

```
  gap citation scan: 124 row(s); verdicts 2 boundary-cut, 121 no-transfer, 1 not-code
  all checks passed
  ... 47 assertions, all passed
```

```sh
python3 -c "
import csv, sys
sys.path.insert(0,'ec/tools')
import citation_gap_scan as G
ctx = G.context(); live = G.classify(ctx)
callees = {(r['scope'], r['addr']): r for r in
           csv.DictReader(open('ec/annotations/call-graph-callees.csv', newline=''), strict=True)}
nb = [r for r in live if r['neighbour_edge']]
agree = [r for r in nb if int(callees[(r['callee_scope'], r['callee_addr'])]['cited_by'])
         == int(callees[(r['callee_scope'], r['callee_addr'])]['inbound'])]
ranked = [r for r in csv.DictReader(open('ec/annotations/call-graph-callees.csv', newline=''), strict=True) if int(r['cited_by'])]
eq = [r for r in ranked if r['cited_by'] == r['inbound']]
print('neighbour-edge pairs', len(nb), '| of those cited_by == inbound', len(agree),
      '| ranked rows', len(ranked), '| cited_by == inbound', len(eq))
"
```

```
neighbour-edge pairs 32 | of those cited_by == inbound 15 | ranked rows 124 | cited_by == inbound 90
```

**The tests that hold this in place.**
`python3 ec/tools/citation_gap_scan.py --self-test` pins the population, the
three verdicts, the `E57E` cut, the zero-gap shape, the overrun guard, the
`not-code` criterion's byte test and the two image scopes, from oracles stated
in the committed listings, `bank-call-targets.csv` and the 8051 map — never
recorded from the tool. `--check` recomputes all 124 rows and fails on any byte
difference. `ec/tools/test_citation_gap_scan.py` covers the pieces on their own:
the window arithmetic including the slack, the overrun guard, the byte criterion
against the `db` form, the scope-dependent boundary, and `--check` rejecting a
CRLF table whose rows parse equal. All three run from
`.github/scripts/agent-gates.sh`; the unit suite also runs from
`bash tools/run-tests.sh`.
