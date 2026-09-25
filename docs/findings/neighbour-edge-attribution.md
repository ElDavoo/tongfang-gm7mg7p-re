# Does the kept citation name the neighbour's call site? Fifteen rows and two, decided (issue #681)

`ec/annotations/call-graph.md` carries the limit — `cited_by` counts comments,
`inbound` counts transfers, so their agreeing is a two-framings-agree check and
not a proof they count the same thing — and
`docs/findings/citation-gap-scan.md` gives the 15-row table behind it. What
neither did was decide, for any of the 15, whether the citing comment names the
same call site the graph booked to a *neighbour*. **This file decides all of
them, and the two population callees with no `neighbour_edge` signal at all, one
row each.**

**The split is 9 / 6 of the 15 and 2 / 0 of the two** — and the mechanical test
that produces the 9 / 6 turns out to be *exactly* predictive of the verdict on
this tree, which is the result worth carrying forward.

**Nothing here is a behavioural claim.** No register `status:` changed, no
annotation CSV row, no name, no re-export, no hardware and no Windows. This is a
text measurement over committed listings, committed tables and the committed
image, and every row below cites the comment file it reads, the `neighbour_edge`
value it compares against, and a site address from a committed table or listing.

## The unit is the kept citation, not the population pair

The population is keyed on `(callee, population-citer)` pairs, and the issue's
table is written that way. But `cited_by` is a count of the comments
`call_graph.citations()` **keeps**, and for **7 of the 15** the kept citing row
is *not* the row the population pair names — the population pair names a
*rejected* or *undecided* mention that contributes nothing to `cited_by`.
Adjudicating the population pair's comment would answer a question that does not
bear on the two columns.

