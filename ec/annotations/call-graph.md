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
| function rows in `decompiled/index.csv` | 2,710 |
| of those, still `FUN_*` | 814 |
| transfer instructions in the `.asm` listings | 5,027 |
| — `lcall` / `ljmp` / `ajmp` / `acall` | 3,854 / 1,063 / 74 / 36 |
| — resolving to an index row | 4,924 |
| distinct targets reaching a row | 1,841 |
| transfer sites whose target is no index row | 103, over 80 targets |
| targets still anonymous | 475 |
| inbound sites to those | 787 |
| anonymous rows no direct transfer reaches | 339 |
| distinct `FUN_*` callees the `.c` files name | 822 |
| anonymous callees a comment names | 141 |
| comments that name one | 315 |

**The 475 and the 822 are two framings of related things, and neither is "the"
count.** The first is decoded out of the committed `.asm` listings; the second
is read off the `.c` export. The `.c` figure is larger because the decompiler
emits calls the listing does not carry directly. It is also the framing that
*cannot* be ranked on: a `.c` names its callees, so the moment 0x05E8 is
annotated the two frames disagree about whether anything reaches it. This
follows the precedent `../tools/audit_call_targets.py` sets by reporting an
upper bound and a decode count for every figure and never one.

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

**Two known distortions in the citation count, both real and both left in.**

- *A comment that refutes the decompile still writes the address.* Seven rows
  in `bank1` share one sentence ending "is not supported by these
  instructions", and every one of them names 0x110A and 0x00CF inside the body
  it is rejecting. Each address has **8 citations, of which those seven are
  the artifact**; the eighth is `common,0x0070`, whose comment records the 0x110A
  call as the bank-0 select and tail-jumps to 0x00CF, both supportively. So 7 of
  8, not all 8, and for 0x110A that eighth is the only citation that is not part
  of the artifact — which is why the two addresses rank near the top of the
  primary key for a reason that has little to do with being worth reading.
  Rewriting those comments to substitute a new name would assert the very call
  the comment denies, so they were left alone.
- *Naming a function removes it from the count.* `cited_by` is defined over
  anonymous callees only, so a row's count goes to 0 the moment it is
  annotated, whether or not its citing comments changed. The `citing` column is
  the work list; it is empty for a row that has been done.

**The citing comments keep their bare addresses, on purpose.** 1,300 comments
already cite an already-named function by address — the figure is on the
committed tree, and it rises every time a function is named, because a new row
tends to cite helpers that are already named — so replacing the address with a
name in the tranche's 109 citing comments would leave the export internally
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

**Twelve of the 44 are `type=unresolved`**, and that is a result, not a gap.
Five are genuinely undecodable from the bytes: 0x9C47 and 0xD2BE are a bare
`ret`; 0x4A76, 0x3B4E and 0x7177 are one to three instructions with no `ret`,
because Ghidra's function boundary on this firmware cuts through straight-line
code. Six are large enough that a first reading pass cannot honestly reach a
role: 0xD757 (282 bytes), 0x8931 (474), 0xDE83 (155), 0xBD45 (170), 0xE656
(117) and 0xCD80 (51). The twelfth is 0x0200, whose listing is 19 bytes and a
header-marked fragment of a longer routine. Each of those rows says what the
entry does, names the registers it touches, and says what is not decoded. A
plausible name would have been the one thing a row must never do.

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

**The work list is the `annotated=no` rows**, 475 of them, of which **141 are
cited** by a comment and so are the ones a reader can trace to a sentence that
needs them. The rest are reachable but uncited: worth naming, not yet blocking
any explanation. The ranking is the order to work them in.

**339 anonymous rows have no direct transfer reaching them at all** — 339 of
the 814 `FUN_*` rows, reached by function pointer, by a dispatch table, or not
reached. **That is a limit of this method and not a claim that they are
unreachable.** The same goes for the 103 transfer sites whose target is no
index row: those are branches into straight-line code, not evidence of a
missing function. They are counted and reported rather than dropped or
guessed, because a target resolving to more than one scope row is left
unresolved rather than assigned to the caller's bank.

**A count is a ranking, not evidence of what a function does.** 0x110A is
worth two `lcall`s of attention; that says it is cheap to read, not that it is a
bank switch. Each tranche row says what its own bytes do and no further, and
`unresolved` is a row that declines to guess.

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
`.c`-named `FUN_*` callees 836 → 822 and citing comments 314 → 315. The
already-named citation count in §"The citing comments" is 1,279 on the tranche's
tree and 1,300 on the merged one — a comment row citing at least one named
index row by canonical-width address, its own included, which is the
`citations()` match in `../tools/call_graph.py` with the `FUN_*` test inverted.
The one between them is the tranche's own `bank0,0x0EA2`: naming 0x05E8, 0x0EE8
and 0x05EF turned a comment that cited nothing already-named into one that cites
three, and it is counted here like any other. The 1,299 this section first
carried was the figure before that row was annotated; re-derive it with the
`citations()` match rather than carrying either number forward.

## Adding the next tranche

Same path as the first sweep, documented in `README.md`: slice the
`annotated=no` rows, annotate one shard at a time, verify each shard against
its own `.asm`, and merge. `../tools/call_graph.py --check` then confirms the
table still matches the listings, and the build confirms every new
`(scope, addr)` resolves to an exported function with a non-empty `evidence`
cell.

**Not done here, and it is a one-line follow-through for a human:**
`call_graph.py --check` is not wired into
`.github/scripts/agent-gates.sh`'s `check_ghidra_tooling` list. This change
touches nothing under `.github/`, because the pipeline's push token has no
`workflow` scope and a branch that does fails at the end rather than the start.
Adding it means adding `ec/tools/call_graph.py` to that tool loop with its own
`case` branch, like `gen_xdata_symbols.py`'s: the tool takes no `--work` and
has no scratch directory, so it does not fit the loop's default branch, which
passes `--work "$scratch" --check && --work "$scratch" --self-test`. Both modes
need no Ghidra and no network, which is what would let the check live in the
cheap gate at all.
