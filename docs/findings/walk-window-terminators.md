# `walk()`'s stop reason is a column now, and the 45 rows its budget truncates are named

(2026-09-25, issue #846. Static reading of committed bytes through the
tool's own `walk_why()` and `classify()`. No capture opened, no EC, no
hardware, no Windows, no `registers.yaml` row touched.)

[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) §Row 9 measured
that `trace_xdata_refs.walk()`'s loop is bounded by `max_insns` and not by
`len(d)`, and then drove that loop from every one of the image's 262144 start
offsets to count where it stops: `max_insns (8) exhausted` fires **119530**
times. That figure is a property of the file, and nothing in the tree had asked
what it means for the committed tables whose `window` column the same function
produces. This is that question, answered: **45 of 1288 rows across nine
tables** are truncated, so their windows are shorter than the code around them
and their `access` cells are summaries of a cut. All 45 are listed in
`ec/annotations/walk-budget-census.csv`, and each of the six affected tables
now carries a `terminator` column saying which of the five guards ended it.

**The terminator is now in the tool rather than in a re-implementation of it.**
`walk_why(d, start, max_insns)` holds the loop and returns
`(instructions, why)`; `walk()` is that function's first element, with its
name, docstring and signature unchanged, so all nine of its call sites and the
eleven modules that import around it are byte-identical in behaviour. The
vocabulary is five tokens and is *not* new — each one is a name
`opcode-len-bounds-census.md`'s own reproducing snippet already prints for the
same event, and that snippet had to re-implement `walk()`'s loop to count
them. Lifting the names into the tool is what makes the column and the 119530
one measurement in two places rather than two vocabularies for one event.

## What was measured

Through `walk_why()`, over every row of every committed `window` column this
function produces, at `walk()`'s own budget of 8:

| table | rows | `flow opcode` | `DPTR reloaded` | `max_insns (8) exhausted` |
|---|---:|---:|---:|---:|
| `ec-07c4-07d5-sites.csv` | 117 | 89 | 12 | **16** |
| `ec-07d6-07d7-sites.csv` | 213 | 174 | 26 | **13** |
| `ec-0x07d1-sites.csv` | 76 | 61 | 5 | **10** |
| `ec-0x07d0-sites.csv` | 254 | 231 | 19 | **4** |
| `manual-fan-ctrl-0751-sites.csv` | 29 | 28 | — | **1** |
| `xdata-0400-045f-sites.csv` | 409 | 344 | 64 | **1** |
| **subtotal** | **1098** | 927 | 126 | **45** |
| `xdata-086x-dispatch-sites.csv` | 114 | 39 | 75 | **0** |
| `xdata-1c3x-consumers-sites.csv` | 67 | 17 | 50 | **0** |
| `ec-09e9-09eb-sites.csv` | 9 | 2 | 7 | **0** |
| **total** | **1288** | | | **45** |

Two of those figures are an independent check rather than a new claim. The
`0x086x` row is 75 DPTR / 39 flow / **0 exhausted** over its 114 rows, which is
#805's own committed tally for the very table its census drove — the same
measurement from a different function, agreeing exactly. And no committed site
reaches `end of buffer` or `instruction does not fit`: the first needs a start
within one byte of the image's end and the second within two of it, and
`sites_for()` only ever hands `walk()` a `MOV DPTR` site.

**`manual-fan-ctrl-0751-arms.csv` is not in the table above** and its 171
`window` cells are not counted here. It has a `window` column, but
`walk_branch_arms.py` produces it, its key is `site_runtime` rather than a file
offset, and its cells are arm listings that end on a flow opcode by
construction. Folding it in would count another tool's guarantee as this one's
measurement.

## The issue's four, and the thirteen

The issue said "**Four** of the 45 change their committed `access` cell" at a
64-instruction budget. All four are among the thirteen, with exactly the
committed and budget-64 values the issue quotes — so it is a correct subset,
and acting on "four" would have left nine cells silently wrong. **It is
thirteen**, and the split is mechanical: a direct store to DPL (`0x82`) or DPH
(`0x83`) — `mov 0x82,a` / `mov 0x82,rn` — sitting between the budget-8 cut and
the `movx` whose direction changed the cell.

