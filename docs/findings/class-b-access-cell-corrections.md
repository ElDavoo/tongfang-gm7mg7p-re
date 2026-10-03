# The three class-B `access` cells were short rather than wrong, and all three are corrected (issue #865)

(2026-10-02. Static reading of committed bytes through `walk()` and
`classify()` over `ec/firmware/GMxMGxx_11.800`, cross-checked against the
committed `.asm` listings and the committed decompiles. No capture opened, no
EC, no hardware, no Windows, and no `status:` moved.)

[`walk-window-terminators.md`](walk-window-terminators.md) §B called three
committed `access` cells "**short rather than wrong**" and stopped there. That
is a claim about three cells in three annotation files, each of which lands
somewhere the tree has already committed an aggregate, so this picks the three
up: what the bytes say, whether the correction is accepted, and what has to
move with it.

**All three were short, and all three are corrected.** With the corrections in
place, `walk_budget_census.py --extend 64` reports that **no** committed
`access` cell in any table the census measures changes at a 64-instruction
budget — which is a stronger statement than "three would", and it is the
outcome worth having: the census's remaining question is not which cells to
distrust but which terminator ended them.

```console
$ python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800
...
15 of 1288 rows across 9 tables are truncated at a budget of 8.
A budget of 64 changes none of their `access` cells; all 15 keep the cell they have.
```

## 1. The three corrections, and what makes each one right

Each is decided on the bytes between the budget-8 cut and the first `movx` a
64-instruction budget reaches, with **no store to DPL or DPH in front of that
`movx`**. That absence is what separates this from
[`walk-window-terminators.md`](walk-window-terminators.md) §A's rows, where
the extra access rides a rebuilt pointer and no budget makes the cell right;
there it is class A, and §A's argument is untouched by anything here.

Each correction then gets a second method that does not go through
`walk()` at all — the committed listing, and the hand-decoded annotation on
the export. The census's class B verdict is the tie-breaker, exactly as the
issue asked; the second method is what says *why* it is right rather than
merely *which way*.

### 1.1 `0x07D6` at file offset `0x2BECB` — `write x2, walks 3 …` → `write x4, walks 4 …`

`ec/decompiled/pd/BECB.asm`, the export
`write_07d6_07d7_07d8_07d9_then_store_07df`:

```
BECB     90 07 d6 mov      DPTR, #0x7d6
BECE     ed       mov      A, R5
BECF     f0       movx     @DPTR, A        ; 0x07D6 = R5
BED0     a3       inc      DPTR
BED1     eb       mov      A, R3
BED2     f0       movx     @DPTR, A        ; 0x07D7 = R3
BED3     e4       clr      A
BED4     a3       inc      DPTR            <- walk()'s 8th instruction; the cut
BED5     f0       movx     @DPTR, A        ; 0x07D8 = 0
BED6     a3       inc      DPTR
BED7     f0       movx     @DPTR, A        ; 0x07D9 = 0
BED8     ef       mov      A, R7
BED9     12 ac d3 lcall    0xacd3          <- the window ends here
```

Four stores, three `inc dptr`, no `mov 0x82,a` / `mov 0x83,a` and no
`mov DPTR,#imm` anywhere in between. `walk()`'s eighth instruction from the
site is the `inc dptr` at `0xBED4`, which is precisely why the committed cell
counted two writes and three walked bytes rather than four of each — the cut
falls one instruction before the third store.

The second method agreed before the correction did:
`../../ec/annotations/ec-07d6-07d7-sites.md` §3.1 had always printed all four
stores, and the export's name has always been the four. **The CSV cell was
the odd one out.**

### 1.2 `0x07D0` at file offset `0x2E8D4` — `write x1` → `read x1, write x1`

`ec/decompiled/pd/E8D4.asm`, the export
`index_07d0_by_0x17_then_fill_128d_and_call_f604`:

