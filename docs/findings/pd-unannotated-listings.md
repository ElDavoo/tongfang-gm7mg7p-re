# Every `pd` listing now has a row, and #471's figures did not move (issue #489)

[`pd-common-address-attribution.md`](pd-common-address-attribution.md) closes by
naming the unannotated `pd` population as the thing that would turn issue #471's
"latent today" into a live figure change. This is that work: every committed
listing under `ec/decompiled/pd/` now carries a `ghidra-functions.csv` row, and
**none of the figures that change was watching for moved.** A null result, and a
real one.

**Nothing here is a behavioural claim and no live test ran.** Every figure is a
static measurement over committed `.asm` listings and committed CSVs. No
hardware is reachable from a GitHub-hosted runner and nothing in this change
needs any.

---

## The population, and the number the issue got wrong

The issue says **38**. It is **37**, and the difference is arithmetic that had
aged rather than a disagreement about what to count.

`pd-common-address-attribution.md` already carried both: its own text said 38 at
the time, and issue #470's correction beside it said 37. The issue re-derived
`535 - 497` — but `pd 0x11C2` was annotated by #470 after that arithmetic was
done, so 497 is a figure from one merge earlier and 38 is its difference. The
set difference over *matched addresses* is 37, and a subtraction of two totals
would have given the same answer today only by luck: it goes wrong the moment a
row names an address with no listing behind it, or a listing arrives with no row.

**It is measured, not argued, and the tool that measures it is committed.**
`ec/tools/pd_unannotated_census.py` derives the population from
`ec/decompiled/pd/*.asm` minus the `pd` rows of the annotation CSV, keyed on the
address each filename already spells, and reports the two halves of the
difference separately — listings with no row, *and* rows naming no listing —
because a census that subtracted the totals would net them to zero and a zero
reads as a finished population. That is the same argument
`merge_annotation_shards.py`'s `--census` mode makes for a batch: *"the number
the batch is sized by has to come out of a committed tool rather than out of
somebody's arithmetic."* The tool prints it on every run; after this change it
prints zero, and the test that holds the claim
(`ec/tools/test_pd_unannotated_census.py`) asserts **the claim** — every listing
has a row, and no row cites another function's listing — rather than a count of
the tree, which is the failure `test_check_pin_table_by_cited_file.py` has been
four times.

## The edge accounting, and why it is all one scope

**The next three figures are the population *before* the 37 rows existed**, and
they are named as before-state because that is the only tree the census can
print them on: run on this tree it reports a population of zero. Of the 37,
**28 are the endpoint of 39 `lcall`/`ljmp` edges out of the rows that existed
then**, and **9 are the endpoint of no such edge** — `0x0000`, `0x0012`,
`0x0B85`, `0x0C13`, `0x1EFE`, `0x39E6`, `0xA000`, `0xCDB7`, `0xE930`. The issue
said 28 and 10; the 10 is the same off-by-one, and the structural figures it got
exactly right are the two that matter.

**Every one of the 39 edges has a `pd` caller, and none targets a `common` row.**
That is the whole of the null result, and it is worth stating as a mechanism
rather than as a number. Seeding a `pd` row makes each of those 39 a
same-scope `pd`→`pd` join. A same-scope join is never proxied, and
`reached_only_by_bank` counts `common` targets whose caller scopes are a subset
of the banks — so a `pd` row can move neither population. Issue #471's fix only
shows where a bank caller and a `pd` caller reach the *same* `common` row, and
on this tree no such row exists, now or before.

**Seeding the 37 moves that accounting without moving the result.** Re-running
the tool's own `edges_from_annotated_rows()` over the same 37 against this
tree's rows gives **33 reached, 45 edges, 4 bare** (`0x0000`, `0x0012`,
`0x0B85`, `0xA000`) — still `callers pd=33`, with all 45 edges out of `pd`. Six
edges are new and every one of them comes from a
caller inside the population, which is why it was invisible before: the caller
had no row of its own, so `cluster()` never walked its listing. `0x0C13`,
`0x1EFE`, `0x39E6`, `0xCDB7` and `0xE930` each gain their first edge that way,
from `0xE902`, `0x6673`, `0x6673`, `0x8A4A` and `0x7B14`, and `0xF1B0` gains a
third from `0xE6C0`. That is the accounting catching up with the graph, not a
new reach: an edge whose two ends were both already in the image.

