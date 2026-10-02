# Splitting the call-graph groups at the BL51 bank-select boundary (issue #444)

## What this is

`ec/tools/group_functions.py` now has a split mode that removes the bank-select
trampoline edges from the graph before its union-find runs, so the
`callgraph_*` groups are components of a graph with that boundary cut rather
than of the committed listing graph itself. The mode is `--split trampoline`,
it is the **default**, and `ec/annotations/function-groups.csv` has been
regenerated in it.

The headline result is a negative one, and it is the finding rather than a
disappointment: **the cut is a partial cause of two of the three large
components and no cause at all of the third.** The largest component does not
move. Read the rest of this file before quoting any of the numbers, because
the interesting ones are the ones that did not change.

Everything here is read out of committed `.asm` listings and committed CSVs.
Nothing was executed, no bank was switched, no register was read, and no
hardware was reachable. Where a figure is a count of the tree rather than of
the committed files, the command that produced it is named.

## Reproducing it

```
python3 ec/tools/bl51_trampolines.py
python3 ec/tools/group_functions.py --report
python3 ec/tools/group_functions.py --check
python3 ec/tools/group_functions.py --self-test
python3 ec/tools/test_trampoline_split.py
```

## The rule, and what it counts

The trampolines are recognised by listing shape, as `subsystems.md` §4
already states it: a function whose whole body is `mov DPTR,#imm16` followed by
`ljmp <a BL51 stub>`. `ec/tools/bl51_trampolines.py` is the rule and its
census; `group_functions.py` imports it rather than repeating it.

**The stub set is pinned, and pinning it is what makes the rule a rule.**
`mov DPTR,#imm16` followed by `ljmp <anything>` matches more rows than the
pinned form does, and the difference is not noise — a function that loads DPTR
and jumps somewhere that is not a bank-select stub is doing something else
with the address. The pin is what makes the difference *measurable*:
`is_trampoline(path, None)` asks the unpinned question, and the census prints
both answers.

The pin is to four addresses, derived from the annotation rows whose name
matches `bl51_bank_select_[0-9]+` rather than written out, so it cannot drift
away from `ghidra-functions.csv`. The match is on the **whole name** because
the same file carries `bl51_bank_select_0_tail_110a_wrapper` at `common`
`0x1048`, which shares the prefix and is a wrapper *around* a stub; a prefix
match sweeps it in and makes the set five.

The census, on the tree this change was measured against:

| figure | count |
|---|---|
| listings of that shape across the export | 290 |
| … naming a BL51 stub | 282 (261 to `0x1100`, 21 to `0x1114`) |
| … naming something else | 8 |
| annotated rows of that shape | 93 |
| … naming a BL51 stub | **85** (65 to `0x1100`, 20 to `0x1114`) |
| … naming something else — what the pin is worth | 8 |

**The first two rows reproduce `subsystems.md` §4 exactly** (290, 282, 261,
21), which is the check that the shape rule is the same rule §4 measured.
`§4`'s *annotated* figure — "**82** of those 282 are annotated (62 and 20
respectively)" — is now stale for the ordinary reason: three more have been
annotated since. The re-derived figure is **85 (65 and 20)**. `subsystems.md` is
a long shared file and §4 says of itself that its census is not gate-held, so
the correction is recorded here rather than edited into it.

Before the regeneration the 85 landed as 30 `bank-switch-trampolines`, 7
`dispatch-tables` and 48 in the single `callgraph_bank1_1738` component; the
census now prints where they sit in the regenerated file. A seed labels a row
without removing its edges, which is why the 48 were in the graph at all, and
why a rule keyed on the `type` column would have fixed nothing — the 30
`type=bank-switch` rows are exactly the ones a `type`-keyed rule skips.

## The mode is the default, and why

`--split {trampoline,none}`, default `trampoline`. It is not an opt-in flag
because `.github/scripts/agent-gates.sh` runs `group_functions.py --check &&
--self-test` with **no arguments**. A mode that had to be named at every call
site would either need a gate edit or leave the committed file and the gate
disagreeing. `--apply --split=none` is **refused** with a message naming the
committed basis, because the file it would write is one `--check` then calls
drift on every row the cut moved; `--report --split=none` is how to look at
that grouping without writing it, and `--check --split=none` stays available to
reproduce a pre-split checkout (against a post-split file it is expected to be
red, and that is the drift half working).

## What the cut does, measured

From `group_functions.py --report` on the EC. Component sizes are `cluster()`'s
own components at or above `min_size=4`; the `callgraph` row count is a
different population, because a component holds every member the union found
while a `callgraph` group holds the members no seed claimed.

| | uncut | cut |
|---|---|---|
| largest component | 505 | **505** |
| second | 408 | 376 |
| third | 394 | 373 |
| fourth | 37 | 16 |
| components at or above `min_size` | 16 | 20 |
| rows carrying `group_basis=callgraph` | 1102 | 1083 |
| `callgraph` group sizes (what `--report` prints) | 370 / 327 / 323 | **370** / 309 / 307 |

