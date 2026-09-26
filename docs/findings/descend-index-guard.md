# `descend()` reads `d[off]` two lines above the test that would catch it, and the invariant that held it was not the one the census named

(2026-09-26, issue #844. Static reading and arithmetic over committed bytes.
No capture opened, no EC, no hardware, no Windows.)

[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) follow-up 2 flags
`walk_branch_arms.py`'s `descend()` as **the one contrast case whose check runs
after the read** — the single row in its table where the post-#679 ordering is
not what #679 established. It offers a genuine either/or: put a comment at the
read naming the invariant, or move the check in front of it. This records which
one landed and why the other was declined.

**The pre-read check `test_site()` already has landed.** A comment naming the
invariant is written too — it is at the guard, not above it — but it is a second
line and not the fix, because **the invariant the census's own reason states is
not true as a general property.** The census says the read is in range because
`off` comes from `offset_for_runtime()`, which is `None`-checked. `None`-checked
is not in-range. That correction is in place, beside the original, in that
file's follow-up 2; the arithmetic behind it is the second section here.

## The two sites, and the two different questions they answer

Both are in one file, eleven lines apart, and that is what makes this worth
settling rather than leaving. The contrast is inside the same function.

**`test_site()`, pre-change `:210-211`** puts the end-of-buffer test *above* the
read, in the shape #679 established:

```python
    for _ in range(SCAN_INSNS):
        if off < 0 or off >= len(d):
            return None
        op = d[off]
        n = OPCODE_LEN[op]
```

**`descend()`, pre-change `:327-329`**, read first, tested second:

```python
        op = d[off]                        # :327
        n = OPCODE_LEN[op]                 # :328
        if off + n > len(d):               # :329
            arm.end(f"0x{pc:04X} runs past the end of the image")
```

The two tests do not overlap, and this is the part that has to be stated before
anything else, because it is why the fix is *additional* rather than a move:

- `off + n == len(d)` is **permitted** by `:329`. A one-byte opcode at the very
  last byte passes, the walk decodes it, and steps to `off == len(d)`.
- The new test at `:343` asks whether the **index** is readable, which
  `off + n == len(d)` does not answer.

So `:329` was never what held `d[off]` in range, and deleting it would not make
that read safe. It stays, with a comment at it saying so — the census's row-9
lesson, which is that *the instruction fits* and *the index is readable* are two
questions, applies here with the same force it applies to
`trace_xdata_refs.py`'s `walk_why()`. **`:329` moved to `:353`; it was not
removed.**

## Where the offset bound actually comes from

The census's supporting argument leans on the largest `hi` in `REGIONS`
(`trace_xdata_refs.py:82-89`) and calls it `<= 0x40000` = the length of
`ec/firmware/GMxMGxx_11.800`. That is true and it is the wrong row, for two
reasons that both have to be walked through to see the guard is needed.

**1. The ceiling is `0x2FFFF`, not `0x40000`.** The largest `hi` is the second
`erased` row, `("erased", 0x30000, 0x40000, None, ...)`. Its `base` is `None`,
and `offset_for_runtime()`'s `next()` at `trace_xdata_refs.py:247` filters on
`base is not None`, so **that row can never be selected.** The highest offset the
function can actually return is the `pd-image` row's last runtime address,
`0x20000 + 0xFFFF` = **`0x2FFFF`**. Measured:

```console
$ python3 -c "
import importlib.util, sys
from pathlib import Path
sys.path.insert(0, 'ec/tools')
s = importlib.util.spec_from_file_location('wba', 'ec/tools/walk_branch_arms.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
print(hex(max(o for o in (m.offset_for_runtime(r, 'pd-image')
                          for r in range(0x10000)) if o is not None)))"
0x2ffff
```

**2. The floor the tool actually certifies is `0x2004A`, 65461 bytes lower.**
`offset_for_runtime()`'s own bound is `trace_xdata_refs.py:256`, and it bounds
the **runtime address** against the region. It says nothing about the **file
offset** it returns against *this buffer*. The buffer is the caller's, and
`main()`'s contract does not certify its length: `PD_MARKER` is
`(0x20040, b"ITE8850-PD")` and the check is a **slice** comparison
(`walk_branch_arms.py:737`), which cannot raise on a short buffer. What it
certifies is therefore a length floor of `0x20040 + 10` = **`0x2004A`** =
131146 bytes — against a `0x2FFFF` ceiling. The margin is **65461 bytes** of
range the region table says is reachable and nothing says the buffer covers.

That is the whole of it, and it is why the honest description is *the read is in
range because the buffer is long enough*, not *because the region table bounds
it*. The first is a statement about the bytes; the second is not true of the
code.

## The two vectors, measured

