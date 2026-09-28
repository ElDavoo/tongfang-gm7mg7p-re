# `test_site()` bounds the index at `:217` and reads three bytes underneath it, and the second bound is now there

(2026-09-28, issue #1019, which is [`descend-index-guard.md`](descend-index-guard.md)
follow-up 3 filed as an issue of its own. Static reading and arithmetic over
committed bytes, plus brute force over constructed fixtures. No capture opened,
no EC, no hardware, no Windows.)

`descend()` answers "does the instruction fit" with its own test, and
`test_site()` — the same file, the same scan shape, a few lines above it — did
not. This records the bound that closes the gap, and two corrections to the
issue that changed what the fix has to *say* rather than what it has to do.

**The headline is a latent exception, not a wrong answer fixed.** The bound
fires **0** times over the committed `0x0751` run and **0** times over all
**10414** `0x90` sites in the image, and both committed CSVs come out
byte-identical before and after. No committed row is wrong today, and this page
does not say one was.

## The two sites, and the two questions

`test_site()` walks a short window forward from a `mov dptr` site looking for
the branch on a mode bit. Its loop is four lines:

```python
    for _ in range(SCAN_INSNS):
        if off < 0 or off >= len(d):      # :217, pre-change — the *index*
            return None
        op = d[off]                       # :219
        n = OPCODE_LEN[op]                # :220
```

`:217` answers *is the index readable*. It is satisfied by `off == len(d) - 1`
whatever `n` is, and the six reads underneath it need more than that:
`d[off + 2]` for a `mov dptr`, `d[off + n - 1]` for the branch's last byte,
`d[off + 1]` for a bit test and for a mask, and two `d[off:off + n]` slices.
`:217` holds the first byte and says nothing about the rest — which is the
census's row-9 distinction, and `descend()` already holds both tests for the
same reason.

`descend()`'s own pair, added by #844, is the model this follows. Its second
test is at `:353` and its comment at `:348-352` says why the two stay; the same
ordering and the same reasoning now sit at `:237` and `:230-236`. `descend()`'s
docstring lists its bounds in one sentence — a transfer depth, an instruction
budget and the end of the buffer — and `test_site()`'s listed one. It now names
two.

**Why #847's verdict does not transfer.**
[`rel8-displacement-bound.md`](rel8-displacement-bound.md) settled the same
shape in `audit_call_targets.py` with *a self-test check of the bound, not a
`len(d)` guard*, and the issue cites that as precedent. It does not carry, and
the reason is where the bound lives. There, the ceiling is `hi` — a **region**
bound, a constant out of `region_bounds()` in another module, and `main()`'s
PD-marker check three frames from the read is what holds the buffer under it. So
a `len(d)` test in the loop would test something other than what actually holds
the read: what is true is `hi <= len(d)`, and that is a property of the *call
sites*, not of the loop. Here the bound *is* this loop's own `len(d)`, one line
up and already tested: that is the census's row-9/row-10 distinction turned the
other way, and it is why the two sites in one file settle differently without
either being the wrong answer.

## Two corrections to the issue, left visible

The issue names four read sites that can reach past `:217`. Both corrections
below were re-derived on this tree and neither changes the fix — the same
comparison closes all of them — but the write-up cannot claim four independent
raising reads, so the old claim stays written here beside the correction.

**1. `:233` can never be the read that raises.** All three `BIT_TESTS` have
`OPCODE_LEN` 3, and `:229` reads `d[off + n - 1]` = `d[off + 2]` — one byte
further out — *two statements earlier*, in the same `if op in CONDITIONAL:`
block. A `0x30` truncated by one byte raises out of `:229`, not `:233`, and so
does the `0x70` accumulator form whose `n` is 2. `:233` is strictly dominated.
It still needs the guard — the guard is what makes the dominance irrelevant —
but it is not a fourth vector.

Counted rather than argued, over every buffer a four-byte `mov dptr ; movx`
prefix followed by up to three arbitrary bytes (**16 843 009** buffers,
exhaustive in the three bytes):