Rows that change group or basis: **49**. Thirty stay `callgraph` in a different
component and 19 fall to `ungrouped` (`ungrouped` 463 → 482).

The edge populations move too, and the two that do are reported separately on
purpose: `proxy_edges` 199 → 124, `cross_region` unchanged at 27, and the cut's
own 85 edges printed on a line of their own. `reached_only_by_bank` keeps 19
rows but changes membership (`0x1114` out, `0x1100` in), so the two
`ungrouped` reasons stay coherent on their own. The report's "found then cut by
the proxy rule" line is **not** where the cut's edges are counted, and a
`--self-test` case holds that wording: attributing this tool's own edit to the
banking rule would be the same conflation `proxy_edges` was split out of
`cross_region` to stop, one edit later.

**The BIOS is inert, and that is a measurement.** `bios/annotations/
function-groups.csv` has 0 `callgraph` rows and no listing matches the shape, so
`--apply` rewrote it byte for byte. That is what the report prints rather than
a reason about x86-64.

### The largest blob does not move, and that is the finding

`callgraph_pd_0003` holds 370 of the 1,961 EC rows and the cut leaves it at
370. Forty-eight in-graph trampolines sit in the bank1 component, which goes
323 → 309, so the trampoline edges account for 14 rows of that one and
something else holds the rest. The `bank0` component goes 327 → 307.

So: **a measured partial cause of two of the three large components, and no
cause at all of the third.** That is the whole result, and it is why this
change does not claim the blobs are solved. What actually holds them together is
not established here and is **not found by this method** — the cut removes
edges at one boundary and the components barely move, which is a statement
about this cut, not a statement that no cut would help.

## Drop, not contract

The issue offers "contracts **or** drops". It drops, and the reason is measured
rather than chosen: **union-find over the transitive closure is unchanged by
contracting one of its own edges**, so contracting `caller → trampoline → stub`
into `caller → stub` returns exactly the same components and cannot split
anything. The operation would be a no-op that reads like a result. Recorded as
a negative finding because "contraction cannot split a union-find" is the kind
of thing the next reader will otherwise re-derive.

What is dropped is the **trampoline's own edge to the stub**. The trampoline
keeps whatever joins it to its callers, which are the edges that say anything
about the code around it. That is why the cut removes a proxy edge at all: a
stub lives below `BANK_BASE`, so the tail jump is the edge that would otherwise
land on the `PROXY_SCOPE` proxy node, one per (scope, stub address), and that
shared node is how every trampoline in a bank reaching the same stub became
joined to every other.

**And the contraction would have been worse than a no-op, not merely useless.**
`bl51_trampolines.py` prints the population: of the 85 annotated trampolines,
**29 carry a DPTR immediate that also carries a row in the other bank** (23
from `bank1`, 6 from `bank0`). A contraction rewrites the tail jump to point at
that immediate instead of at the stub, so the address becomes an edge target —
and at those 29 that edge is exactly the bucket-B ambiguity
`group_functions.py` exists to refuse, on a function whose entire purpose is to
reach the other image.

The `--self-test` fixture that holds this is built on precisely that shape, and
its three properties are all load-bearing by being *safe without the cut*: a DPTR
immediate below the bank base can be contracted safely (the per-bank proxy
already keeps the banks apart); an immediate in only one bank can be contracted
safely (the same-bank branch joins the one row that exists); only an immediate
in both images is the ambiguity. A fixture missing any one of them passes
against the bug it is written for.

## Why not strong articulation points

The issue offers the split and SAP as alternatives. This takes the trampoline
cut, for two reasons, and both are worth keeping:

- **SAP has no committed oracle here.** A SAP partition would have to be
  validated against something, and there is nothing committed to validate it
  against — which is what the 85-row shape census *is*, and the reason it was
  the tractable half of the choice.
- **The measurement says the trampoline cut is a partial cause**, so if the
  blobs are to be broken up further the next cut has to be somewhere SAP can
  reach and this one cannot. That is a follow-up issue, not this one.

A follow-up should be opened for it. What it would need and does not have yet
is an oracle: a second cut whose result can be checked against something
committed rather than against a plausible story about the firmware.

## What would still have to be checked

- **Which bank a trampoline reaches is not established**, and nothing here
  establishes it. `subsystems.md` §12 note 4 carries the caveat forward
  unchanged: the same address means different bytes in each bank, so neither
  the caller's `lcall` nor the trampoline's `mov DPTR` names a bank. The new
  check's scope is "the cut did not join two regions", which is a property of
  the graph and **not** a bank mapping.
- **What holds the largest component together is not found by this method.**
  One cut at one boundary was measured; the component it did not move is
  still unexplained, and nothing here says no other cut would move it.
- **Ghidra's function boundaries are a hypothesis**
  (`ec/annotations/bank-call-audit.md` §1), so an edge can be an artifact of
  where a boundary was drawn. The shape rule reads whole committed listings,
  which makes it independent of that — and which is also why a listing Ghidra
  drew differently tomorrow could move the count.
- **`subsystems.md` §4's "82 of those 282 are annotated" is stale** and is
  corrected above rather than in place.