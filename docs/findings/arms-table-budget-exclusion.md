# The arms table stays out of the budget census because no committed row ends on a budget, and that is a measurement rather than a promise (issue #866)

(2026-10-02. Static reading of a committed CSV through the two committed
tools that write and would have to reproduce it. No capture opened, no EC, no
hardware, no Windows, no `registers.yaml` row touched, and no annotation CSV
regenerated.)

[`walk-window-terminators.md`](walk-window-terminators.md) §What was measured
and `ec/tools/walk_budget_census.py`'s module docstring both decline to census
`ec/annotations/manual-fan-ctrl-0751-arms.csv`'s `window` cells, and both gave
the same reason: that those cells "are arm listings that end on a flow opcode
by construction". The tool does not offer that guarantee. `walk_branch_arms.py`
gives every arm an instruction budget, `END_BUDGET` is one of the four reasons
it groups as a cut, and an arm can end on it.

**The exclusion rests on a fact about the committed file, and §2 records it
and `ec/tools/test_walk_budget_census.py`'s
`test_no_committed_arm_ends_on_the_instruction_budget` holds it.** §3 names
what the table's `partial: DPTR built at run time` rows cost a reader — the
sibling of the class A shape
[`walk_budget_census.py`](../../ec/tools/walk_budget_census.py) exists to name,
on a table that census declined to look at.

## 1. The retraction

Three places carried the sentence. All three now carry the measurement, and
the wrong version is quoted here rather than edited out of the record:

> its 171 cells are arm listings that end on a flow opcode by construction

— `ec/tools/walk_budget_census.py`, in the **Two populations, kept apart.**
paragraph of the module docstring, before issue #866.

> its cells are arm listings that end on a flow opcode by construction

— [`walk-window-terminators.md`](walk-window-terminators.md) §What was
measured, in the paragraph beginning "`manual-fan-ctrl-0751-arms.csv` is not
in the table above", before issue #866.

> a different producer, keyed on site_runtime, ending on a flow opcode by
> construction

— the comment on `test_the_arms_table_is_not_one_of_them` in
`ec/tools/test_walk_budget_census.py`, before issue #866.

**The clause is wrong, and it is wrong in the direction that matters.** "By
construction" is a claim about the module: it says no arm can end on the
budget, so the exclusion needs no evidence. The opposite is true of the code —
the budget is a real cut with its own token and its own guard — so the
exclusion was resting on a guarantee that a reader who opened the producer
would find does not exist.

Where each piece of that lives in `ec/tools/walk_branch_arms.py`:

| what | where |
|---|---|
| the budget, `--max-insns`, default 500 | `main()`'s argument declaration |
| where it is spent | `descend()`, which takes `budget = max_insns` and ends an arm with `arm.end(f"{END_BUDGET} at 0x{pc:04X}")` when the guard fires, decrementing per decoded instruction |
| the token | `END_BUDGET = "instruction budget"`, alongside the other `END_*` stop reasons |
| the grouping as a cut | `CUTS = (END_DEPTH, END_BUDGET, END_INDIRECT, END_IMAGE)` — "stop reasons that mean the walk gave up rather than finished" |
| where a cut becomes a `status` | `arm_status()`, which prefixes `"cut: "`, and `callee_row()`, which prefixes `"unresolved: "` |

Those last two prefixes are why a case that checks only one of them would pass
on a cut row of the other kind: the two row builders in `write_csv()` spell a
cut differently.

## 2. The measured replacement

Over the committed `manual-fan-ctrl-0751-arms.csv`, on the default bounds:

- **171 rows**, and no `ends` cell carries `END_BUDGET` or any other member of
  `CUTS`.
- **No `status` is a cut**: none begins with a `CUTS` token, and none begins
  with `"cut: "` or `"unresolved: "`.
- **The largest committed arm decodes 429 instructions against that default of
  500**, so the run that produced the table did not come near the budget on
  any row.

**This is a per-row property and not a census total, and that is the point.**
Which rows exist moves on every regeneration, and a number of them is a value
every future regeneration has to edit — the shape `CLAUDE.md` warns against.
The case asserts that *no row* carries a cut, not that there are 171 of them
or that none of 171 was cut; it asserts the headroom, which no row count
implies.