The census reports the per-address caller scope rather than a total for exactly
this reason, and reports separately the **two** addresses in the population that
also carry a `common` row: `pd 0x0000` beside `common 0x0000`, and `pd 0x0012`
beside `common 0x0012`. Those are the two the issue names, and they are the two
where the question is live. Both stay unreached.

## Measured: no published figure moves

`python3 ec/tools/group_functions.py --report`, before and after, on the
committed tree:

| `--report` line | before | after |
|---|---|---|
| `proxy_edges` | 198 (bank0=129, bank1=69) | **198 (same)** |
| distinct `common` targets | 38 | **38** |
| proxied edges by row population | 98 / 100 | **98 / 100** |
| `reached_only_by_bank` | 20 | **20** |
| `cross_region` | 27 | **27** |
| functions | 1914 | 1951 |
| `callgraph_pd_0003` | 303 | 364 |
| `ungrouped` | 491 (481 + 10) | **460 (450 + 10)** |
| call-edge buckets | A=1083 B=1481 C=450 | A=1238 B=1481 C=631 |

**The issue's own before-figures were three generations stale**, and this table
does not restate them: it asks for a before/after on `26 / 196 / 36 / 115-81`,
and today's `--report` prints `20 / 198 / 38 / 98-100`. Those four numbers no
longer describe the tree. The figures above are the ones this change measured.

What *did* move is the PD program's own connectivity, and bucket B did not move
at all. The 37 listings had no rows, so `cluster()` never walked their `.asm`
and never counted the transfers in them; annotating them adds 37 readers to the
graph, which is where A=+155 and C=+181 come from. B is the bucket the same-
bank assumption decides, and no `pd` edge can reach it — the PD image is a
separate program, not a third bank. The same 37 rows are what moved
`callgraph_pd_0003` from 303 to 364 and `ungrouped` from 491 to 460, and the
two deltas are deliberately not the same size: of the 37, five take a typed
group (`arithmetic` 237 → 242) and two take another (`dispatch-tables`
99 → 101), so 28 join the component and two stay `ungrouped` — `pd 0x0000`,
the one-instruction forwarder, and `pd 0x0012`, the fill byte, are the pair,
and neither is an endpoint any listing reaches, so `cluster()` has no edge
from either. The component's +61 is 28 new plus 33 moved: 33 rows that were
`ungrouped` before are now inside it, so the component gained more rows by
absorbing than by joining. A
connected component is not a subsystem:
`group_functions.py`'s `--report` says so on every run and so does this.

## An interior byte takes a row only if the export gives it one

The issue's criterion, applied. **Two of the 37 are single bytes with no
terminator at all**: `pd 0x0012` (`0xFF`, `mov R7,A`) and `pd 0x39E6` (`0xFD`,
`mov R5,A`). Each has its own committed listing and its own `index.csv` row, so
each meets the criterion and neither is given a role. `0x0012` is named for what
the byte is — `ff_filler_not_a_function_0012` — after `common 0x7FF1`'s
precedent for naming a filler byte rather than inventing a function.
`0x39E6` is a different case and is worth separating: it *is* the endpoint of
a single `lcall`, the one at `ec/decompiled/pd/6673.asm:16` (site `0x6685`, in
`pd 0x6673`) — `grep -rn "12 39 e6" ec/decompiled/pd/*.asm` returns that line and
no other, and `group_functions.listing_calls()` over `pd/`, `bank0/`, `bank1/`
and `common/` agrees on one inbound edge — and it has no `ret`, so that call
stores A into R5 and then runs on
into `0x39E7` (`set_args_r1_d3_r2_07_r3_01`) — a separate export of the next
four instructions of the same straight-line block. Ghidra's function boundary
cuts between the store and the constants; the row says so rather than inventing
a return. Its own row reads *"a `lcall 0x39E6` thus returns to *its* caller"*,
which is what one caller does and asserts nothing about a second; the
two-`lcall` reading here had no source but the before-state's bare-list, which
did name `0x39E6`.