| line | read | `IndexError`s |
|---|---|---|
| `:229` | `relative_target(op, d[off + n - 1], pc)` | 370 979 |
| `:258` | `prev = (op, d[off + 1])` | 112 911 |
| `:240` (was `:222`) | `dptr = (d[off + 1] << 8) \| d[off + 2]` | 73 477 |
| `:251` (was `:233`) | `bit = d[off + 1]` | **0** |

Three sites raise, and `:251` is not one of them.

**2. The slices at `:252`/`:254` cannot truncate on any path that reaches
them.** They are in the same `if op in CONDITIONAL:` block as `:229`, and
reaching them means passing `:229`, which reads `d[off + n - 1]` — the slice's
own last byte. That read in range *is* `off + n <= len(d)`, so `d[off:off + n]`
is always exactly `n` bytes. Measured: of the **6144** dicts that sweep
returned, **0** had a `raw` shorter than its own opcode's length. So the
issue's "the quieter of the two failure modes" is not true of the code as
merged, and a write-up that reported a fixed truncation would be overclaiming.

The fits test still closes the shape, and the reason to want it is a future
edit rather than today's bytes: `:229` and the slices are two statements apart
with nothing binding them, and reordering that block — or moving a read into
it — is exactly what would expose a quiet short `raw`. That is a real hazard
and it is the one this guard removes. It is not a bug that was fixed.

## The two vectors

Both reproduced read-only against the tool as merged, with `:217` in place and
nothing else changed, on the same `common` fixtures the suite's own `walk()`
helper builds.

```console
$ python3 -c "
import importlib.util, sys, traceback
sys.path.insert(0, 'ec/tools')
s = importlib.util.spec_from_file_location('wba', 'ec/tools/walk_branch_arms.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
for label, d, off in (('A', b'\x00'*10 + bytes([0x90, 0x07]), 10),
                      ('B', bytes([0x90, 0x07, 0x51, 0xE0, 0x54]), 0)):
    try:
        m.test_site(d, 'common', off, off, 0x0751, True)
    except IndexError:
        print(label, traceback.format_exc().strip().splitlines()[-2].strip())"
A   File "walk_branch_arms.py", line 222, in test_site
B   File "walk_branch_arms.py", line 258, in test_site
```

*(against the pre-change tool, whose `:222` and `:258` are `:240` and `:276`
here.)* Both are **constructed**: `descend-index-guard.md` records that the
committed `0x0751` run reaches neither site, and the count below is the
measurement that says the same for this one.

## The bound, and how often it fires

```python
        # A different question, and it stays: this asks whether the
        # *instruction* fits, which `off + n == len(d)` satisfies, so a
        # one-byte opcode at the very last byte decodes and the scan is
        # allowed to land exactly on len(d). The test above is what holds the
        # index; deleting this one would not make the operand reads beneath it
        # safe -- `d[off + n - 1]` and `d[off + 2]` are the bytes this bounds,
        # and neither of them is the one the index test covers.
        if off + n > len(d):
            return None
```

`>` and not `>=`, and that is the whole reason for the second half of each pin:
a `jnb` whose last byte is the buffer's last byte is a whole instruction and
has to decode. An over-bounding guard would refuse real sites, which is the
quiet way to be wrong in the other direction.

**Fires 0 times**, measured rather than argued, over both sets that matter:

- the committed `0x0751` run — **29** sites, **17** of them branched, lowest
  site offset `0x8942`, so **227 006** bytes of margin to the end of the
  `0x40000`-byte image;
- **all 10414** `0x90` sites in the image, walked in each of the four regions
  the tool knows — 0 fires, and 0 `IndexError`s, before and after.

That is what makes the headline sentence a measurement: **a latent exception,
not a wrong answer fixed.**

## What `None` now also means, and what it costs

`None` is the function's only failure value, and the new guard makes it mean
one more thing: not only "no mode-bit branch follows the site", but also "the
scan reached an instruction the buffer does not hold whole". The docstring says
so rather than leaving it to be discovered.