**The headroom is what makes the exclusion re-derive.** It is read off
`walk_branch_arms.py`'s own `add_argument("--max-insns", ...)` rather than
written into the test, because the help string's "(default 500, …)" is prose
hand-written next to the value and would keep reading 500 after the value
moved. Lower the default below 429 and the case goes red, naming the committed
table as re-cut rather than widening the assertion; nothing else in the suite
would notice, which is the whole subject of this page. Both directions were
run: red at a default of 400, green at 500.

**The first thing the case asserts is `END_BUDGET in CUTS`.** Without it the
per-row check would still be true if the token were renamed or dropped from
`CUTS` — vacuously, and for a different reason each time. The case reads the
vocabulary off the producer module rather than transcribing the strings, so
the strings cannot drift out from under it either.

**The population is asserted non-empty before it is checked.** A rule over
nothing reports green, which is the `census_test_line_pins.py` convention and
the shape `test_walk_budget_census.py` already follows for its own baseline:
a check that measured nothing has to say so rather than pass.

## 3. The 49, and what a `partial` row costs a reader

`status` over the 171 rows is 88 `resolved`, 49 `partial`, 34 `complete` — and
the split is not spread across the table the way those three numbers read.
**Every `complete` row is a `kind=arm` row and every `arm` row is `complete`;
all 137 `callee` rows split 88 / 49.** `partial` is a word `callee_row()` has
and `arm_status()` does not, so the 49 are a property of the callee population
and of nothing else — and the cost is that a reader who takes `complete` to
mean "nothing was left unattributed" is wrong on **5 of the 34 site arms**,
which record `unattributed` of 2 and still read `complete`, because
`arm_status()` reports cuts and has no `partial` to give.

What one costs a reader:

- **The window ends where DPTR stops being known.** `descend()` clears the
  pointer on a store to DPL or DPH and records
  `"DPTR built at run time (a store to DPL/DPH)"` in `ends`. The new
  `dp_causes` column says which of the causes took the pointer away for each
  unattributed store, so the 49 no longer all read as this one.
- **Every later `movx` is counted `unattributed` rather than charged to the
  site**, on purpose: "unattributed" is the safe direction and a wrong address
  is not. Over the 49 the count is 1 on 29 rows and 2 on 20.
- **So the row's `xdata` column is a lower bound on what the arm touches.**
  This is the sentence a reader needs and the table does not carry: **20 of the
  49 have an empty `xdata` cell**, every `movx` in them landing
  `unattributed`. An empty cell there does not mean the arm touched no XDATA;
  it means the arm touched XDATA through a pointer this walk could not
  resolve. A negative read off that column is a statement about the method and
  not about the firmware, and the 15 empty `xdata` cells among the 88
  `resolved` rows are a different thing again — a resolved row has no
  unattributed access to have, so an empty cell there is at least consistent
  with the arm being XDATA-silent.

### The 26, the 49, and the 13 between them