**Five already carried a name from the export** and needed a row recording what
the listing already said: `0x0000`, whose `index.csv` `seed_basis` **was**
`vector` before this row existed and reads `annotation` on this tree, and the
four one-instruction `lcall 0x10BC` thunks at `0x3497`, `0x998B`,
`0x9C1B` and `0x9C4D`. **All five** are why `build_ec_decompile.py`'s ledger
said 26 functions were named without a CSV row and now says 21, and
`second_copy_census.py --check` agrees: its `target-of-a-transfer` count went
from 12 to 7, and the five it lost are exactly these. The export had propagated
a name across the transfer, which is a fact about the callee. **The row's name
is therefore not the export's.** `pd 0x0000` is
`ljmp_0500`, matching its neighbours in the vector table (`ljmp_0056` at
`0x0003`), and the four thunks are `call_10bc`, matching `0x6FD5`
(`call_10bc_with_b_60_and_dptr_0433`). Naming them after their callee would
assert a mechanism the bytes at those addresses do not contain.

**The `vector` is the one figure here that no longer reads off the tree, and
that is a consequence of the row rather than a fact about the address.**
`build_ec_decompile.py:544` sorts seeds by evidential strength with
`STRENGTH = {"annotation": 0, "vector": 1, ...}` and the first seed at an
address wins, so a row at `0x0000` necessarily outranks the vector slot
underneath it and the export rewrites its own record. **The claim it was
evidence for survives without it**: `origin/main`'s `ec/decompiled/index.csv`
already reads `pd,0000,c_startup_idata_clear,3,vector`, and
`docs/findings/named-without-a-row.md` already records the propagated name, so
"the export discovered this as a vector slot and gave it a name from across the
jump" is evidenced on the before-state rather than on this one. **The row's own
comment carries the same correction**: it attributes `seed_basis=vector` to
`origin/main`'s `index.csv`, says outright that this tree records `annotation`
and why `STRENGTH` makes that the outcome, and keeps the reset-slot reading tied
to the before-state value instead of asserting it of the shipping tree. The
export was re-run for the reworded comment, so the plate at
`ec/decompiled/pd/0000.c` and its digest in `ec/ghidra/c-digests.csv` carry it
too. The clause as it was first written asserted that `vector` value in the
present tense, which was wrong about the tree it shipped with; that clause, and
the propagated-name claim beside it, are the only parts of the row that changed.

## What this does not establish

**`unresolved` is a result, and thirteen of the 37 are one.** The large record
handlers — `0x6673`, `0x7B14`, `0x7CE0`, `0x8A4A`, `0xA0E6`, `0xB8DB`, `0xB9A1`
among them — are described as far as their instructions go: which XDATA bytes
they read and write, which direct bits they test, which already-named helpers
they call, and where each one exits. What a record *means*, and which arm a
given caller selects, is not decoded, and the rows say so rather than filling the
gap with a plausible name. That is the rule `ec/annotations/README.md` states
and the vocabulary exists to make free.

**Nothing is established about hardware behaviour, and no live test was run.**

**A reach that the graph does not have is not an absence.** The bare listings —
9 in the before-state above, 4 on this tree, both named there — are *"no
annotated row reaches them"*, measured over the
committed `lcall`/`ljmp` operands. That is not "unreachable" and not "dead": a
computed target (`sjmp @a+dptr`), a DPTR-carried bank-select target and the
paged `ajmp`/`acall` forms are all invisible to that reader, which is the first
thing `group_functions.py`'s own docstring lists among its blind spots. Seeding
the five that gained an edge did not make them reachable, only visible: an edge
between two addresses the image already contained is not a new reach, and
`0x0000`, `0x0012`, `0x0B85` and `0xA000` are exactly as unreached as they were.

**One reading in this write-up is a lower bound, and the tool says so.**
`pd_unannotated_census.py` reports that 67 committed annotation rows name a
document and no `.asm`, and therefore contribute no edges to the accounting
above — `cluster()` skips exactly the same rows, so the figure is the
clustering's and not a second reading of it. That is a pre-existing property of
`ghidra-functions.csv`, it is left alone here, and repairing 67 citations is a
change to a shared file for reasons unrelated to this population. **Both edge
counts mean edges out of the rows whose evidence names a listing**, 39 before
and 45 after, and the 67 are 67 on either tree.

## What else this change moved, and what it inherited

**The grouping layer moved, and `--apply` is mandatory** — `group_functions.py
--check` fails the moment an annotated row has no group row, so the 37 rows each
needed one. The diff to `function-groups.csv` is large and mostly one thing:
several hundred existing `pd` rows whose comment reads *"One of 414 mutually
reachable functions"*, which is now 499 because the component grew.