| table | `file_offset` | `addr` | committed `access` | at budget 64 | |
|---|---|---|---|---|---|
| `ec-0x07d0-sites.csv` | `0x2C2FA` | `0x07D0` | `write x1` | `read x1, write x1` | A |
| `ec-0x07d0-sites.csv` | `0x2E8D4` | `0x07D0` | `write x1` | `read x1, write x1` | B |
| `ec-0x07d1-sites.csv` | `0x28B8B` | `0x07D1` | `read x1` | `read x2` | A |
| `xdata-0400-045f-sites.csv` | `0x0DD4A` | `0x045A` | `read x2, write x1` | `read x2, write x2` | B |
| `ec-07c4-07d5-sites.csv` | `0x2B9D2` | `0x07D4` | `read x1` | `read x2` | A |
| `ec-07c4-07d5-sites.csv` | `0x2949C` | `0x07D5` | `read x1` | `read x2` | A |
| `ec-07d6-07d7-sites.csv` | `0x2A0E6` | `0x07D6` | `read x1, write x1` | `read x2, write x1` | A |
| `ec-07d6-07d7-sites.csv` | `0x2BECB` | `0x07D6` | `write x2, walks 3 …` | `write x4, walks 4 …` | B |
| `ec-07d6-07d7-sites.csv` | `0x2C6EB` | `0x07D6` | `read x1` | `read x2` | A |
| `ec-07d6-07d7-sites.csv` | `0x2A0FB` | `0x07D7` | `write x1` | `read x1, write x1` | A |
| `ec-07d6-07d7-sites.csv` | `0x2ABFF` | `0x07D7` | `read x1` | `read x2` | A |
| `ec-0x07d1-sites.csv` | `0x2B344` | `0x07D1` | `read x1` | `read x2, walks 2 …` | A |
| `ec-0x07d1-sites.csv` | `0x2B370` | `0x07D1` | `read x1` | `read x2` | A |

**Ten are A and three are B**, and the two are different findings rather than
degrees of the same one.

### A: the larger-budget cell would be a miscount, for ten of the thirteen

`walk()`'s guard tests `d[i] == MOV_DPTR` and cannot see the `0xF5 0x82` /
`0x8F 0x82` form, so past a DPTR store it walks on and files the *indexed*
access under the site register. `ec-0x07d0-sites.csv` `0x2C2FA` is the clearest
case, and it is the one the repository already holds the refutation of:

```
0x2C2FA  mov  dptr,#0x07d0      <- the site: 0x07D0
0x2C2FD  mov  a,r7
0x2C2FE  movx @dptr,a           <- budget-8 window ends here on `clr a`
0x2C2FF  mov  0xf0,#0x5e
0x2C302  mul  ab
0x2C303  add  a,#0xf8
0x2C305  mov  0x82,a            <- DPL. walk()'s guard cannot see this.
0x2C307  clr  a                <- 8th instruction: the budget runs out
        --- the budget-8 window ends; a 64-instruction budget continues ---
0x2C308  addc a,#0x08
0x2C30A  mov  0x83,a            <- DPH. DPTR is now 0x0800 + low(A), not 0x07D0
0x2C30C  movx a,@dptr          <- the read a 64-instruction budget would count
0x2C30D  jnz  +0x08
```

`../annotations/pd-index-geometry.md` records that the `0xC2FA` site indexes
`0x08F8 + R7×0x5E`, and `pd_index_geometry.py --self-test` asserts that decode
off this very row's `window` cell. So the repository already holds the
contrary reading for this row: the extra `movx a,@dptr` at `0x2C30C` is a read
of an address built from R7, not a second access to `0x07D0`, and a
`read x1, write x1` cell would say it is. **This is the finding that decides
what this work does not do.** Re-cutting at a larger budget is not a tidier
version of the same table; for 10 of the 13 it would put a wrong `access` cell
into a committed file.

### B: the budget-8 window was short, for three of the thirteen

`xdata-0400-045f-sites.csv` `0x0DD4A` is the possibility the issue raises — "a
site may have two accesses and the budget-8 summary happens to read the same":
`read x2, write x1` → `read x2, write x2` is a **second real write to
`0x045A`**, and the bytes say so with no DPTR store anywhere in between.