26 rows carry `"DPTR built at run time (a store to DPL/DPH)"` in `ends`. That
is **not** a subset of the 49: the two sets intersect in **13**. Of the 26, 9
are `complete` (all of them site arms, which arrive at `descend()` holding the
site's DPTR and so keep attributing), 4 are `resolved`, and **36 of the 49
carry no such `ends` note at all**.

The cause is one line. `callee_row()` calls `descend()` with `dptr=None`,
because a callee inherits the caller's DPTR and that value is not carried into
the row. A callee whose first `movx` is `movx a,@dptr` therefore starts already
unknown, and it starts unknown without anything having gone wrong: **a row
carrying no note had no store of the form the walk recognises**, which for
most of these 36 is the ordinary case — a callee handed an unknown pointer —
rather than a gap in the walk. (The next section is about the one form it does
not recognise.) **So the `ends` cell and the `status` cell are answering two
different questions, and neither is a subset of the other.** Counting the note
to stand in for the status — which the shape of the two columns invites —
understates the population by 36 rows.

> **Corrected 2026-10-03 (issue #242).** This section read "The 61", "76
> `resolved`", "7 of the 34 site arms", a 1/2/4 tally, "the 16 between them"
> and "45 of the 61". Every one of those moved when `descend()` began
> following `inc dptr`: stores that had been charged to no address because the
> pointer went unknown at an increment now carry one, which took twelve callee
> rows out of `partial` and two site arms out of having an `unattributed` at
> all. The `status` vocabulary also widened — `partial:` now names the cause
> and can name more than one — so the three numbers above are a count of rows
> starting with `partial`, which is the population this section is about. The
> argument is unchanged and the arithmetic under it has been re-derived from
> the committed table.

### The `ends` note is not a complete record, and one form is missing

Measuring the 45 above turned up a second finding, in the other tool.
`walk_branch_arms._dptr_write()` and
`trace_xdata_refs.is_dptr_rebuild()` do not give the same answer for every
opcode, and over all 256 crossed with `0x82`, `0x83` and `0x00` there are three
kinds of disagreement:

- **`pop direct` (`0xD0`).** `is_dptr_rebuild()` answers True for
  `pop 0x82`; `_dptr_write()` answers False. #517 is what added `0xD0` to the
  census side, and `pop 0x82 ; pop 0x83` is the sequence
  [`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md)'s `0xD0` row
  spells out and `ec/tools/test_dptr_rebuild_guard.py`'s module docstring
  names ("past `pop 0x83`"). **This one is live here.**
- **`0xA8`–`0xAF` (`mov @Ri,A`).** `_dptr_write()` groups these with the
  direct stores, but their operand byte is the register number rather than a
  direct address, and `is_dptr_rebuild()` correctly answers False. **This one
  is latent**: no such instruction reaches a walked arm on this image.
- **`0x90` (`mov dptr,#imm16`).** Also False against True, and it does not
  count, because nothing asks: `descend()` takes `MOV_DPTR` in its own branch,
  where it sets `dp` from the immediate rather than clearing it, so
  `_dptr_write()` is never reached with it. **This one is not reachable in the
  walk.**

> **Corrected 2026-10-05 (issue #1154). All three clauses of the `0xA8`–`0xAF`
> bullet above are now wrong, in the same direction.** The block is
> **`MOV Rn,direct`**, not `mov @Ri,A`, so its operand byte **is** a `direct`
> address rather than a register number — `0x82` (DPL) and `0x83` (DPH) are its
> commonest operands — and it *loads a register from* that address, so DPTR is a
> source and is left alone. `walk_branch_arms._dptr_write()` no longer groups the
> block with the direct stores, which retires the disagreement itself: it and
> `is_dptr_rebuild()` now agree on every opcode in the range, so that bullet no
> longer describes a third kind. `a8af_operand_role.py` derives the reading from
> the committed listings alone and
> [`a8-af-block-length-and-operand.md`](a8-af-block-length-and-operand.md) has
> the measurement.
>
> **The "latent" clause is retired, and its retirement is this branch's doing.**
> It said no such instruction reaches a walked arm. `bank_attribution.py`'s walk
> does reach one, and now follows it: `ac 83` and `ae 83` at `0x0F7A`/`0x0F98`
> are `mov r4,DPH` / `mov r6,DPH`, and the old predicate mistook each for a store
> *to* DPH, so it killed the pointer at those two rows. With the block read as a
> load the pointer survives, the `0x0F95` clear loop's own `inc dptr` (`0x0FA2`)
> runs, and the walk steps `0x9000` to `0x9001`. Re-running
> `bank_attribution.py --self-test` reproduces the causality in both directions:
> with the old predicate restored in-process the leftover set is `0x9000` alone,
> and with the corrected one it is `0x9000, 0x9001`. `0x9001` is the second cell
> of the same clear loop, not a route into code, which is why
> `bank_attribution.XDATA_CLEAR_IMMEDIATES` now names it rather than letting it
> read as a missed bank of code.
>
> **What did not move, and is why this file's own figures still stand.** That
> walk is not the one this correction is about. The committed
> `manual-fan-ctrl-0751-arms.csv` is byte-identical under the corrected
> predicate —
> `walk_branch_arms.py ec/firmware/GMxMGxx_11.800 0x0751 --callee-depth 1 --csv
> | diff - ec/annotations/manual-fan-ctrl-0751-arms.csv` is empty — so §3's
> figures, its `ends` arithmetic and §5's exclusion are all untouched, and the
> `pop direct` finding above still stands as written. No `0xA8`–`0xAF`
> instruction in any committed arm `window` names `0x82` or `0x83`, which is why
> removing the block from `_dptr_write()` changed nothing here; the instructions
> that reach DPTR through this block are in the closure `bank_attribution.py`
> grows, not in these arms. Both walks call the same predicate, and the retracted
> clause was written about "a walked arm" without saying which walk — that
> ambiguity is what let a claim scoped to one walk stand as a claim about the
> image.

Adding `0xD0` to `_dptr_write()` and re-running the reproducing command moves
**`ends` on 5 of the 171 rows** and **drops a `code_pointers` entry of `0x0A49`
from the two `0x93CA` arm rows**, and changes nothing else: `xdata`,
`unattributed` and `status` are byte-identical on every row. So §3's reading of
the `partial` population survives this untouched, and the damage is confined to
two columns.

**What the dropped `code_pointers` entry is.** Both rows' `code_pointers` cell
reads `0x0A49`, and both `window` cells contain the sequence that puts it
there:

```
0x940B mov dptr,#0x0a49
0x940E movx a,@dptr
0x9410 pop 0x82        ; DPL -- the pointer is rebuilt from here on
0x9412 pop 0x83        ; DPH
0x9418 movc a,@a+dptr  ; ... and this is what 0x0A49 is credited to
```

The walk held `dp = 0x0A49` straight across both pops, so a `movc` behind them
was credited as a CODE pointer through a pointer it had no business still
holding. `descend()`'s own rule is that a store to DPL or DPH makes the
pointer unknown, and its `movc` arm then drops the credit — **that is the
"confident wrong answer" the tool's module docstring says it refuses to
produce, produced by the one store form its predicate does not name.** It is a
finding, not a fix: changing `_dptr_write()` is a change to a shared tool that
issue #866 did not ask for, and the table it would move is one nothing here has
grounds to re-cut.

### The same bytes, two vocabularies

This is the shape
[`trace_xdata_refs.py`](../../ec/tools/trace_xdata_refs.py) was widened to
cover in issue #517, reaching the arms table's other tool:

| | `trace_xdata_refs.py` | `walk_branch_arms.py` |
|---|---|---|
| what it does at a run-time-built DPTR | **ends the window** — `walk_why()` tests `is_dptr_rebuild()` and returns `RELOAD_END` | **continues**, clearing `dp` and counting every later `movx` as `unattributed` |
| how it says so | one token, `RELOAD_END = "DPTR reloaded"`, covering every construction `is_dptr_rebuild()` names | two cells and no token: an `ends` note saying which instruction did it, and a `status` of `partial: …` for the row as a whole |
| the budget cut | `budget_end(max_insns)`, the fifth terminator, a function of one number rather than a fifth string | `END_BUDGET`, one of `CUTS` |

**The difference is what makes class A empty in the committed census.** Because
`walk_why()` *ends* the window on a reload, no `access` cell ever counts an
access through a pointer the site did not set — which is why
`walk_budget_census.py`'s own docstring can say nothing in the committed census
is class A, and why its rows with an indexed access are no longer truncated at
all. `walk_branch_arms` counts the same `movx` as `unattributed` and marks the
row `partial`, which is a stricter answer about more bytes.

**Two vocabularies for one event is deliberate on both sides**, and both
modules' docstrings say so: splitting one event into two tokens is the
duplication the names exist to prevent within a tool. Across the two tools the
split is a difference in scope — an 8-instruction window that must stop, and a
whole-arm reachability walk that must not.

### One citation of the issue's does not land

The issue points at `trace_xdata_refs.py:316` for the shape a census cannot
see. **That pointer does not land on anything DPTR-related**; the line number
has moved since the issue was filed, and re-pinning it to whatever is there
now would make this page the kind of citation it is correcting. The symbols
that carry the shape are `is_dptr_rebuild()`, `RELOAD_END` and `TERMINATORS`,
and `budget_end()`. They are cited here by name for that reason, and this
repository's own rule is to cite by name rather than by line anyway.

## 4. What this does not establish

- **Nothing about the EC.** Every input is a committed CSV and two committed
  tools; no register was read back, no capture opened, no hardware or Windows
  involved, and `ec/annotations/registers.yaml` is untouched.
- **No claim about the budget.** Whether `--max-insns` should be 500, or
  anything else, is not asked here. The headroom §2 records is recorded as
  headroom and nothing more is read off it.
- **No claim that the arms table could be folded into the census.**
  `walk_budget_census.read_sites()` requires `addr` and `file_offset`, and this
  table is keyed on `site_runtime`; a row keyed that way is not a row the
  census could re-derive at `BUDGET` anyway. Naming the shape is the work;
  supporting the table is a different one.
- **The committed table is not regenerated and no tool behaviour changes.**
  `walk_branch_arms.py` is untouched, so
  `python3 ec/tools/walk_branch_arms.py --self-test` and
  `python3 ec/tools/test_walk_branch_arms.py` stay green for the same reason
  they were before: this is prose and a test, not a behaviour change.

## 5. What does and does not hold the arms table

**No check re-derives `manual-fan-ctrl-0751-arms.csv` byte for byte.**
`walk_branch_arms.py` has no `--check` mode, and the nine site tables this
census does read are held byte for byte by tools that have one. Three things
stand in for that and none is a gate: `census_xdata_writers.arms_gap()`
sums the file's `unattributed` column per `addr`, held by
`test_census_xdata_writers.py`;
`test_walk_branch_arms.py::UnknownDptrCauseTests` reads both arms tables and
holds the claim that every unattributed store carries a declared cause, which
is a property of the cells rather than of their bytes; and
[`manual-fan-ctrl-0751.md`](../../ec/annotations/manual-fan-ctrl-0751.md)
carries the `diff -` that reproduces the table, as a procedure for a person to
run rather than as a command anything calls.

**So the case added here is the first check that reads the `ends`, `status`
and `insns` columns at all**, and it holds a property of the file rather than
its bytes — which is the property the exclusion needs and a byte comparison
would not have supplied. A `--check` is a real gap and is named here as the
natural follow-up rather than absorbed: it is a change to a shared tool that no
issue has asked for.

## 6. Reproducing every figure above

```
python3 -m unittest discover -s ec/tools -p test_walk_budget_census.py
python3 ec/tools/walk_branch_arms.py --self-test ec/firmware/GMxMGxx_11.800
python3 ec/tools/test_walk_branch_arms.py
python3 ec/tools/gen_findings_index.py --check
python3 ec/tools/check_no_append_logs.py
python3 ec/tools/check_findings_frozen.py
```

The counts are one `csv.DictReader` pass over the committed CSV, and
`collections.Counter` over the columns named beside them:

```python
import csv, collections
with open("ec/annotations/manual-fan-ctrl-0751-arms.csv", newline="") as f:
    rows = list(csv.DictReader(f))
print(len(rows), collections.Counter(r["status"] for r in rows))
print(collections.Counter((r["kind"], r["status"]) for r in rows))
print(max(int(r["insns"]) for r in rows))
```

The test holds them per row rather than as figures, and
`bash tools/run-tests.sh` is what runs it. No Ghidra, no `analyzeHeadless`, no
`ilspycmd`, no image beyond the committed firmware — and the two cases that
read the committed CSV need no image at all.

**Three red directions were run, each restored afterwards.** Lowering
`main()`'s `--max-insns` default to 400: the case fails with the largest arm
and the current default both named. Dropping `END_BUDGET` from `CUTS`: it fails
on the guard assertion, naming what `CUTS` then held. Adding one row carrying
`instruction budget at 0x1234` in `ends` and `cut: …` in `status`: it fails on
the per-row check, naming the row. **A check that cannot go red is the thing
this page is about**, so all three were run rather than the first assumed.

The `pop direct` measurement above is the same shape — `_dptr_write()` edited
in a scratch copy, the reproducing command re-run, the diff read, and the tool
restored. Both runs were compared column by column over all 171 rows rather
than by eye, and the committed table was first confirmed to come out of the
unmodified tool with an empty diff, so the comparison has a baseline.

## 7. Follow-ups this opens

Stated rather than acted on, per the mission's rule that a finding which opens
a question says so.

1. **`walk_branch_arms._dptr_write()` does not name `pop direct`.** §3 measures
   what it costs on the committed table and nothing more. Whether the fix is to
   widen the predicate or to delegate to `trace_xdata_refs.is_dptr_rebuild()` —
   which is the duplication the census side already avoids — is a question
   about that tool. The `0xA8`–`0xAF` clause used to be named here as wanting the
   same answer; #1154 resolved it in the other direction, by removing that block
   from the predicate rather than adding to it, so there is no second consumer
   left to generalise over.
2. **No `--check` for the arms table** (§5). Named in §5 and unchanged by it.
