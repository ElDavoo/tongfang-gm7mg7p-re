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
| anonymous callees a comment names | 99 |
| comments that name one | 142 |
| — candidate (callee, comment) pairs, before the frame gate | 382 |
| — kept / rejected / undecided by it | 152 / 185 / 45 |

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
`undecided`** — 45 pairs today — rather than defaulted either way. The
rejected and undecided populations are printed by the tool and are never
dropped, because a guard that silently discards what it rejects cannot be told
apart from one that rejects too much. **Each undecided pair has a recorded
verdict in
[`../../docs/findings/citation-undecided-verdicts.md`](../../docs/findings/citation-undecided-verdicts.md)**,
one row each, settled on the listing or on the committed firmware bytes. Those
are readings of the *sentences*, not reclassifications: the tool still reports
the pair as undecided, and an undecided line carries the frame verdicts its
mentions drew rather than a bare `--`. The count has moved once, to 44, and
only because `sjmp` joined `CODE_VERB` for the one committed comment that
needed it (`bank1,9B03`'s "it ends in an sjmp to 0x9B3C"). `sjmp` is **not** a
member of `TRANSFERS` above and must not become one: a PC-relative branch is
not a call, and a comment's lexicon and this tool's transfer set are
deliberately different sets.

**Two further signals sit beside the frame, and the second is not lexical.** A
`pd` comment cannot cite an EC row at all: the dump holds two 8051 programs
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

**Two known distortions in the citation count, both real and both left in.**

- *A comment that refutes the decompile still writes the address.* Seven rows
  in `bank1` share one sentence ending "is not supported by these
  instructions", and every one of them names 0x110A, 0x158E, 0x0F75, 0x1594
  and 0x00CF inside the body it is rejecting. The frame gate keeps those
  mentions, and it is right to: each one does read as a call, to a code
  address, in a call enumeration. What is wrong is the **caller** — the
  address the comment is attached to is `0xFF` fill, not the reset path those
  calls live in. 0x110A and 0x00CF have since been named and left the
  candidate set; the three that remain, **0x0F75, 0x158E and 0x1594, are
  ranks 1–3 with 7 citations each, all seven of them this artifact**, and the
  eighth citation (`common,0x0070`, which records the calls supportively) is
  `undecided`, because the aside between its governing verb and the mention is
  longer than the window. **So the top of the ranking is now right about the
  addresses and still wrong about who calls them** — the second, distinct
  defect, and the next thing to fix. Rewriting those comments to substitute a
  new name would assert the very call the comment denies, so they were left
  alone.
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

**The work list is the `annotated=no` rows**, 475 of them, of which **99 are
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

**0x1C00 is the limit worth carrying, not an absence.** Twenty comments name
it, 19 in a data frame and 1 unsettled — but it has **no row in this table at
all**, because no transfer reaches it, so it was never in the ranking to be
wrong in. That is the shape to watch for in any other count
here: not ranked is not absent, and 67 candidate pairs name a callee the table
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