```
E8D4     90 07 d0 mov      DPTR, #0x7d0
E8D7     ef       mov      A, R7
E8D8     f0       movx     @DPTR, A        ; 0x07D0 = R7
E8D9     7e 00    mov      R6, #0x0
E8DB     7f 17    mov      R7, #0x17
E8DD     c0 06    push     0x06
E8DF     c0 07    push     0x07
E8E1     7d 00    mov      R5, #0x0        <- walk()'s 8th instruction; the cut
E8E3     e0       movx     A, @DPTR        ; read the same byte back
E8E4     75 f0 17 mov      B, #0x17
E8E7     a4       mul      AB              ; index by the record stride 0x17
...
E8F6     12 12 8d lcall    0x128d          <- the window ends here
E8F9     90 07 d0 mov      DPTR, #0x7d0    <- past the call: its own CSV row
```

The read-back is real work, not a mask-and-store: its result is multiplied
against the record stride `0x17` and handed to `0x128D`, which is the
indexing this function exists to do.

**The issue's premise about this file was wrong, and the correction is worth
recording because it removed the last stated reason to check separately.**
Issue #865 said `ec/decompiled/pd/E8D4.c` is unannotated and therefore had no
second method. It is a named, hand-decoded export with an annotation row, and
that row's comment already says the function "reads the byte back from
`0x07D0`". The `type:` field reads `unresolved`, which is a verdict about
`0x128D` and `0xF604` — what those two are asked to do is not decoded — not
about the annotation or about this read.

The second `mov DPTR,#0x07d0` at `0xE8F9` sits **past** the `lcall 0x128d`,
so it is outside the window and is already a row of its own in
`ec-0x07d0-sites.csv` at `read x1`. Counting it here as well would have
double-counted one read.

### 1.3 `0x045A` at file offset `0x0DD4A` — `read x2, write x1` → `read x2, write x2`

`ec/decompiled/bank0/DD4A.asm`, the export
`or_intmem_32_low_nibble_into_045a`:

```
DD4A     90 04 5a mov      DPTR, #0x45a
DD4D     e0       movx     A, @DPTR
DD4E     54 f0    anl      A, #0xf0
DD50     f0       movx     @DPTR, A        ; write 1: clear the low nibble
DD51     e0       movx     A, @DPTR        ; read it back into R7
DD52     ff       mov      R7, A
DD53     e5 32    mov      A, 0x32         ; internal-RAM 0x32
DD55     54 0f    anl      A, #0xf
                        <- walk()'s 8th instruction; the cut
DD57     fe       mov      R6, A
DD58     ef       mov      A, R7
DD59     4e       orl      A, R6
DD5A     f0       movx     @DPTR, A        ; write 2: (old & 0xF0) | (0x32 & 0x0F)
DD5B     22       ret                     <- the window ends here
```

Two reads and two writes, and the net is a single statement about the byte:
`0x045A = (old & 0xF0) | (internal 0x32 & 0x0F)`. The export's annotation
spelled out both writes and the net before this correction existed.

## 2. Two premises of the issue that are recorded rather than acted on

**"`ec/decompiled/pd/E8D4.c` is unannotated"** is addressed in §1.2 above: the
file is a named export with a hand-decoded annotation row, and its comment
already says what the correction says. The row the issue treated as the one
lacking corroboration had the same corroboration as the other two.

**"the low nibble has an owner that is not in the image at all" is an
overclaim, and CLAUDE.md's calibration rule forbids it.** Internal RAM `0x32`
is referenced across committed decompiles under `ec/decompiled/` —
`grep -l DAT_INTMEM_32 ec/decompiled/*/*.c` names them — and
`ec/decompiled/common/2F85.c` dispatches on its value. What is true and
bounded is narrower: `0x32` has **no entry in
`../../ec/annotations/registers.yaml`**, and its role is not established — that
is, nothing here says what sets it or what reads it besides this one routine.
"Found by this method" is not "absent", and this repository has retracted
enough confident-sounding absences to be worth repeating that.

## 3. What moves, and what does not