*(Correction to this change's plan, which put that count at 11. It is 7; the
complement — the 8 whose population pair **is** a kept citation — is the number
the plan's phrasing was reaching for. The split, the verdicts and every site
address below are unaffected; §[Re-deriving](#re-deriving) prints both counts.)*

So for each of the 15 the reading runs on the callee's `citing` list from
`ec/annotations/call-graph-callees.csv`: for **each** address in it, read the
comment in `ec/annotations/ghidra-functions.csv` and ask whether it names the
neighbour's site or a different one. The comment still has to be read — a
comment can name the neighbour *function* without naming the site the graph
booked — but which comments are in scope is read off the committed table rather
than guessed.

The 73 other agreements, and the 17 neighbour-edge pairs outside the 15, are
out of scope here, as the issue scopes them.

## The first step is mechanical, and it is exactly predictive

*Is the `neighbour_edge` address in the callee's `citing` list?* That is one
comparison over two committed CSVs, and it gives **9 yes / 6 no**. It is not
itself the verdict — a `neighbour_edge` that is also a kept citer could still be
a comment naming a different site — so the comment is read for all 15 either
way. On this tree the two partitions come out **identical**: all 6 rows where
the neighbour is *not* a kept citer name a different site, and all 9 where it
is, do not.

That is a measured fact about 15 rows, not a rule, and 15 is a small
population. It is recorded because it is the cheapest available screen and
because it was not the expected answer: the two counts are independent
derivations from different files, and their agreement is what a reader should
check this file by.

## The verdict table, 17 rows

`neighbour` is the `neighbour_edge` column verbatim; the site is the transfer
`bank-call-targets.csv` records for it, which is where the graph books it. Where
the verdict is **different**, the last column gives the address the comment
names instead.

| callee | kept citing row | `citing` list | neighbour | graph's site | verdict | the comment names instead |
|---|---|---|---|---|---|---|
| `bank0,D5DB` | `bank0,D5D4` | `D5D4` | `bank0:D5DB ljmp` | 0xD662, inside `D5DB` itself | **different** | the `sjmp 0xd607` at **0xD5D9** (`D5D4.asm:9`) |
| `bank0,E033` | `bank0,DF78` | `DF78` | `bank0:DF78 lcall` | 0xDF81 | agrees | — |
| `bank1,9FF0` | `bank1,9FC1` | `9FC1` | `bank1:9FC1 lcall` | 0x9FC7 | agrees | — |
| `bank1,A24E` | `bank1,AB64` | `AB64` | `bank1:AB64 lcall` | 0xAB6A | agrees | — |
| `bank1,A8C5` | `bank1,A841` | `A841` | `bank1:A841 ljmp` | 0xA85A | agrees | — |
| `bank1,B33B` | `bank1,AD85` | `AD85` | `bank1:AD85 ljmp` | 0xAD85 | agrees | — |
| `bank1,B43B` | `bank1,B415` | `B415` | `bank1:B33B ljmp` | 0xB377, booked to `B33B` | **different** | the `jc 0xb43b` at **0xB415** (`B415.asm:7`) |
| `bank1,DEC4` | `bank1,9A41`, `bank1,9A78` | `9A41 9A78` | `bank1:9A41 lcall` | 0x9A68, and 0xDEBF booked to `DEA5` | agrees at 0x9A68; second comment names the function only | — |
| `common,30DF` | `common,2DE3` | `2DE3` | `common:2DE3 lcall` | 0x2DE3 | agrees | — |
| `common,3459` | `common,355E` | `355E` | `common:3578 ljmp` | 0x3578, the neighbouring thunk's head | **different** | 0x3459 as a *caller*, not a site |
| `common,34C6` | `common,355E` | `355E` | `common:3555 ljmp` | 0x355B, booked to `3555` | **different** | 0x34C6 as a *caller*, not a site |
| `common,3A0D` | `common,2E9C` | `2E9C` | `common:2E9C ljmp` | 0x2F1A | agrees | — |
| `common,492D` | `common,4A76` | `4A76` | `common:4825 ljmp` | 0x482E, booked to `4825` | **different** | 0x485B, 0x4868 and **0x492D** as `lcall` sites |
| `common,4A77` | `common,43A5`, `common,4A76` | `43A5 4A76` | `common:43A5 lcall` | 0x4435 and 0x4454, both booked to `43A5` | agrees at `43A5`; second comment names the function only | — |
| `common,5A5A` | `common,5A55` | `5A55` | `common:0046 lcall` | 0x0049, booked to `0046` | **different** | 0x5A5A as the tail of a data run |
| `common,451A` | `bank0,445E` | `bank0:445E` | *(no signal)* | 0x447E (`445E.asm:27`) | agrees | — |
| `pd,06EA` | `pd,88BE`, `pd,D83D` | `88BE D83D` | *(no signal)* | 0x8937 (`pd/88BE.asm:76`), 0xD86B (`pd/D83D.asm:38`) | agrees | — |

### The six that name a different site

The claim to state, with the address each comment names instead. All six were
re-read against the committed inputs.

- **`bank0,D5DB`** — `write_33_to_1501_join_loop_d5db` is three instructions
  ending `D5D9 sjmp 0xd607`, and the comment says so: *"jumps into the middle of
  the 0xD5DB loop at 0xD607"*. The graph's site is the `ljmp 0xD5DB` at
  **0xD662**, which is 91 bytes further on and inside `D5DB`'s own listing.
  This is also the one row where **the neighbour is the callee itself** — a
  search of every committed `.asm` listing in every scope finds exactly one
  transfer to 0xD5DB, and it is that self-`ljmp` — so `neighbour_edge` and
  `neighbour` are the same row here, which the write-up's table renders as an
  ordinary neighbour edge.
- **`bank1,B43B`** — `bump_counter_054d` opens `B415 jc 0xb43b`, and the
  comment reads *"if it is set the code jumps to 0xB43B"*. The graph's site is
  the `ljmp 0xb43b` at **0xB377**, which `bank1/B33B.asm:34` shows booked to
  `B33B`. The comment's site is the listing's own first instruction.
- **`common,3459`** — the `shared_tail_return_of_3459_and_34c6` comment names
  0x3459 and 0x34C6 as **the two callers** reaching the shared `ret`, which is a
  *source* role: the sites it implies are inside 0x3459's own body, one of its
  eleven `ljmp`s to 0x355E. The graph's site is the `ljmp 0x3459` at **0x3578**
  — the head of the neighbouring thunk `thunk_FUN_CODE_3459`, and the
  `boundary-cut` row `citation-gap-scan.md` already read. Same comment, and the
  same reading, decide **`common,34C6`**: the graph books the `ljmp 0x34c6` at
  **0x355B**, three bytes below the `ret`, inside `common,3555`.
- **`common,492D`** — `dptr_4900_plus_15x_r1` reads 0x492D as one of **three
  `lcall` sites** reaching 0x492D (*"at 0x485B, 0x4868 and 0x492D each is
  immediately followed by a separate lcall 0x4A4D"*), and says five reach it.
  The graph books exactly one, an `ljmp 0x492d` at **0x482E** inside
  `common,4825`. Different address *and* different transfer form.
- **`common,5A5A`** — the strongest of the six, because the comment does not
  merely name a different site, it declines the one the graph booked.
  `table_bytes_disassembled_as_code_5a55` reads 0x5A5A as *"the tail of a
  data run"* and states plainly that *"whether any code at all is at 0x5A55 is
  not established"*, with a `reti` and not a `ret` at 0x5A62. The graph books
  a real `lcall 0x5a5a` at **0x0049**, inside `common,0046`.

### The seven that agree, one-for-one

Each sits on the very function the graph books the edge to, which is the
one-for-one agreement; how far the comment goes in naming the *site* rather
than the callee varies, and the variation is worth recording rather than
flattened. In four steps:

- **`common,3A0D` names the site outright** — *"then tail-jumps to 0x3A0D at
  0x2F1A"*, and the graph's site is 0x2F1A (`common/2E9C.asm:73`). This is the
  only row in the whole 17 where comment and graph cite the same address
  explicitly, and it is an agreement no re-framing can dissolve.
- **`bank1,9FF0` pins the span containing it** — *"The three lcalls span
  0x9FC1-0x9FC9"*, and the graph's site 0x9FC7 is inside that span.
- **`bank0,E033`**, **`bank1,A24E`** and **`bank1,A8C5`** name the callee as a
  call or tail jump made from the citing listing's own bytes, and the graph
  books exactly that listing. The agreement is over the listing rather than over
  an address, which is all the more defensible: a site inside a listing cannot
  be booked to a different listing without the listing itself moving.
- **`bank1,B33B`** and **`common,30DF`** are the tightest of all, where the
  site *is* the citing listing's first instruction: `forwarder_to_b33b` reads
  *"Three bytes: ljmp 0xB33B"* over a listing that is exactly those three bytes
  at 0xAD85, and `mask_1106_then_clear_18_34` opens `2DE3 lcall 0x30df`.

## The two shapes the write-up's table does not distinguish

Two of the nine carry a **second** kept citation whose comment names no call
site at all — it either contrasts the neighbour's call against its own, or
names the callee as a function boundary rather than a call. Both belong in the
table above rather than in a footnote, and both are also the two rows where
`cited_by` and `inbound` agree in **number** while naming **different sets of
listings** — a shape the two-column summary cannot show at all.

- **`bank1,DEC4` — a contrast mention.** `cited_by=2`, `inbound=2`. The two
  citations are `bank1,9A41` (*"it calls 0xDEC4 if bit 0 of XDATA 0x0497 is
  set"*) and `bank1,9A78`, whose comment names 9A41's call and **explicitly
  denies its own**: *"The bit-3-set path calls no subroutine here, where 0x9A41
  calls 0xDEC4"*. The graph agrees with the denial — it books **no** edge to
  `9A78`, and `9A78`'s own listing carries no transfer to 0xDEC4. The
  neighbour's site is 0x9A68 (`9A41.asm:27`), inside the listing 9A41's comment
  is attached to, and that is the one-for-one agreement. The second inbound is
  the `lcall 0xdec4` at **0xDEBF** in `bank1,DEA5.asm:22`, and `DEA5` carries
  no comment. So the two columns agree in number and the **comment set and the
  transfer set are not the same**: `{9A41, 9A78}` against `{9A41, DEA5}`.

  *(Correction to this change's plan, which read this row as the graph booking
  `9A78` as a caller. It does not: `call_graph.scan` books `DEA5`. The contrast
  the comment draws is real, and the graph sides with it.)*

- **`common,4A77` — a framing mention.** `cited_by=2`, `inbound=2`. The two
  citations are `common,43A5` (*"finishing by passing R6 to 0x4A77"*) and
  `common,4A76`, whose comment names 0x4A77 as a **function boundary** rather
  than a call site: *"Ghidra's function here is the single mov A,R1 and the
  twelve bytes after it belong to a second function"*. Both transfers are in
  `43A5` — `lcall 0x4a77` at **0x4435** and **0x4454**
  (`common/43A5.asm:89,103`) — and `4A76`'s own listing carries no transfer at
  all, so the framing mention names no site and books none. Again the counts
  agree while the sets do not: `{43A5, 4A76}` against `{43A5, 43A5}`.

## A third shape: the population pair is a rejected data-frame mention

For three of the seven — `bank1,A8C5`, `common,30DF`, `common,3A0D` — the
population pair is a **rejected** data-frame mention, so the `neighbour_edge`
signal cannot be the failure the headline reads as. The measured reasons are
`data-marker:register` (`bank1,A8DA`) and `data-marker:copy` for both `common`
rows, and these three are precisely the rows where a reader following the
population table rather than the `citing` column would adjudicate a comment
that contributes nothing to `cited_by`.

## The two population callees, and the correction they need

`common,451A` and `pd,06EA` are the two agreements among the 90 that carry no
`neighbour_edge` signal. Both land on **agree**, one-for-one:

- **`common,451A`** — one kept comment, on `bank0,445E`
  (`stage_and_commit_0a56_block`), against the `ljmp 0x451a` at **0x447E**
  (`bank0/445E.asm:27`), inside that very listing. The comment reads *"branches
  to 0x451A when bit 7 of 0x0A57 is clear"*, which is the listing's own
  `jb 0xe7, 0x4481` / `ljmp 0x451a` pair.
- **`pd,06EA`** — two kept comments, on `pd,88BE` and `pd,D83D`, against the
  `lcall 0x06ea` at **0x8937** (`pd/88BE.asm:76`) and **0xD86B**
  (`pd/D83D.asm:38`). Each comment names 0x06EA as a call from its own listing
  (*"before calling 0x05A6 and 0x06EA"*; *"then 0x05A6 with R0 = 0x3F … and
  0x06EA"*).

`ec/annotations/bank-call-targets.csv` carries only the `common`, `bank0` and
`bank1` regions, so the two `pd` site addresses come from the committed `pd`
listings. That substitution is stated here rather than made silently.

`docs/findings/citation-gap-scan.md` §What the split means for the ranking
concludes for these two that *"rows where the citing listing does carry the
transfer, so the two columns are counting the same call sites"*. **That
conclusion stands, and it now has a per-row reading behind it.** Its *reason*
is corrected in place beside the original: the sentence is true of the **kept**
citing row, and not of the population pair the row is about. Each population
pair is a *rejected* data-frame mention — `common,4AFB` → `data-marker:copy`,
`bank0,D045` → `data-marker:clears` — that contributes nothing to `cited_by`,
and the population pair's own citing listing carries **no** transfer at all
(`grep -cE "^[0-9A-F]{4} .*(lcall|ljmp|ajmp|acall)"` returns 0 for both
`common/4AFB.asm` and `bank0/D045.asm`), which is the predicate that put the row
in the population. So the check is working, for a better reason than the one
written down.

## What a recovered edge would need before it is credited

**Nothing here credits or retracts an edge**, and that is deliberate rather than
deferred. A recovered edge is a change to `call_graph.py`'s input, so it moves
`cited_by`, `inbound`, `callers` and the ranking's order, and it would need:

1. **An independent re-measurement of the site that does not go through the
   window walk.** The walk in `citation_gap_scan.py` is a linear decode from a
   listing's end, and a re-measurement that reused it would be the same
   evidence counted twice. `bank-call-targets.csv` or the committed listing is
   the independent source.
2. **A boundary that survives a re-decode.** `bank0,D091` is the standing
   precedent: 40 bytes of CODE table at 0xD14B that decode exactly as
   convincingly as code
   ([`citing-listing-evidence.md`](citing-listing-evidence.md) §What the rule
   still cannot decide; open as #543). A site that only decodes as a transfer
   under one framing is evidence about framing.
3. **Its own `call_graph.py --check`, before and after.** The proof that this
   change moved no number is that the 1,841-row
   `ec/annotations/call-graph-callees.csv` is byte-identical; a change that
   credited an edge would move it, and that run is what would show it.

**A seed row would additionally need a `--mode rebuild-project` re-export** — a
`ghidra-functions.csv` row for the recovered entry, which is the other half of
an argument `bank1,E582`'s row is already having about 0xE582 being both a
target byte and a decodable `XCHD A,@R0`. Two branches that both rebuild the
EC project cannot merge, so that is a separate change with its own branch, not a
line to add here.

**The one candidate stays uncredited.** `bank1,E5D6` is the ranking's rank 3 and
the one pair where a `boundary-cut` reads as a recovered call (`lcall 0xE5D6` at
0xE580). It is not in the 15 — it is not an agreement, reading
`cited_by=3` / `inbound=1` — and the two columns disagreeing there is a
different question from the one this file answers. `citation-gap-scan.md`
already names the seed row it would need and why that row is the other half of
an open argument; nothing here changes that.

## What this does not move

No CSV is edited. `ec/annotations/ghidra-functions.csv`,
`ec/annotations/call-graph-callees.csv`, `ec/annotations/registers.yaml`,
`ec/ghidra/gap-citation-scan.csv` and `ec/ghidra/xdata-symbols.csv` are all
untouched, which is also why no re-export is needed and why none of the three
Ghidra failure modes apply. No new tool and no new test file: registering a gate
in `.github/scripts/agent-gates.sh` is an upstream `agent-pipeline` change, and
this change does not need one.

The 15 and the 90 are properties of the committed CSVs, and the derivation below
reproduces both without moving either. What moves is the **reading** of the 15,
and that is what `ec/annotations/call-graph.md` §"What is left, and the two
limits a reader must carry" now points here for.

## Re-deriving

One command, from the repository root, over the two committed CSVs. It
reproduces 124 pairs, 32 carrying a `neighbour_edge`, 15 of those on a
`cited_by == inbound` row, 90 agreements overall, the 9 / 6 split, and the 7 / 8
population-pair count of §The unit is the kept citation.

```sh
python3 -c "
import csv
rows=list(csv.DictReader(open('ec/ghidra/gap-citation-scan.csv',newline=''),strict=True))
cal={(r['scope'],r['addr']):r for r in csv.DictReader(open('ec/annotations/call-graph-callees.csv',newline=''),strict=True)}
nb=[r for r in rows if r['neighbour_edge']]
ag=[r for r in nb if cal[(r['callee_scope'],r['callee_addr'])]['cited_by']==cal[(r['callee_scope'],r['callee_addr'])]['inbound']]
rk=[r for r in cal.values() if int(r['cited_by'])]
def key(r):
    a,_=r['neighbour_edge'].split(); return tuple(a.split(':'))
def citing(r):
    return {tuple(x.split(':')) for x in cal[(r['callee_scope'],r['callee_addr'])]['citing'].split()}
print('pairs',len(rows),'| neighbour_edge',len(nb),'| agreements among them',len(ag))
print('ranked',len(rk),'| cited_by==inbound overall',len([r for r in rk if r['cited_by']==r['inbound']]))
print('neighbour IS in citing',len([r for r in ag if key(r) in citing(r)]),
      '| is NOT',len([r for r in ag if key(r) not in citing(r)]))
pop=lambda r:(r['citer_scope'],r['citer_addr'])
print('population pair IS a kept citation',len([r for r in ag if pop(r) in citing(r)]),
      '| is NOT',len([r for r in ag if pop(r) not in citing(r)]))
"
```

```
pairs 124 | neighbour_edge 32 | agreements among them 15
ranked 124 | cited_by==inbound overall 90
neighbour IS in citing 9 | is NOT 6
population pair IS a kept citation 8 | is NOT 7
```

**The site addresses in the table** are the `bank-call-targets.csv` rows for each
neighbour, cross-read against the listing the graph books them to. Each pair of
lines below is the comment's site and the graph's site for one row:

```sh
grep -n "^D5D9\|^D662" ec/decompiled/bank0/D5D4.asm ec/decompiled/bank0/D5DB.asm
grep -n "^B415\|^B377"      ec/decompiled/bank1/B415.asm ec/decompiled/bank1/B33B.asm
grep -n "^355B"             ec/decompiled/common/3555.asm
grep -n "^3578"             ec/decompiled/common/3578.asm
grep -n "^482E"             ec/decompiled/common/4825.asm
grep -n "^0049"             ec/decompiled/common/0046.asm
grep -n "^4435\|^4454"      ec/decompiled/common/43A5.asm
grep -n "^9A68"             ec/decompiled/bank1/9A41.asm
grep -n "^DEBF"             ec/decompiled/bank1/DEA5.asm
grep -n "^447E"             ec/decompiled/bank0/445E.asm
grep -n "^8937"             ec/decompiled/pd/88BE.asm
grep -n "^D86B"             ec/decompiled/pd/D83D.asm
```

**The four listings a claim says carry no transfer to the callee** — the two
population pairs' citers, and the two second comments' own listings:

```sh
grep -cE "^[0-9A-F]{4} .*(lcall|ljmp|ajmp|acall)" \
  ec/decompiled/common/4AFB.asm ec/decompiled/bank0/D045.asm \
  ec/decompiled/bank1/9A78.asm  ec/decompiled/common/4A76.asm
```

```
ec/decompiled/common/4AFB.asm:0
ec/decompiled/bank0/D045.asm:0
ec/decompiled/bank1/9A78.asm:0
ec/decompiled/common/4A76.asm:0
```

**The two rejected population pairs** and their reasons come from the gate that
produced them:

```sh
python3 -c "
import sys; sys.path.insert(0,'ec/tools')
import call_graph as cg, citation_gap_scan as G
ctx=G.context()
_kept,rejected,_undecided,_lk = cg.citations(ctx.index, ctx.listings)
for c in rejected:
    if c.callee in {('common','451A'),('pd','06EA')}:
        print(c.callee, c.citer, c.reasons, c.verdicts)
"
```

```
('pd', '06EA') ('bank0', 'CA53') ('data-marker:counter',) ('data', 'undecided')
('pd', '06EA') ('bank0', 'CDE4') ('data-marker:zeroes',) ('data', 'undecided')
('pd', '06EA') ('bank0', 'CE37') ('data-marker:zeroes',) ('data', 'undecided')
('pd', '06EA') ('bank0', 'D045') ('data-marker:clears',) ('data',)
('common', '451A') ('common', '4AFB') ('data-marker:copy',) ('data',)
```

The two **population pairs** are the last row and the fourth: `bank0,D045` for
`pd,06EA` and `common,4AFB` for `common,451A`. The other three are worth seeing
because they say what `pd,06EA` attracts: four `bank0` comments mention
0x06EA, and in all four it is an **XDATA** counter — `tick_06ea_against_period_in_0a56`
at `bank0,CA53` *"adds 0x0001 to the big-endian 16-bit counter at 0x06EA/0x06EB"*,
`inc_06e7_clear_06ea_eb_read_06e8` at `bank0,D045` *"clears 0x06EA and 0x06EB to
zero"* — not the `pd` CODE row of the same address. The data markers are the
guard working rather than a coincidence of framing: the
program-versus-address conflation is the subject of
[`pd-common-address-attribution.md`](pd-common-address-attribution.md), and
`citation_frames.program_reason` deliberately decides only the one direction it
can (`pd` comment, non-`pd` row), so here the data marker is what rejects all
four. None contributes to `cited_by`.

**The three gates that hold the numbers still where they were:**

```sh
python3 ec/tools/citation_gap_scan.py --check
python3 ec/tools/citation_gap_scan.py --self-test
python3 ec/tools/call_graph.py --check
```

```
  gap citation scan: 124 row(s); verdicts 2 boundary-cut, 121 no-transfer, 1 not-code
  all checks passed
  ... 47 ok lines
  all assertions passed
call-graph-callees.csv: 1841 rows, no diff
```

`bash tools/run-tests.sh` is unchanged and picks up no new file, which is the
point: the claim here is a per-row reading, and a reader re-runs the commands
above rather than a test asserting a prose sentence.