Both were run read-only over committed files. Neither is a live test and neither
is a claim about the firmware.

**Vector A — a ten-byte `common`-region fixture of `0x00`,** which is exactly the
shape `test_walk_branch_arms.py`'s own `walk()` helper builds. It raises
`IndexError: index out of range` at `op = d[off]`, and the arithmetic shows why
`:329` never sees it: `0x00` is a one-byte opcode, so the walk decodes
`off = 0…9` and steps to `off = 10 == len(d)`. On the last byte `off + n > len(d)`
is `9 + 1 > 10`, which is **false**. Same vector shape as the census's derived
`b"\x00\x00\x00\x00"` and the same off-by-one the census records for row 9.

```console
$ python3 ec/tools/test_walk_branch_arms.py BoundTests 2>&1 | tail -3
  test_an_index_past_the_end_of_the_buffer_is_reported_as_a_cut ... ERROR
IndexError: index out of range
FAILED (failures=1)
```

*(against the pre-change tool; the case passes on the tree this commit leaves
behind.)*

**Vector B — the `pd-image` region, on a buffer the tool's own entry point
accepts.** `GMxMGxx_11.800[:0x2004A]` still satisfies `main()`'s marker test
(`True`), and a `pd-image` arm at runtime `0x004A` or above raises. `0x0049` does
not: it is inside the buffer, and its one-byte instruction runs to the end, so
the *existing* `:329` test catches that one. The boundary is the whole story in
two numbers.

`pd-image` is genuinely reachable, not a region nothing points at: `sites_for()`
scans the whole buffer, there are **3176** `0x90` bytes in the `0x20000-0x30000`
window, and `arms_for()` hands their region straight to `descend()`. It is not
reached by the committed `0x0751` run — all 29 of its sites are `bank0`/`bank1`
(28 and 1) — which is exactly why `--self-test` exits 0 and why this was never
noticed. **The new stop reason fires 0 times over that run**, and the fire count
is recorded here so a later reader can revisit it.

Vector A alone is enough to decide the question. Vector B is what makes "the
region table does not bound the buffer" a measurement rather than an argument.

## The change

Four edits to `walk_branch_arms.py`, and nothing else in the tool:

- **`END_IMAGE` at `:130`**, a stop reason beside `END_RET` … `END_LOOP`, and
  **added to `CUTS` at `:141`**. Deliberately, and the reason is in a comment
  there: a cut can only *widen* `no_claim()`'s wording and `arm_status()`'s,
  never narrow one. That is the same reasoning the existing `END_LOOP` entry's
  comment gives — "saying `cut` there would understate what was read" — and the
  fire count above is what makes the widening zero-observable on this image.