Two of the three move no class bucket at all, which is why the aggregate work
is smaller than the issue anticipated.

| site | was | now | bucket moves? |
|---|---|---|---|
| `ec-07d6-07d7-sites.csv` `0x2BECB` | `write x2, walks 3 consecutive bytes (inc dptr)` | `write x4, walks 4 consecutive bytes (inc dptr)` | no — both are "a write that walks" |
| `ec-0x07d0-sites.csv` `0x2E8D4` | `write x1` | `read x1, write x1` | **yes** — write → read-modify-write |
| `xdata-0400-045f-sites.csv` `0x0DD4A` | `read x2, write x1` | `read x2, write x2` | no — both are "both directions" |

The three aggregates that carry them:

- **`ec-07d6-07d7-sites.md` §2** gains a `write x4, walks 4 consecutive bytes
  (inc dptr)` row at 1 and drops `write x2, walks 3 …` from 2 to 1. The `142`
  total, the `85` plain reads, the `10` plain writes and the 3
  read-modify-writes do not move, and neither does the paragraph below the
  table: the corrected row walked before and walks now, so the count of rows
  that walk is unchanged. Only the string attached to one row changed.
- **`ec-0x07d0-sites.md` §3** moves `write` 8 → 7 and read-modify-write 2 → 3,
  which moves the net sentence to **229 read, 14 write, 3 read-modify-write, 8
  unresolved**. 229 does not move: it is 157 site-level reads plus the 72
  handoffs §3 resolves as reads, and neither figure is touched by a
  correction to one site's own cell. `229 + 14 + 3 + 8` is still the 254 the
  table partitions. The same sentence is quoted in `registers.yaml`'s `DBD1`
  note as "229 read, 15 write, 2 increment in place" and moves with it.
- **`registers.yaml`'s `XDATA_045A` note** is unchanged in its figures.
  `19 reads, 1 write and 2 read-modify-writes` still holds, because the
  corrected cell was already a both-direction cell and lands in the same
  bucket — `register_ref_table.py`'s `bucket()` reads a string containing both
  `read` and `write` and answers `read+write` for `read x2, write x1` and for
  `read x2, write x2` alike, which is that table's independent agreement with
  the correction. What the note gains is the two-cycle write and the
  `0x32` low-nibble source, phrased as a gap in this repository rather than
  an absence in the firmware.

**No `status:` moves.** `XDATA_045A` stays `present-untested`; `DBD1` stays
`unknown-not-absent-DO-NOT-WRITE-BLIND`. A direction class is not a status,
and a static decode is not a behavioural test.

### 3.1 `pd-0x07d0-07cc-clusters.csv` also commits an `access` cell

`pd_site_clusters.py` writes its own `access` column over the same
`0x07D0`/`0x07CC` sites `ec-0x07d0-sites.csv` enumerates, and its row at
`0x2E8D4` read `write x1`. Left alone, the tree would have held two committed
`access` cells for one site, answering the same question two ways — the exact
disagreement this issue exists to end. `corrected()` is called there too and
the file is regenerated by its own command, so one site has one cell:

```console
$ python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 --check
ec/annotations/pd-0x07d0-07cc-clusters.csv: this run reproduces it byte for byte (261 lines)
```

## 4. How a corrected cell is derived rather than typed

**A corrected cell cannot simply be typed into the CSV, and the tree says so
twice.** `trace_xdata_refs.py`'s `--check` diffs the generator's output
against the committed file and answers "regenerate rather than edit";
`walk_budget_census.py`'s `census_table()` refuses the entire run when it
cannot re-derive a committed `access` cell from the image. Both would go red
on a hand-edit, and both would be right to.

`ec/tools/access_cell_corrections.py` is therefore the single place a
committed `access` cell may differ from `classify(walk(d, offset))` at
`walk()`'s own budget of 8. Each entry carries the corrected string, **the
instruction budget at which the tool itself produces that string**, a reason,
and an evidence path. `verify()` re-walks the image at each recorded budget
and raises unless `classify()` hands back exactly the string the entry claims
— a correction that cannot be re-derived from the bytes is a claim, and this
repository does not keep those.

