# Do the agreements agree as sets, and not only in number? 61 of 74, and the thirteen that do not (issue #704)

`ec/annotations/call-graph.md` carries `cited_by == inbound` as the
two-framings-agree check and says plainly that it is *"not a proof they are
counting the same thing"*. Issue #681 read fifteen of the agreements one at a
time and found two of them — `bank1,DEC4` and `common,4A77` — where the counts
agree while the two sets are different listings, which it called *"a shape the
write-up's table does not distinguish"* and *"a shape the two columns cannot
show at all"* ([`neighbour-edge-attribution.md`](neighbour-edge-attribution.md)
§The two shapes the write-up's table does not distinguish). **This file measures
how common that shape is across every agreement the tree carries**, because the
real strength of the check the ranking's justification rests on is what was
never calibrated.

**The split is 61 set-identical against 13 count-only, over the 74 agreements
the committed tree carries.** The 13 are listed with both sets in §The split.
Of the five that are new to the record, two open a question this change does
not settle — the 0x0200 / 0x0213 boundary pair and `bank1,E9CE` — and
§The five that are new says what each is, and why leaving those two open is the
finding rather than a gap in it.

**Nothing here is a behavioural claim.** No register `status:` changed, no
annotation row, no name, no re-export, no hardware and no Windows. This is a
text measurement over `call_graph.scan()`'s edges and the committed CSVs, and
"count-only" below is a statement about two sets **this run produced** — not a
claim that any comment is wrong, and not a claim that any edge is spurious.
`call-graph-callees.csv` is byte-identical, which is the issue's own pass
condition and §What this does not move is what makes it so.

## The denominator is 74, not the issue's 90