```
0x0DD4A  mov  dptr,#0x045a
0x0DD4D  movx a,@dptr
0x0DD4E  anl  a,#0xf0
0x0DD50  movx @dptr,a           <- the one write the budget-8 cell counts
0x0DD51  movx a,@dptr
0x0DD52  mov  r7,a
0x0DD53  mov  a,0x32
0x0DD55  anl  a,#0x0f
        --- the budget-8 window ends ---
0x0DD57  mov  r6,a
0x0DD58  mov  a,r7
0x0DD59  orl  a,r6              <- a computed value, written back
0x0DD5A  movx @dptr,a           <- the second real write to 0x045A
0x0DD5B  ret
```

The third is `ec-07d6-07d7-sites.csv` `0x2BECB`, where the budget-8 window ends
between two `inc dptr` halves of a `movx @dptr,a` / `inc dptr` chain and
`write x2, walks 3` → `write x4, walks 4` is four writes with no reload
anywhere. So the issue's "say so if that is what it turns out to be" turns out
to be right for two of its four, and the committed cells are **short rather
than wrong** in those two.

## What the tool records, and what it refuses

`ec/tools/walk_budget_census.py` is the census, and it re-derives every row's
terminator through the same `walk_why()` the `terminator` column is rendered
from. `--budget N` answers "which rows does *this* budget truncate";
`--check` holds `ec/annotations/walk-budget-census.csv`.

Three refusals, all of them the `load_census_map()` shape — a default in any of
these places is a cell that reads as agreement:

- **`--check` at a budget the committed CSV does not record** is refused, and
  says which budgets the file does record. A `--check` that went green against
  rows it never looked at is worse than no check.
- **A terminator outside the vocabulary** stops the run. A `walk_why()` that
  grew a sixth way to stop would otherwise put a token in the census and into
  `--check` that nothing can classify.
- **The class A/B verdict refuses to guess.** A `--extend` too small to reach
  the first extended `movx` yields `undecided`, not class B: "the window was
  too short to see a store" and "there is no store here" are different
  findings, and a row that keeps its cell either way is recorded `unchanged`
  and named no class at all. **Nothing in the committed census is
  `undecided`** — at the committed `--extend 64` every row is `A`, `B` or
  `unchanged` — and the case is reachable rather than hypothetical:
  `--extend 9` reports exactly two rows `undecided`, `ec-07d6-07d7-sites.csv`
  `0x2BECB` and `ec-0x07d0-sites.csv` `0x2E8D4`, both still budget-truncated at
  nine instructions. The other 43 are `unchanged` there, because their
  `access` cell is already the same at nine, so the short window never has to
  be diagnosed. `ec/tools/test_walk_budget_census.py` exercises the
  `undecided` verdict on a hand-built fixture rather than depending on a
  budget at which it happens to fire.

The tool also re-derives each row's committed `access` cell from the image and
**refuses the whole run** if it cannot reproduce one, at `walk()`'s own budget
and only there. Without that check the census could be measuring a different
walk than the tables were cut with and every verdict in it would be about the
wrong population. At any other budget the committed cell is simply not what a
run should reproduce, so no comparison is made.

## The re-cut: one column, and one cell that was already stale

Six tables gained the `terminator` column, regenerated with
`--terminator-column` by the command now on each of their six pages. The
`terminator` column is **opt-in**, exactly like `--census-column`, so the
default output of `csv_table()` is unchanged and
`xdata-086x-dispatch-sites.csv` — #800's table, whose `--check` is the
regression test — still reproduces byte for byte. The census's first
reproducing command is that check.

**No `access` cell changed in any of the six. Exactly one `window` cell did**,
and it has nothing to do with this work:

| table | `file_offset` | was | now |
|---|---|---|---|
| `xdata-0400-045f-sites.csv` | `0x11F16` | `movx a,@dptr ; db 0xa2` | `movx a,@dptr ; mov c,acc.0` |