**This widens an existing conflation rather than creating one.** `:217` already
returned the same `None` for a buffer the scan ran off the end of, so there
were already two meanings. The direction is the safe one: `main()` prints *"no
conditional branch on a mode bit follows the site in the decoded window"*, and
a window that ended early is not one it may claim to have read. What is lost is
the ability to tell the two apart, and **that costs something real**:
`main()` returns `0 if branched else 1`, so on a buffer short enough to
truncate every site the run would exit 1 having branched on nothing — the same
exit status as a target that genuinely has no mode-bit branch, and for a
different reason.

**The stronger option was declined, and it is the one a reader should take up
if a dump ever makes it matter**: a distinct truncation verdict — a sentinel
return, a reason field on the result, or a new column in the arms CSV — so a
caller can tell "no branch" from "window truncated". That is the more
calibrated design and it was not taken here because it changes a shared tool's
interface and a committed CSV's columns, and it fires 0 times on the committed
image, so it would be a redesign bought for nothing observable. Recorded so the
next reader can pick it up rather than re-derive the argument.

## The pin

Two cases in `BoundTests` — *"Every bound has to stop the walk and say so"* —
in the existing `test_walk_branch_arms.py`, called through `wba.test_site()`
directly because `walk()` pins the region to `common` *and* descends, and these
are about the scan. Same reason `descend-index-guard.md` records for its one
`pd-image` case. The class docstring carries a clause so a reader is not
puzzled by cases that never call `walk()`.

Each case asserts **both halves**, which is what makes it a pin rather than a
formality: the truncated buffer returns `None`, and the same scan one
instruction later returns a branch dict whose `raw` is the full
`OPCODE_LEN[op]`. The first half fails on the pre-change tool by raising
`IndexError` out of `:222` and `:258`; the second fails if a later change
over-bounds and refuses a well-formed branch.

| case | truncated fixture | raises out of | full form ends on |
|---|---|---|---|
| `test_a_site_scan_stops_at_an_instruction_the_buffer_does_not_hold_whole` | ten `0x00` then `90 07` | `:222` | a `jnb` whose last byte is the buffer's last |
| `test_a_site_scan_does_not_read_a_mask_past_its_own_operand` | `90 07 51 E0 54` | `:258` | the `anl ; jnz` pair's `jnz`, likewise the last byte |

This work **adds no suite**, so `tools/README.md` needs no row and is not
touched; the existing row at its `:77` already reads *"direction
classification, **bounds**, refusals, and negative-result wording"* and stays
true. Adding a new `test_*.py` instead would have needed a row in that table —
the every-merge-must-edit lock `test_readme_suite_table.py` and
[`no-append-logs.md`](no-append-logs.md) exist to stop.

## The old → new line mapping

Every citation this edit moves, in one place, in `descend-index-guard.md`'s
shape. Old lines are `HEAD`; new lines are this tree. `test_site()`'s
docstring grew by 9 and the guard and its comment by 9 more, so everything
below `:211` in that function and everything in `descend()` shifts by 18.