Keyed on the file offset rather than on a `(table, offset)` pair: the offset
*is* the site, since `trace_xdata_refs.sites_for()` only ever hands `walk()`
the address of a `MOV DPTR,#imm16`.

`classify()` and `walk()` are unchanged, so every other row of every
committed table still satisfies `classify(walk(d, off)) == access` byte for
byte, and the `window` and `terminator` cells of the three corrected rows are
untouched: those rows are still genuinely budget-truncated, and that stays
recorded.

## 5. Reproducing all of it

```console
# Each corrected string equals classify(walk(d, offset, budget)) at its
# recorded budget. This is the reproducer for the corrections themselves.
$ python3 ec/tools/access_cell_corrections.py --self-test
$ python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --extend 64 --csv

# The three site tables, each by its own page's command, and the census.
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x07D6 0x07D7 --csv --terminator-column | diff - ec/annotations/ec-07d6-07d7-sites.csv
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x07D0 --csv --terminator-column | diff - ec/annotations/ec-0x07d0-sites.csv
$ cd ec/tools && python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 \
      $(python3 -c "print(' '.join(f'0x{0x400+i:04X}' for i in range(0x60)))") \
      --csv --terminator-column | diff - ../../ec/annotations/xdata-0400-045f-sites.csv
$ python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --check

# Independent consumers, run because they re-derive direction from the image
# and would disagree silently if a correction were wrong. Both of the first
# two read `0x0DD4A` as `read+write` before the correction and after it, which
# is what §3 says about buckets not moving.
$ python3 ec/tools/check_site_resolution.py ec/firmware/GMxMGxx_11.800 | grep 045A
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --markdown | grep 045A
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/gen_findings_index.py --check
$ bash tools/run-tests.sh
```

## 6. What this does not establish

- **Nothing about what the EC, the PD firmware or Windows does with any of
  these bytes.** Every claim here is a direction class over a linear decode
  on both sides, from committed files.
- **Nothing about `walk()`'s budget.** `walk()`'s own `max_insns` stays 8, and
  nothing here argues for a different value. 64 is
  `walk_budget_census.py`'s named `--extend` default and the figure issue
  #846's table used; it is a measurement point, not a recommendation.
- **The tool half of the budget question is untouched.**
  [`walk-window-terminators.md`](walk-window-terminators.md) §A's class-A
  rows and `0x2C2FA` are left exactly as they are: their cells would be wrong
  at *any* budget, because DPTR is rebuilt mid-window and the extra `movx` is
  not this register's. Whether `walk_why()` grows the DPL/DPH guard that class
  A is about is #846's remaining half.
- **Issue #799 is not touched and is not closed by this.** A DPTR reassignment
  inside a callee is a different shape in a different place, and no row here
  is an instance of it.
- **`0x32`'s role is not established, only located.** §2 says what that is
  worth, and it is not a name for the byte.

## 7. What this opens

- **The census's class-B column is now empty, and its class-A column was
  already empty.** Every budget-truncated row the census measures keeps its
  cell at a 64-instruction budget. That makes the census's remaining value its
  *terminator* column rather than its verdict column — the open question is
  which of the rows it lists should say something other than "budget
  exhausted", and #846's tool half is where that is worked.
- **`0x2E8D4`'s correction reaches a page and a `registers.yaml` note through
  two hops**, which is the shape most cell corrections in this tree will have:
  the site table, the page's tally, the net sentence, and the register note
  that quotes it. If a fourth correction appears, that is four files again,
  and `access_cell_corrections.py` is where the decision to make it goes.
- **Internal RAM `0x32` is now named here with no owner recorded.**
  Committed decompiles reference it — `grep -l DAT_INTMEM_32
  ec/decompiled/*/*.c` — and `registers.yaml` has no entry for it. That is a
  real gap and a good candidate for the next census, not a claim about the
  byte.