The issue asks about "all 90 agreements". **The committed tree carries 74**, and
the 90 is the figure issue #489's naming retired. `neighbour-edge-attribution.md`
§*** CORRECTION 2026-09-27 (issue #489)**** and `call-graph.md` §Corrected
2026-09-27, issue #489 both record why: `call_graph.citations()` proposes a
candidate only while the address a comment names still resolves to an anonymous
`FUN_*` export, and #489 named 37 `pd` rows — 20 of them `FUN_CODE_*` *callees*
the ranking still counted, each with `cited_by` now 0 and none replaced. So the
pool fell to 74 while the fifteen #681 read one at a time stayed the same
fifteen, all of them already named.

This file therefore measures the rows the tree carries and does not re-derive
90. Re-deriving it would need the pre-#489 tree, and measuring that tree would
report an artefact that no longer exists. **Every figure below is a function of
the committed inputs, and §Re-deriving reproduces them**; a reader whose tree
carries a later tranche should re-run rather than carry these forward, which is
the rule `call-graph.md` §The counts, in every framing this repo has for them
already sets for its own.

## The split is 61 set-identical against 13 count-only

The comparison is set-wise, over the same run that forms the table.
`call_graph.scan()`'s `edges` maps a callee to its inbound sites as
`(scope, caller, form)`, and `call_graph.build()` already forms
`callers = {(scope, caller) for scope, caller, _ in sites}` before collapsing it
to a number. This file rebuilds that set rather than the number and compares it
to the `citing` set the same run keeps in `build()`'s `"citing"` column.

`rank` is the row's position in the committed table's own order. `transfer` is
the caller-listing set; `citing` is the citing-row set. The site column is the
transfer instruction the graph books.

| rank | row | transfer set | citing set | where the transfer is |
|---|---|---|---|---|
| 8 | `bank1,DEC4` | `{9A41, DEA5}` | `{9A41, 9A78}` | `lcall 0xDEC4` at 0x9A68, 0xDEBF |
| 11 | `common,4A77` | `{43A5}` | `{43A5, 4A76}` | `lcall 0x4A77` at 0x4435 and 0x4454, both in `43A5` |
| 44 | `bank0,D5DB` | `{D5DB}` | `{D5D4}` | `ljmp 0xD5DB` at 0xD662, inside `D5DB` itself |
| 46 | `bank0,E6F4` | `{E7BB}` | `{E6B1}` | `ljmp 0xE6F4` at 0xE7C1 |
| 52 | `bank1,B43B` | `{B33B}` | `{B415}` | `ljmp 0xB43B` at 0xB377 |
| 69 | `bank1,E9CE` | `{ED3A}` | `{E954}` | `acall 0xE9CE` at 0xEEA2 |
| 75 | `common,0FE6` | `{0213}` | `{0200}` | `lcall 0x0FE6` at 0x021E |
| 79 | `common,150A` | `{0213}` | `{0200}` | `lcall 0x150A` at 0x0272 |
| 82 | `common,153A` | `{0E34}` | `{0D7B}` | `ljmp 0x153A` at 0x0E34 |
| 87 | `common,3459` | `{3578}` | `{355E}` | `ljmp 0x3459` at 0x3578 |
| 88 | `common,34C6` | `{3555}` | `{355E}` | `ljmp 0x34C6` at 0x355B |
| 93 | `common,492D` | `{4825}` | `{4A76}` | `ljmp 0x492D` at 0x482E |
| 103 | `common,5A5A` | `{0046}` | `{5A55}` | `lcall 0x5A5A` at 0x0049 |

**Eleven of the thirteen are one transfer listing against one citing row, same
size and different members. `bank1,DEC4` is two against two**, sharing one
member and differing in the other. **`common,4A77` is the one that differs in
kind**: `inbound=2` from **one** caller — `common,43A5`, at 0x4435 and 0x4454 —
against **two** citing rows, so there the agreement hides a 1-vs-2 gap at the
caller level that no column in the table could have shown. That row is the
reason the count and the set have to be measured separately rather than the count
standing in for the set.

*(Correction to this change's plan, which called twelve of the thirteen
"1-site-against-1-citer". The gloss beside it — same size, different members —
is right for twelve rows and wrong only for `common,4A77`, which is the one row
the sentence then singles out; the label itself is wrong for `bank1,DEC4`, whose
two sets are both of size two. The split, the ranks and every set above are
unchanged.)*

## Eight of the thirteen are on the record already

Eight of the thirteen are not new, and re-deciding them would be a second,
competing reading of a row that has already been read:

- **Six** are the rows `neighbour-edge-attribution.md` §The six that name a
  different site adjudicated, each with the address its comment names instead:
  `bank0,D5DB`, `bank1,B43B`, `common,3459`, `common,34C6`, `common,492D`,
  `common,5A5A`.
- **Two** are the rows §The two shapes the write-up's table does not distinguish
  named without adjudicating — `bank1,DEC4` and `common,4A77` — which is where
  this issue's shape was first seen and is the whole of its population on the
  #681 reading.

## The five that are new, and what each one is

**Five appear in neither file #681 worked from.** They are outside
`ec/ghidra/gap-citation-scan.csv` altogether, so the count-only shape is **not**
confined to the rows that already carried a neighbour-edge signal: `bank0,E6F4`,
`bank1,E9CE`, `common,0FE6`, `common,150A`, `common,153A`. The next section says
what each is; this one says only that they were outside the population #681
measured, which is a fact about the population and not about the rows.

What each comment actually says is worth stating, because **three of the five
turn out to be comments that are right** and the disagreement is about which row
a comment is attached to and which listing a transfer sits in:

- **`common,0FE6` and `common,150A` — the 0x0200 / 0x0213 boundary pair.** Both
  are cited by `post_05e8_sp_0c0_init_1042_16e7_3105` at `common,0200`, and both
  are transferred from `common/0213.asm` — at 0x021E and 0x0272. That comment
  attributes the calls itself: *"Read forward from the committed image, 0x0213
  onwards ORs 0x80 into 0x16E7, sets XDATA 0x3105 = 4, sets R7 = 3, **calls
  0x0FE6** and zeroes 0x103E-0x103B"*, and *"ending in a loop whose four back
  edges all land on `lcall 0x150A` at 0x0272"* — naming the site address
  outright in the second case. **The comment and the graph agree about the
  listing and disagree about the row**, because the comment hangs off 0x0200
  while the transfers are inside the 136 bytes that
  [`../../ec/annotations/call-graph.md`](../../ec/annotations/call-graph.md)
  §The five boundary rows were the load-bearing correction records as
  belonging to `FUN_CODE_0213`. `common,0213` has no annotation row of its own.
- **`common,153A` — the same caller role #681 already adjudicated twice.** The
  citing comment at `common,0D7B` reads *"0x0E34 is ljmp 0x153A, a BL51 far-call
  stub that pushes nothing"*, naming 0x0E34 as a **caller** reaching 0x153A. That
  is a *source* role, the shape `neighbour-edge-attribution.md` recorded for
  `common,3459` and `common,34C6` as *"0x3459 as a caller, not a site"*. The
  graph books the same transfer, in the listing the comment names.
- **`bank0,E6F4` — a continuation boundary read as a citation.** The citing
  comment at `bank0,E6B1` ends *"The listing ends at 0xE6F3 and the next entry,
  0xE6F4, continues the same routine, so this is a fragment of it."* That names
  0xE6F4 as a **boundary**, not a call, and names no transfer in `bank0/E7BB.asm`
  — which is where the `ljmp 0xE6F4` at 0xE7C1 is booked and which has no
  annotation row. This is the shape `bank1,DEC4`'s second comment has.
- **`bank1,E9CE` — a transfer booked to a listing its own row calls a data
  run.** This is the one that most needs a human, and it is stated rather than
  adjudicated. The transfer is an `acall 0xE9CE` at 0xEEA2 inside
  `bank1/ED3A.asm`; `ED3A`'s own annotation row is titled `data_run_2e_3e` and
  reads *"Not a function: the bytes here continue the same ascending data run
  (0x2E-0x3E) that 0xED02 sits in … its 345-line body is not a reading of
  code."* The citing comment at `bank1,E954` names 0xE9CE as a listing rather
  than a call — *"a final AJMP 0xEA19 that lands inside the 0xE9CE listing"*.
  **So the graph has booked a call out of a listing that its own annotations say
  is data.** That is an observation about a booking the graph made, and it is
  worth more than a verdict: settling it either way moves `inbound`,
  `named_callers` and the ranking, which this issue rules out.

**Adjudicating these five is the natural next issue and this change does not do
it.** A verdict needs what `neighbour-edge-attribution.md` §What a recovered
edge would need before it is credited already lists — an independent
re-measurement of the site that does not go through the window walk, a boundary
that survives a re-decode, and its own `call_graph.py --check` before and after
— and a seed row would additionally need a `--mode rebuild-project` re-export,
which is its own branch, because two branches that both rebuild the EC project
cannot merge.

## No count-only row moves the ranking, and the reason is the sort key

**The answer is structural, so it is argued from `call_graph.build()`'s sort
key rather than measured by re-ranking.** The key is `(-cited_by, -inbound,
scope, addr)`. **`callers` is emitted as a column and is not a sort key**, so a
count-only row keeps both of its ranking keys whatever its caller set is, and no
count-only row changes the ranking's order. The supporting measurement is the
band structure: `common,4A77` is rank 11 inside an 8-row band spanning ranks
4–11, and the eleven `cited_by=1` / `inbound=1` count-only rows all sit inside a
single 66-row band spanning ranks 39–104, whose internal order is `scope` then
`addr`. **The count-only rows are not being promoted by a count that should not
have promoted them** — inside a band the two keys tie, so what orders them is the
lexicographic fallback the tool already documents.

The counterfactual "what if `callers` replaced `inbound`" is deliberately not
run as a headline. It moves the overwhelming majority of the table, almost all of
it rows the issue does not ask about, and quoting it would read as the ranking
being unstable when the ranking never used the column.

## The committed table cannot show this, and that is the screen's blindness

The reason the shape survived #681's reading is structural and worth stating as
a measurement rather than a lament. `call_graph.build()` stores
`"callers": len(callers)` — **a bare number** — so the per-callee transfer-listing
set is not in the committed table at all. **The CSV alone finds 1 of the 13**:
only `common,4A77`, where `callers=1` against two `citing` entries. The other
twelve are `callers == len(citing)` and are invisible to any screen reading only
the columns, which is precisely why #681 had to walk the `.asm` listings to
adjudicate its fifteen.

That is the issue's premise confirmed as a measurement, and it is the
repository's own calibration rule pointed at the method being proposed: **not
found by this method is never absent.** The cheap screen is not a weaker version
of the scan — it is a different and much blinder one, and on this population it
sees one row in thirteen.

Over the 104 ranked rows, **34 have a caller set that is not the citing set**;
13 of those are the ones where the two counts still agree, which is the
coincidence the check is about. The other 21 are rows where `cited_by` and
`inbound` already disagree, so the agreement reading does not apply to them and
this file makes no claim about them.

## What this does not move

No CSV is edited. `ec/annotations/call-graph-callees.csv`,
`ec/annotations/ghidra-functions.csv`, `ec/annotations/registers.yaml`,
`ec/ghidra/gap-citation-scan.csv` and `ec/ghidra/xdata-symbols.csv` are all
untouched — which is also why no re-export is needed, and why none of the three
Ghidra failure modes applies. `call_graph.py`, `citation_callers.py`,
`citation_frames.py` and `citation_gap_scan.py` are **read, not changed**: this
change consumes `scan()`'s edges and does not alter how they are formed.

**There is no new tool and no new suite**, for the reason
`neighbour-edge-attribution.md` §What this does not move gives: this is a
per-row reading over a table that already exists, so a test asserting "13 of 74"
would be a test asserting a count of the tree — the failure CLAUDE.md records as
bit #1169, where `test_check_pin_table_by_cited_file.py` held a count that four
concurrent branches each bumped from a different base. **The claim is checked by
re-running the derivation**, which is §Re-deriving below, and every figure in
this file is in it.

The one shared-file edit is a single clause added to
[`../../ec/annotations/call-graph.md`](../../ec/annotations/call-graph.md)
§What is left, and the two limits a reader must carry, inside the paragraph that
already states the two-framings-agree reading and points at
`neighbour-edge-attribution.md` for the per-row verdicts. **The honest answer
belongs where the reading is stated**, not only in a file a reader has to find.

## Re-deriving

**The cheap screen first**, over the committed CSV alone. This is what the
columns can see, and §The committed table cannot show this is the measurement it
supports: the 104 ranked rows, the 74 agreements, and the one row where the
columns disagree at all.

```sh
python3 -c "
import csv
rows = list(csv.DictReader(open('ec/annotations/call-graph-callees.csv', newline=''), strict=True))
rk = [r for r in rows if int(r['cited_by'])]
ag = [r for r in rk if r['cited_by'] == r['inbound']]
cit = lambda r: set(r['citing'].split())
print('rows %d | ranked %d | cited_by==inbound %d'
      % (len(rows), len(rk), len(ag)))
print('of those, callers != len(citing): %d'
      % len([r for r in ag if int(r['callers']) != len(cit(r))]))
for r in [r for r in ag if int(r['callers']) != len(cit(r))]:
    print('  %s,%s callers=%s citing=%s' % (r['scope'], r['addr'], r['callers'], r['citing']))
"
```

```
rows 1841 | ranked 104 | cited_by==inbound 74
of those, callers != len(citing): 1
  common,4A77 callers=1 citing=common:43A5 common:4A76
```

**Then the set-wise comparison**, which drives `call_graph.scan()` and prints
the split and all thirteen rows with both sets. This is the block a reader runs
to check every other figure in this file, and it needs nothing but `python3` and
the committed tree.

```sh
python3 -c "
import sys; sys.path.insert(0, 'ec/tools')
import call_graph as cg

index = cg.load_index()
edges, _unres, _orph, _tot, listings = cg.scan(index)
cited, _rej, _und, _lk = cg.citations(index, listings)
rows = cg.build(index, edges, cited)
sets = lambda k: (sorted({'%s:%s' % (s, c) for s, c, _ in edges[k]}),
                  sorted({'%s:%s' % (s, a) for s, a, _ in cited.get(k, [])}))
agree = [r for r in rows if r['cited_by'] and r['cited_by'] == r['inbound']]
ident = [r for r in agree if sets((r['scope'], r['addr']))[0] == sets((r['scope'], r['addr']))[1]]
only = [r for r in agree if sets((r['scope'], r['addr']))[0] != sets((r['scope'], r['addr']))[1]]
print('ranked %d | agreements %d | set-identical %d | count-only %d'
      % (len([r for r in rows if r['cited_by']]), len(agree), len(ident), len(only)))
rank = {(r['scope'], r['addr']): i + 1 for i, r in enumerate(rows)}
for r in only:
    k = (r['scope'], r['addr']); t, c = sets(k)
    print('  %3d %s,%s  transfer %-28s citing %s'
          % (rank[k], k[0], k[1], '{%s}' % ', '.join(t), '{%s}' % ', '.join(c)))
"
```

```
ranked 104 | agreements 74 | set-identical 61 | count-only 13
    8 bank1,DEC4  transfer {bank1:9A41, bank1:DEA5}     citing {bank1:9A41, bank1:9A78}
   11 common,4A77  transfer {common:43A5}                citing {common:43A5, common:4A76}
   44 bank0,D5DB  transfer {bank0:D5DB}                 citing {bank0:D5D4}
   46 bank0,E6F4  transfer {bank0:E7BB}                 citing {bank0:E6B1}
   52 bank1,B43B  transfer {bank1:B33B}                 citing {bank1:B415}
   69 bank1,E9CE  transfer {bank1:ED3A}                 citing {bank1:E954}
   75 common,0FE6  transfer {common:0213}                citing {common:0200}
   79 common,150A  transfer {common:0213}                citing {common:0200}
   82 common,153A  transfer {common:0E34}                citing {common:0D7B}
   87 common,3459  transfer {common:3578}                citing {common:355E}
   88 common,34C6  transfer {common:3555}                citing {common:355E}
   93 common,492D  transfer {common:4825}                citing {common:4A76}
  103 common,5A5A  transfer {common:0046}                citing {common:5A55}
```

**The site addresses for the five rows §The five that are new introduces** come
straight from the listings the graph books them to. The eight already on the
record have their own block in
[`neighbour-edge-attribution.md`](neighbour-edge-attribution.md) §Re-deriving,
and those addresses are unchanged by this measurement.

```sh
grep -n "^E7C1"             ec/decompiled/bank0/E7BB.asm
grep -n "^EEA2"             ec/decompiled/bank1/ED3A.asm
grep -n "^021E\|^0272"      ec/decompiled/common/0213.asm
grep -n "^0E34"             ec/decompiled/common/0E34.asm
```

```
10:E7C1     02 e6 f4 ljmp     0xe6f4
234:EEA2     31 ce -  acall    0xe9ce
15:021E     12 0f e6 lcall    0x0fe6
56:0272     12 15 0a lcall    0x150a
9:0E34     02 15 3a ljmp     0x153a
```

**The gates that hold the numbers where they were** — the first of which is this
issue's own pass condition, and its output is what proves the measurement read
the edges rather than changing them:

```sh
python3 ec/tools/call_graph.py --check
python3 ec/tools/citation_gap_scan.py --check
python3 ec/tools/citation_gap_scan.py --self-test
```

```
call-graph-callees.csv: 1841 rows, no diff
  gap citation scan: 121 row(s); verdicts 2 boundary-cut, 118 no-transfer, 1 not-code
  all checks passed
  ... 47 ok lines
  all assertions passed
```

`git status` shows `ec/annotations/call-graph-callees.csv` unmodified after both
blocks, which is the byte-identical condition stated above.

`bash tools/run-tests.sh` is unchanged and picks up no new file, which is the
point: the claim here is a per-row reading, and a reader re-runs the commands
above rather than a test asserting a prose sentence.