`disasm8051.py` renders opcode `0xA2` as `mov c,acc.0` today, and this table
was not regenerated when that rule landed, so its cell was stale before the
re-cut and the re-cut is what brought it up to date. **It reproduces on clean
`origin/main`**: `git stash`, run the page's command, `cmp` against the
committed file, and `cmp` reports a difference at byte 35100, line 385. No
prose quotes the old cell — the string `db 0xa2` appears in the repository at
that CSV row and nowhere else. It is recorded here rather than quietly fixed
because a re-cut that moves a cell is exactly the thing a reader has to be
able to see, and "this work changed a decode" would have been the wrong
conclusion. `test_walk_budget_census.py` pins it as the *only* cell that moved,
by diffing every re-cut table against `e198fd9` — the commit immediately before
this one. The ref is pinned rather than `HEAD` because `HEAD` is *this* work on
the merge commit, where each table is its own baseline and the diff finds
nothing; step 9 below carries the same ref for the same reason.

## Prose that inherited a cell: a measurement, not an assumption

The issue asks for the `.md` companions to be re-read for prose inheriting one
of the moving cells. Checked rather than assumed, by grepping the four issue
addresses and the three class-B additions across every `.md` under
`ec/annotations/` and `docs/` **as they stood before this change** — the two
files this work adds (`docs/findings.md` §57 and this one) quote the addresses
themselves, so a grep run after the merge hits them and that is this write-up
talking to itself, not a page inheriting a cell:

- `0x2E8D4`, `0x28B8B`, `0x0DD4A`, `0x2BECB`: **quoted in no pre-existing
  page.** So
  `ec-0x07d0-sites.md`, `ec-0x07d1-sites.md`, `manual-fan-ctrl-0751.md` and
  `xdata-0400-045f.md` inherit none of them, and the issue's third bullet is a
  no-op.
- `0x2C2FA` **is** quoted, in `../annotations/pd-index-geometry.md` §7 — not in
  the three pages the issue names. Its two `--self-test` pins
  (`pd_index_geometry.py:1349-1352`) assert substrings of that row's `window`
  and `file_offset` cells, and both still pass, because no `window` cell
  moved. That is also why `0x2C2FA` is the class A case spelled out above: the
  page that quotes it is the page that refutes the budget-64 reading of it.

And one tally that could have broken and did not: `ec-07d6-07d7-sites.md` §2
reconciles the exact `access` strings across all 213 rows
(85/1/3/10/2/2/36/3 = 142 and 44/1/1/11/3/—/9/2 = 71), and it still reconciles
after the re-cut, cell for cell.

## What this does not establish

- **Nothing about what the EC does.** Every input is a committed file: a site
  table and `ec/firmware/GMxMGxx_11.800`. A `classify()` cell is a reading aid
  over at most 8 instructions of a linear window that cannot follow a branch,
  and `trace_xdata_refs.py`'s module docstring says what else that decode
  cannot do. A window that ends at the budget is a property of Python walking
  a `bytes` object, not a statement about the firmware's intent.
- **Nothing about a register's status.** `ec/annotations/registers.yaml` is
  untouched and no `status:` value changes. This is about how a tool renders a
  window, and a re-cut table with an `access` column in it looks enough like a
  register finding to say so plainly here.
- **What the budget should be.** It stays 8. The work records the budget, its
  per-table consequence, and the fact that raising it corrupts 10 of the 13
  cells that would move; it does not argue for a value, and `--extend`'s
  default of 64 is issue #846's own figure kept as a re-derivable named
  default, not a recommendation.
- **Which address the extra `movx` in a class A row actually touches.** The
  census can say that DPL or DPH was overwritten before it — that is a byte
  fact — and it cannot say what the new DPTR is, because the value comes from
  registers the window does not show. `pd-index-geometry.md` §7 is where that
  is worked out for `0x2C2FA`, by hand, with its own arithmetic.
- **#799, which this does not touch and must not be cited as closing.** #799
  is one register (`0x0D31C`) undercounted because
  `mask_dp_byte_7c_reset_dptr_0860` reassigns DPTR **inside a callee**. That
  is a different shape in a different place: the reassignment is not in this
  walk's linear window at all, so no budget reaches it and the class A verdict
  cannot see it. A DPL/DPH store *inside* the window is what class A is; one
  inside a called routine is what #799 is, and this work's evidence says
  nothing about it either way.