- **The guard at `:343`**, in `test_site()`'s exact shape (`off < 0 or
  off >= len(d)`), above the read, ending the arm with a verdict rather than a
  silent `None` — `descend()` reports every other stop reason, and
  `arm.end(...)` is what puts it in the CSV's `ends` column.
- **The comment at `:334-342`** naming what holds the index, in the style of the
  neighbouring operand-bytes comment at `:361-363`.
- **`:329` → `:353`, kept**, with a comment at `:348-352` saying the two tests
  answer different questions.

The two `ends` messages stay distinguishable in the one CSV column they share,
which is the point of both being there: the existing one says an *instruction*
runs past the end, the new one says the *index* is past it.

## The pin

Two cases in `BoundTests` — "Every bound has to stop the walk and say so," which
is the right class — in `test_walk_branch_arms.py`, the one place a later reader
looks, and which already drives `descend()` through `walk()`. **Both raise
`IndexError` on the pre-change tool**, which is what makes them pins rather than
formality; that was checked by running them against `HEAD`'s
`walk_branch_arms.py`.

The second names `region="pd-image"` on a buffer cut to the marker floor, so the
risky region is the one covered and the case is not read as an artefact of a
short `common` fixture. It calls `descend()` directly, because `walk()` pins the
region to `"common"`; the module docstring's clause saying the fixtures "are
walked in the `common` region" is amended to name the exception, so a reader
does not have to find the contradiction.

`walk()` is unchanged, and so is `test_site()` — that ordering is already what the
census calls correct and is the model the new guard copies.

## The old → new line mapping

Every citation this edit moves, in one place, per the census's own rule for
itself ("the symbol is named in every row as well as the line, so a later edit
to a comment moves the number without making the row unreadable"). Old lines are
`HEAD`; new lines are this tree.

| cited as | is now | what moved |
|---|---|---|
| `:210-211` (`test_site()` guard) | `:217` | +7 from `END_IMAGE` and its `CUTS` entry above |
| `:212` (`test_site()` read) | `:219` | lifted |
| `:213` (`test_site()` table index) | `:220` | lifted |
| `:321-322` (`None`-check) | `:328-329` | +7 |
| `:324` (`budget <= 0`) | `:331` | +7 |
| `:327` (`op = d[off]`) | `:346` | +19: +7 above, +12 for the guard and its comment |
| `:328` (`n = OPCODE_LEN[op]`) | `:347` | +19 |
| `:329` (`if off + n > len(d)`) | `:353` | +24: +19, +5 for the fits-test comment |
| `:337-339` (the operand-bytes comment) | `:361-363` | +24 |
| `:380-388` (the `ljmp`/`lcall` block) | `:404-412` | +24 |
| `:213` in the census's grep block | `:220` | the same +7 |
| `:328` in the census's grep block | `:347` | the same +19 |

The census's **per-site table rows 2 and 8 are deliberately left at `:212-213`
and `:327-328`**, and the `three more rows` paragraph with them. Row 8 is the
most conflict-prone cell in that file, both rows name their function beside the
number, and follow-up 2's correction clause carries the update. The mapping for
a reader who follows one of those citations is in that file's note beside the
grep block, in the same shape as its #846 note: a moved file, not a wrong one.

**A fourth shared file had to be edited, and the plan did not list it: the two
notes added beside that grep block are 25 lines long, so they moved everything
below them in `opcode-len-bounds-census.md`, and one of those lines was pinned.**
`test-line-pin-census.md`'s table row citing `opcode-len-bounds-census.md:122`
now points at `:147`, which is where that row of the census's `not a site` table
went. **Three suites went red on it** — `test_check_pin_table_rows.py`
(`1 unplaced-row`, and `105 != 106` placed), and `test_census_test_line_pins.py`
and `test_check_pin_table_by_cited_file.py` behind it on `107 != 106` — and the
fix was the repointed line, not the gate. The census's `:71` pin, on the fenced
grep block above the notes, did not move.

**This write-up is itself subject to that census, and that is worth a reader
knowing.** The first draft of this paragraph named the test file and the line
the census row names, in backticks — which is exactly the shape
`check_pin_table_rows.py` reads as a pin — and the result was a
`row-without-record` against a file that did not exist a moment earlier. It is
reworded to describe the citation rather than make one. **The lesson generalises
past this paragraph**: any new write-up under `docs/findings/` that cites a
`file.py:NN` in backticks adds a row to `test-line-pin-census.md`'s table or
trips the checker, and the cheapest way to find out is to run the suites before
writing the summary, not after.

**And the defect itself is this issue's own subject matter, found in a
different file**: a citation that reads correctly and points one row too high is
precisely what #844 is about in `descend()`, and here a committed pin table said
so rather than a reader noticing.

**One correction to the plan, recorded because the plan's own arithmetic for
this was off in a way a reader would hit.** The plan expected *"the one line
that moved"* in the grep block. **Two moved** (`:213` and `:328`), and the
re-run also picked up **four that were already stale before this issue touched
anything** — `trace_xdata_refs.py:229` is `:297` (the #846 move, which that
block never received) and the four `disasm8051.py` lines are each one higher.
The count is unchanged at 39. All six are in the re-run, because that block's
own rule is that it is the grep re-run and not the old output edited by hand,
and a two-line hand-edit would have left it neither.

## What this does not establish

- **No live test ran.** No EC was opened, no register read back, no capture
  taken, no hardware and no Windows involved. Every number here is a static read
  of a committed file or the output of a command over one. Nothing here is a
  claim about what the firmware does with any of this.
- **The read is in range on this image, and that is a measurement, not a
  proof.** `--self-test` over `ec/firmware/GMxMGxx_11.800` exits 0 and the new
  stop reason fires **0** times over the committed `0x0751` run. That is what
  this range produced; it is not "cannot raise", which is the census's row-10
  lesson and the mistake `docs/findings.md` §4 is a page about.
- **`pd-image` reachability is counted, not demonstrated end to end.** 3176
  `0x90` bytes in the window is a byte count, and `sites_for()` scans the whole
  buffer — but no committed CSV walks a `pd-image` arm, so the vector is
  constructed rather than harvested. It is a real region with a real
  `offset_for_runtime()` row, which is all the guard's justification needs.
- **Nothing else in the tool changed, and the two committed CSVs are the
  evidence.** `manual-fan-ctrl-0751-arms.csv` and `-sites.csv` come out
  **byte-identical**, before and after. That is a real regression test rather
  than a formality — the guard is inert wherever `off < len(d)`, which is
  everywhere on the committed image — and it is also the check that adding
  `END_IMAGE` to `CUTS` changes nothing observable.
- **No register status moved, and none could have.** Nothing here is about a
  register. `ec/annotations/registers.yaml` is not touched. `tools/README.md` is
  not touched either: this adds no suite, and
  `test_readme_suite_table.py`'s docstring says it compares the discovered
  **set** and never the counts, so a totals edit would be a conflict bought for
  nothing.
- **The census's row 8 "settled by" cell still says "existing guard; see
  follow-up 2"** and is not edited. It is a shared cell, its function is named
  beside it, and the follow-up now carries the answer.
- **`END_IMAGE` is classified as a cut; the neighbouring
  "runs past the end of the image" is not.** That one also means the walk gave
  up, and it fires as a bare `0x…` message that `CUTS`' `startswith` does not
  match. It was already true and it is out of scope here; see the follow-ups.

## Reproducing it

From the repository root. **Both flags are load-bearing, and one of them is not
in the tool's own usage list** — `trace_xdata_refs.py`'s `Usage:` block lists
`--census-column` and `--check` but never `--terminator-column`, so the natural
command omits it and the sites table comes out a column short. A diff against
the committed file then fails for a reason that has nothing to do with this
change. `--callee-depth 1` **is** in `walk_branch_arms.py`'s usage list, on the
`--csv` example.

```sh
# the two new cases, and the whole suite
python3 ec/tools/test_walk_branch_arms.py
bash tools/run-tests.sh ec/tools