**Eleven rows in that file changed for reasons this change did not cause.** A
pristine `--apply` on the untouched tree — no annotation change at all —
rewrites them: `pd 0x35DA`, `bank0 0x8931 / 0x9C47 / 0xD2BE / 0xDE83`,
`bank1 0xBD45 / 0xE656`, `common 0x0200 / 0x3B4E / 0x4A76 / 0x7177`. Five of
them actually reclassify — four out of a *callgraph* component (`bank1 0xBD45`
and `0xE656` out of `callgraph_bank1_1738`, `common 0x3B4E` out of
`callgraph_common_2BC1`, `common 0x7177` out of `callgraph_common_0000`) and
one out of `ungrouped` (`common 0x4A76`) — and ten of the eleven gain evidence
paths, `bank1 0xE656` being the one that does not. The other six keep the
group they had. `pd-common-address-attribution.md` recorded this drift for one
row (`bank1 0x8096`) and deliberately did not absorb it; it has since grown to
eleven. `--apply` cannot be run around it, and hand-reverting ten unrelated
rows would be worse than the drift, so it is absorbed and named here. **It wants
its own issue.**

**And one `index.csv` row outside the `pd` population moved the same way.**
`common 0x0000` reads `seed_basis=vector` on `main` and `annotation` here, and
no `common` row was added by this change — the row at
`ghidra-functions.csv:1271` has been there throughout. It moves because a
`common` seed is appended to *both* bank programs
(`build_ec_decompile.py:538-541`) and `STRENGTH` ranks `annotation` ahead of
`vector`, so the pre-existing `common` row outranks the vector slot both banks
also carry at `0x0000`. It is named here for the same reason the eleven are: a
re-export recomputing a value nobody edited is exactly the drift this section
exists to record, and hand-writing `vector` back would be undone by the next
export. **`pd 0x0000` moved for the same `STRENGTH` reason, from a row this
change did add, and it is named above**; between them these are the only two
`vector` → `annotation` moves in the whole `index.csv` diff, the other 35
transitions in that file being `auto` → `annotation` for the rows this change
added.

**The hand-transcribed figure sets elsewhere that moved with the tree**, each
updated in place rather than left red: `census_ff_fill.py`'s fill census (whose
`pd 0x0012` was this issue's last unannotated member, so its self-test now holds
"every fill listing carries a row" instead of a count of how many do not);
`build_ec_decompile.py`'s self-test pins, which record the annotation-layer
ledger and the per-program `functions_named`; `subsystems.md`'s census, which
`--check` recounts; `citation_gap_scan.py`'s population, which fell from 99
citing rows to 96 because `call_graph.citations()` proposes a candidate only
when the address a comment names still resolves to an anonymous `FUN_*` export
(`call_graph.py:343`), and the three pairs it lost — `pd 0x06EA` cited by
`bank0 0xD045`, `pd 0x39E6` by `pd 0x39E7`, `pd 0xE930` by `bank1 0xE924` —
stopped resolving that way once this issue gave each callee a name of its own;
`call-graph.md`'s ranking paragraph, which counts the same population and
therefore moved with it **and further**: the `FUN_` predicate runs on every
citation, not only on that scan's, so naming these 37 also took 20 `pd` rows out
of `call-graph-callees.csv`'s ranked set outright — every one a `FUN_CODE_*`
callee whose `cited_by` is now 0, none replaced — taking `sum(cited_by)` 147 →
126 and the `cited_by == inbound` agreements 90 → 74. The 15 neighbour-edge
agreements the tool finds among them are the *same* 15, so the 9/6 reading
`call-graph.md` records stands whole; only the pool it is counted against is
smaller. Both are corrected in place at their own citations; and
`test-line-pin-census.md`'s per-pin table, whose `../findings.md` rows the
`docs/findings.md` correction below moves by 26 and which therefore re-registers
four of them. That last one is a re-anchor rather than a correction, and its
note is written where the other re-registrations are recorded, so the reasoning
is not duplicated here.