- **#800**, which is the `census` column of the one table this measures as
  clean. That table is deliberately not re-cut, and its `--check` staying
  green is what makes the re-cut's own claim checkable.
- **Any hardware or Windows step.** None is needed and none is implied. No
  capture was opened, no register read back, no EC or HID node touched. The
  toolchain needed here is `python3` and the committed firmware — no Ghidra,
  no `analyzeHeadless`, no `ilspycmd`, no radare2.

**One prepared follow-up, not done here.** Wiring the census's `--check` into
the cheap gate would want a new `docs/ci/agent-gates-*.patch`, which
`tools/test_agent_gates_patches.py` holds against the committed gate script
without editing `.github/`. Doing it in this change would put a new file into a
set a shared suite enumerates, and a gate change is a human's call, so it is
named here for the follow-up rather than absorbed.

## Reproducing it

All of it, from the repository root. The six `diff`s first — they are what the
re-cut rests on — then the census, then the checks that consume the tables.

```sh
# 1-6. each page's command, re-cut through --terminator-column and diffed
#      against the committed file. Six `diff -` invocations, all exit 0.
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x07C4 0x07D3 0x07D4 0x07D5 --csv --terminator-column \
  | diff - ec/annotations/ec-07c4-07d5-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x07D6 0x07D7 --csv --terminator-column \
  | diff - ec/annotations/ec-07d6-07d7-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 --csv --terminator-column \
  | diff - ec/annotations/ec-0x07d0-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D1 --csv --terminator-column \
  | diff - ec/annotations/ec-0x07d1-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --csv --terminator-column \
  | diff - ec/annotations/manual-fan-ctrl-0751-sites.csv
(cd ec/tools && python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 \
  $(python3 -c "print(' '.join(f'0x{0x400+i:04X}' for i in range(0x60)))") \
  --csv --terminator-column) \
  | diff - ec/annotations/xdata-0400-045f-sites.csv

# 7. the regression test: no `access` or `window` cell moved in the default
#    output, and the census's 45
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
  0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check

# 8. the census: the per-table tally above, and the 45 against the committed CSV
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --check

# 8b. the two refusals, and the verdict the committed data never reaches
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --budget 16 --check
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --extend 9 --csv

# 9. the one `window` cell that moved, and that it predates this work: the
#    pre-change table says `db 0xa2`, and the pre-change tool has the loop
#    walk() now hands to walk_why() at its own :224-243. e198fd9 is the commit
#    before this one; HEAD is this work once merged, so `git show HEAD:` would
#    print the new cell and this step would show nothing at all.
git show e198fd9:ec/annotations/xdata-0400-045f-sites.csv | sed -n '385p'
git show e198fd9:ec/tools/trace_xdata_refs.py | sed -n '224,243p'

# 10. consumers of the re-cut tables: two of pd_index_geometry.py's pins are
#     `window` cells in ec-0x07d0-sites.csv, and the 0x086x table is read by
#     the site census by vocabulary
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/check_site_census.py

# 11. the suites: this work's own, the one that reads a re-cut table, and
#     the runner's total
python3 -m unittest discover -s ec/tools -p test_walk_budget_census.py
python3 -m unittest discover -s windows/tools -p test_gpu_block_watch.py
bash tools/run-tests.sh
```

Two of these are worth naming as the ones that would catch a mistake. Step 7 is
the fifteen-address `0x086x` sweep from
[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md)'s command 1: it
diffs a 114-site sweep against a table this work did **not** re-cut, and it is
what makes "no `access` or `window` cell moved" a measurement rather than an
assertion. Step 10's `--self-test` is what would catch a `window` cell moving
in `ec-0x07d0-sites.csv`, the one table a tool asserts substrings of.

**A note on the line numbers in that census.** `walk()`'s loop moved into
`walk_why()`, so `:229`, `:230`, `:241-242`, `:330` and `:436` in
`opcode-len-bounds-census.md` and `docs/findings.md` §53 are **pre-change**
numbers, and the note appended to that file records where each moved to rather
than rewriting the record in place.