# the tool's own oracle, unchanged
python3 ec/tools/walk_branch_arms.py --self-test ec/firmware/GMxMGxx_11.800

# behaviour unchanged: the committed artifacts, byte for byte
python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
    0x0751 --callee-depth 1 --csv \
  | diff - ec/annotations/manual-fan-ctrl-0751-arms.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
    0x0751 --csv --terminator-column \
  | diff - ec/annotations/manual-fan-ctrl-0751-sites.csv

# the census's own membership test, re-run rather than hand-edited
grep -rn 'OPCODE_LEN\[' --include=*.py ec/tools | wc -l        # 39, unchanged
```

**The `diff` pair is the load-bearing command**, and it was run in both
directions: byte-identical before the change and byte-identical after. A reader
who wants the "before" result can get it from `HEAD` without touching this
branch.

**The suite has one red, and it is not this change's.**
`ec/tools/test_check_cluster_citations.py` fails on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220`, a file this change
does not touch, and `docs/findings.md` §59 records the suite as still red on
`main`. Named here rather than fixed, the same call
[`rel8-displacement-bound.md`](rel8-displacement-bound.md) and
[`pd-sites-address-range.md`](pd-sites-address-range.md) made.

## Follow-ups this opens

1. **The "runs past the end of the image" message is not in `CUTS`, and
   probably should be.** It means the walk gave up for the same reason
   `END_IMAGE` does, but it is emitted as `f"0x{pc:04X} runs past the end of the
   image"`, so `CUTS`' `startswith` never matches it and `arm_status()` will
   call such an arm `complete`. That is a wrong claim in the safe-looking
   direction — it understates a cut — and it is a one-line change to the
   message plus a `CUTS` entry. It is not made here because it is a
   classification decision about an existing message rather than the
   ordering question #844 asked, and because on the committed image it fires
   only in vector B's neighbour (`0x0049`), so changing it now would be
   changing a word nobody has read a CSV row of. **This is a well-posed issue
   and should be filed.**
2. **The other callers of `descend()` have the same shape and were not
   checked.** `callee_row()` and the `--callee-depth 1` path both reach
   `descend()`, and the census's table credits `walk_branch_arms.py` with one
   row for the file. Whether a callee entry point can name an offset past the
   end is the same question this guard answers for an arm, and nothing here
   measures it. The guard covers them — they are the same function — so this is
   a coverage question about the *classification*, not a gap in the guard.
3. **`test_site()`'s own operand reads are the same "does the instruction fit"
   question, and nobody has looked at them.** The guard at `:217` bounds the
   *index*, and four reads sit under it at offsets the index bound does not
   cover: `d[off + 1] << 8 | d[off + 2]` at `:222` (a `mov dptr` is three bytes
   and nothing here has tested that three of them are there), the last-byte read
   `d[off + n - 1]` at `:229`, `d[off + 1]` at `:233` and at `:258`, and the
   `d[off:off + n]` slices at `:252` and `:254` — slices, so they truncate
   rather than raise, which is a quieter failure. The census excludes the
   last-byte-of-instruction read as a different shape with a different bound
   (answered by #847 for `audit_call_targets.py`), so it is out of scope here —
   but `test_site()`'s is another instance of that shape in a file the census
   already has two rows in, and unlike `descend()`'s it is **not** covered by
   the guard this change adds. Worth an issue of its own.