**Three committed checks this change turned red, each a generated artefact and
each regenerated rather than hand-corrected.** None of the three is run by
`agent-gates.sh`, which is why the first pass did not see them; all three are
green here, and each is re-runnable by the name given. `docs/findings/INDEX.md`
read `134 write-ups` against a generator producing 135 — this write-up being
the one added — fixed by `python3 ec/tools/gen_findings_index.py >
docs/findings/INDEX.md`, after which the file differs from the committed one in
that count line alone; the alphabetical entry itself was already in place.
`ec/ghidra/gap-text-check.csv` still carried the pre-rename `FUN_CODE_*` callee
names in four surviving rows (`pd 0x06EA`, `0x1EFE`, `0x6673`, `0xD72E`) —
`python3 ec/tools/verify_gap_text.py --report`, whose diff is those four
`row_name` cells and nothing else, since the 143 instruction verdicts agreed
before and after and this change moved names, not bytes. And
`ec/tools/export_ownership.py`'s `OWNERSHIP_ORACLE` still pinned the floor-1
figures at 13 and 28; re-measured with the tool's own `bridged_classes` and
`classes_of` they are 14 and 29, while `bridged` (7) and `flood_no_floor` (562)
hold, so the floor is doing the work it was pinned for. The cause is that
`body_of` reads the statements between the braces, so a rename changes the text
containment is measured on. Four of the 37 — `pd 0x3497`, `0x998B`, `0x9C1B`,
`0x9C4D` — are one-instruction forwarders to `0x10BC` that had been carrying
the *callee's* name `add_full_product_to_dptr` and are now `call_10bc`, and
everyone calling one of them had that call statement renamed with them, whether
directly or by jumping into a body that makes it: `0x4402`, `0xC901`, `0xF22E`,
and `0x4800` and `0xF79F`, which `ljmp` into `0x4402`. Those five left the
193-member floor-1 class. The four forwarders kept the body
`add_full_product_to_dptr();` — they still call `0x10BC` under its own name —
and with `0xB263`, a fifth forwarder to `0x10BC` this issue did not name, plus
`0xCCB7` and `0xEDB5`, which merely contain that statement, they became a class
of their own. The comment above the pins carries the same worked case, since
that is where the next reader re-measuring these four numbers will look.

**One further figure is left stale on purpose.**
`docs/findings/xdata-export-ownership-page-census.md` transcribes a
`--self-test` console run that printed the 13 and 28 this change moves, and
that file is a dated snapshot which says so: its own header caveat leaves the
transcribed runs as the runs printed them, per `docs/findings.md` §4a. Editing
it would renumber a transcript into a run that never happened, so it stays and
is named here instead, so that the 13 and 28 in it are not read as current.

**And `gen_findings_index.py --check` is red on `origin/main` too, for a reason
this branch does not share.** At `637b5dc1` the committed count is 134 against
135 generated, because #1231 landed a write-up there and did not move the count
with it. This branch is one commit behind that, and on this branch the
generator does agree with the 135 committed here. That drift is main's own and
is not absorbed here.

**Those three retired, and none of them was answered.** **No citing comment
changed**: `bank0 0xD045` still reads *"It then clears 0x06EA and 0x06EB to
zero"*, and all three citers are still rows in `call-graph-callees.csv`. What
moved is the *callee*, and only the `FUN_` predicate notices that. All three
pairs were `no-transfer` — the scan's actual question is whether a comment
naming an address is one the citing listing can reach, and `no-transfer` is its
verdict that it cannot — so naming the callee settles nothing about the reach.
**It is a smaller population and an unchanged set of open questions.** Each of
the three wants its own reading, which is a separate piece of work from this
one; it is stated here rather than done, and nothing in this diff answers it.

**`census_ff_fill.py --self-test` was already red on `main`** for one unrelated
reason (its `seed_basis`/`also_in` check over the seventeen `common` fill rows),
and that failure reproduces on a pristine checkout. It is not absorbed here.

**The re-export needed one environment workaround, recorded because a reader
reproducing this will hit it.** `analyzeHeadless` refuses the committed project
with `NotOwnerException: Project is owned by dave` — `ec/ghidra/project/ec.rep/
project.prp` carries `OWNER="dave"` and the pipeline runs as a different user.
`JAVA_TOOL_OPTIONS="-Duser.name=dave"` makes the JVM report the name the
committed project expects, and the default export-only mode then runs with the
`.gpr`/`.rep` never opened for writing. **No project file was edited**; this is
an environment setting and nothing in the repository depends on it.

**`ec/ghidra/reassembly.csv` needed no regeneration**, which is worth saying
because "re-run the digests" invites the reader to assume every report moves.
`verify_reassembly.py` hashes the parsed instruction stream, not the file bytes,
and an annotation change alters only the header.

**`docs/findings.md` §17's `786 / 684 / 497` census is stale and was not chased.**
It is a record of a specific build run in a frozen file, and a re-export moves
`pd`'s figure again. Reported, not absorbed.