| cited as | is now | what moved |
|---|---|---|
| `:204-211` (`test_site()` docstring) | `:204-220` | +9, the two-bounds paragraph |
| `:217` (pre-read index guard) | `:226` | +9 |
| `:219` (`op = d[off]`) | `:228` | +9 |
| `:220` (`n = OPCODE_LEN[op]`) | `:229` | +9 |
| — (the fits test and its comment) | `:230-238` | new |
| `:222` (`dptr` read) | `:240` | +18 |
| `:229` (`d[off + n - 1]`) | `:247` | +18 |
| `:233` (`bit = d[off + 1]`) | `:251` | +18 |
| `:252`, `:254` (the slices) | `:270`, `:272` | +18 |
| `:258` (`prev`) | `:276` | +18 |
| `:343` (`descend()`'s pre-read guard) | `:361` | +18 |
| `:346` (`descend()`'s read) | `:364` | +18 |
| `:347` (`descend()`'s table index) | `:365` | +18 |
| `:353` (`descend()`'s fits test) | `:371` | +18 |
| `:361-363` (the operand-bytes comment) | `:379-381` | +18 |
| `:404-412` (the `ljmp`/`lcall` block) | `:422-430` | +18 |
| `:220` in the census's grep block | `:229` | the same +9 |
| `:347` in the census's grep block | `:365` | the same +18 |

**Where the mapping lives, stated because the issue points both ways.** The
issue asks for a moved line's mapping "in the same shape as the #846 and #843
notes", which sit beside the census's grep block. **It goes here instead, and
no new note is added beside that block.** A per-change note there is an append
log by construction — the block already carries four stacked — and
`no-append-logs.md`'s whole argument is that a document every merge must edit is
a lock nobody holds. It would also push every line below it, including the
`not a site` table row that
[`test-line-pin-census.md`](test-line-pin-census.md) pins, which is the exact
three-suite breakage `descend-index-guard.md` records paying for.

The consequence is stated plainly: **after this change the census's grep block
is stale** at its `walk_branch_arms.py` lines, and this table carries the
mapping — the same standing the #844/#846/#843 notes already give that file.
Its **per-site table row 2 is deliberately left at `:212-213`**, with row 8 at
`:327-328` and both `three more rows` paragraphs, and the only edit to that file
is row 2's `settled by` cell, which now names both guards beside the function.

**The grep block is not re-run, and this change's own two lines are not in
it.** The command prints **59** lines on `HEAD` where the block says 52, which
is drift in four other files this change does not touch and the same fourth
occurrence the census has now caught three times. Its own rule is that it is
*the grep re-run, not the old output edited by hand*, and this is not a re-run:
re-running it would import that drift and re-anchor ~19 more lines in
`pd_index_geometry.py` alone, crediting this change with work it did not do.

The two cases above add two lines to the command's output — **61** on this tree
— and both are in `test_walk_branch_arms.py`, which is not one of the block's
nine files. The block's own arithmetic is therefore unchanged: those nine still
sum to **41**, `walk_branch_arms.py` still contributes **2**, and **no site of
the shape is added** (the new bound indexes no table). A later re-run will have
to record the 61, the way every note beside that block has recorded its own.


## What this does not establish

- **No live test ran, and none is planned.** No EC was opened, no register read
  back, no capture taken, no hardware and no Windows involved. Every number here
  is a static read of a committed file, a brute force over constructed
  fixtures, or a command over the committed image. The subject is a property of
  Python walking a `bytes` object, so there is nothing for a human with the
  machine to run.
- **The 0-fire count is a measurement, not a proof.** It says the bound is inert
  on the committed image at the committed bounds. It is not "cannot fire", which
  is `docs/findings.md` §4's lesson and the census's row-10 mistake.
- **The two CSVs being byte-identical is the regression evidence.** It was run
  in both directions — before and after — and it is what makes "no behaviour
  changed" a measurement. `manual-fan-ctrl-0751-arms.csv` and `-sites.csv` both
  come out identical, which is also the check that adding the bound changes
  nothing wherever `off + n <= len(d)`.
- **No register status moved, and none could have.** Nothing here is about a
  register; `ec/annotations/registers.yaml` is not touched. No upstream patch is
  prepared either: this is a change to an offline analysis tool, not to a
  driver, and issue #10 keeps any upstream PR a human's manual submission.
- **A `pd-image` reachability vector for `test_site()` was not built.**
  `descend-index-guard.md` has one (the #844 vector-B shape), and this is the
  same file and the same scan. It is left unbuilt deliberately: the 0 fires over
  all 10414 sites is what the guard needed, and constructing a reachability
  vector for it would buy a claim about a path nothing opens. Named here so the
  next reader knows it was not swept rather than forgotten.
- **The `:252`/`:254` truncation is closed as a shape, not reported as a fixed
  bug.** The corrections above are the reason, and they are measurements, not
  arguments.

## Reproducing it

From the repository root.

```sh
# the two new cases, and the whole suite
python3 ec/tools/test_walk_branch_arms.py BoundTests
python3 ec/tools/test_walk_branch_arms.py
bash tools/run-tests.sh ec/tools

# the tool's own oracle, unchanged
python3 ec/tools/walk_branch_arms.py --self-test ec/firmware/GMxMGxx_11.800   # exit 0

# behaviour unchanged: the committed artifacts, byte for byte
python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
    0x0751 --callee-depth 1 --csv | diff - ec/annotations/manual-fan-ctrl-0751-arms.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
    0x0751 --csv --terminator-column | diff - ec/annotations/manual-fan-ctrl-0751-sites.csv

# the two gates this touches
python3 ec/tools/gen_findings_index.py --check
bash .github/scripts/agent-gates.sh
```

**The `diff` pair is the load-bearing command**, and it was run in both
directions: byte-identical before the change and byte-identical after. A reader
who wants the "before" result gets it from `HEAD` without touching this branch.
`--terminator-column` is load-bearing on the second one and is *not* in
`trace_xdata_refs.py`'s own `Usage:` block, so the natural command omits it and
the sites table comes out a column short; `rel8-displacement-bound.md` and
`descend-index-guard.md` both say so.

The `OPCODE_LEN` figures the corrections rest on: `MOV_DPTR` (0x90) is 3, the
three `BIT_TESTS` are 3 each, the four accumulator tests are 2 each, and the
three `MASK_OPS` are 2 each — which is what makes `:229` dominate `:233` rather
than the other way round.

**The suite has five reds, and none of them is this change's.** A whole-tree
`bash tools/run-tests.sh` on this branch: **67 suites, 2048 tests, 5 FAILED**.
Each of the five was run against this tree and against `HEAD` with this work
stashed, and **every failure list is byte-identical** between the two — so none
of them is this change's doing, and none is repaired by it either.

| suite | what it fails on |
|---|---|
| `test_check_cluster_citations.py` | `docs/findings/xdata-cluster-names-guard-off-recipe.md`, a file this change does not touch; `docs/findings.md` §59 records the suite as still red on `main` |
| `test_check_pin_table_rows.py` | `docs/agent-pipeline.md`, likewise untouched here |
| `test_check_doc_figure_pins.py` | a shape case that reads the tree, the way `test_two_figures_in_one_cell_are_both_read` above it does |
| `test_check_eq_guard_citations.py` | untouched by this change |
| `windows/tools/test_gpu_block_watch.py` | `ec/annotations/registers.yaml` and a door table; a different component, untouched here |

Named here rather than fixed, the same call
[`descend-index-guard.md`](descend-index-guard.md) and
[`rel8-displacement-bound.md`](rel8-displacement-bound.md) made — though those
recorded one red each, and the count has since gone up on its own. That is the
point of naming all five rather than the one the plan expected: a red recorded
only on the page that found it is a red nobody is tracking, and the count
belongs to a whole-tree run rather than to whatever a single change happened
to run. `test_walk_branch_arms.py` — the suite this change is about — passes
at **40** tests, and `bash tools/run-tests.sh ec/tools` reports the four reds
above it.

## Follow-ups this opens

1. **`None` conflating "no branch" with "window truncated" is now three-way.**
   The distinct-verdict option is declined above with its reason; this is the
   standing note that it exists and what it would cost. It becomes worth doing
   when a dump arrives that is short enough to trigger it, not before.
2. **The `pd-image` reachability vector for `test_site()`**, the #844 vector-B
   shape applied to the scan rather than to `descend()`. Unbuilt here, for the
   reason above; the guard covers it if such a vector ever reaches it, since it
   is the same function.
3. **`test_site()`'s other callers.** `descend-index-guard.md` follow-up 2 names
   `callee_row()` and the `--callee-depth 1` path as other callers of
   `descend()` that were not examined. This change is one function inside
   `test_site()` and does not widen that question, which is still open.
