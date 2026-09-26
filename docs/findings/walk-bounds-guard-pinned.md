# The bounds disjunct is pinned, by two cases — and the sweep that could have noticed it cannot see it

(2026-09-26, issue #845. Static reading, and two mutation runs over a copy of
this tree. No capture opened, no EC, no hardware, no Windows.)

Issue #845 asked for a case that pins the bounds disjunct of `walk_why()`'s
guard, on the grounds that deleting it left the runner printing the same totals
with the same single failure — "the disjunct is pinned by nothing". **That
measurement was taken on a tree this one is not.** On this tree the disjunct
is pinned, by two cases in `ec/tools/test_walk_budget_census.py`, and deleting
it turns that suite red. The other half of the issue's measurement — that the
fifteen-address `--check` sweep still exits 0 with the guard gone — **is still
true, and still exactly why the disjunct reads as dead code.** The correction
lives here, beside the claim it corrects; the wrong claim is the issue's, and
no committed file asserted it.

What lands with it is `ec/tools/test_trace_xdata_refs.py`, holding the
contracts the other suite does not assert.

## The two runs

Each guard was located by its source text, deleted **through its `break`**, and
nothing else in the file was touched. The copy is a `git worktree`-shaped copy
of this tree rather than a bare directory, because
`ec/tools/test_walk_budget_census.py`'s baseline case resolves a pinned commit
with `git show` and a tree with no `.git` goes red for that reason alone.

One correction to the issue's recipe, because a reader hits it first: **the
guard is three lines on this tree, not two.** #846 split the one `or` into two
statements, each with its own `why` and its own `break`, so "delete the guard"
now means three lines rather than the `if` plus the `break` it owns. And the
locator has to ask for a *statement*, not a mention — see *Two things in the
census's file* below, which is about exactly that and cost a run to find out.

| | deleted | `bash tools/run-tests.sh ec/tools` last line | suites red | the fifteen-address `--check` |
|---|---|---|---|---|
| baseline | nothing | `29 suite(s) run, 960 tests; one or more FAILED.` | 1 | exit 0, byte for byte |
| run 1 | the `i + 2 >= len(d)` block | `29 suite(s) run, 960 tests; one or more FAILED.` | 2 | exit 0, byte for byte |
| run 2 | the `d[i] == MOV_DPTR` block | `29 suite(s) run, 960 tests; one or more FAILED.` | 3 | **exit 1**, 75 of 114 rows |

The red set in the baseline run is the standing one — `ec/tools/test_check_cluster_citations.py`, on
`:220` of #822's `docs/findings/xdata-cluster-names-guard-off-recipe.md`, with
the same two `0x0464`/`0x0465` disagreements. It reproduces on a clean
`origin/main`, `docs/findings.md` §52 names it and #830 owns it, and it is
named here rather than fixed here.

**With the bounds block gone**, the red set gains
`ec/tools/test_walk_budget_census.py` and nothing else, with two errors:

```
ec/tools/test_walk_budget_census.py: FAILED
................................EE..................
======================================================================
ERROR: test_the_end_of_the_buffer_names_the_buffer (test_walk_budget_census.TerminatorTokenTests.test_the_end_of_the_buffer_names_the_buffer)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/measure/ec/tools/test_walk_budget_census.py", line 150, in test_the_end_of_the_buffer_names_the_buffer
    self.assertEqual(why(img), T.BUFFER_END)
                     ^^^^^^^^
  File "/tmp/measure/ec/tools/test_walk_budget_census.py", line 116, in why
    return T.walk_why(img, start, max_insns)[1]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/tmp/measure/ec/tools/trace_xdata_refs.py", line 313, in walk_why
    if d[i] == MOV_DPTR:
       ~^^^
IndexError: index out of range

======================================================================
ERROR: test_the_three_byte_opcode_alone_does_not_reach_that_guard (test_walk_budget_census.TerminatorTokenTests.test_the_three_byte_opcode_alone_does_not_reach_that_guard)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/measure/ec/tools/test_walk_budget_census.py", line 172, in test_the_three_byte_opcode_alone_does_not_reach_that_guard
    self.assertEqual(why(fixture(bytes([0x90, 0x07, 0xD0]), size=3)),
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/tmp/measure/ec/tools/test_walk_budget_census.py", line 116, in why
    return T.walk_why(img, start, max_insns)[1]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/tmp/measure/ec/tools/trace_xdata_refs.py", line 313, in walk_why
    if d[i] == MOV_DPTR:
       ~^^^
IndexError: index out of range

----------------------------------------------------------------------
Ran 52 tests in 1.010s

FAILED (errors=2)
```

Two things in that block are the point.

**The traceback lands on `if d[i] == MOV_DPTR:` — the other guard.** With the
bounds block cut, `d[i]` at the sibling test is the read that raises, so the
last frame a reader sees names the line that did *not* do it. This is the same
disjunct the census's row 9 says does all the work, so the frame points at the
one a reader has been told is safe and away from the one they were told to
delete. A case that says what it is for is worth more here than a case that
merely goes red.

**It is an `ERROR`, not a `FAILURE`.** The `IndexError` escapes the case; the
assertion naming the guard never runs. A traceback from inside a neighbouring
suite is a weaker statement of "this guard is load-bearing" than a case whose
comment says so, and it is invisible to anyone who is not already running that
suite.

**With the reload block gone**, the red set gains `ec/tools/test_check_site_census.py` and
`test_walk_budget_census.py` goes from 2 errors to **10 failures** — the
terminator tally, the fifteen-address byte-for-byte reproduction, and
`classify()`'s agreement with every committed `access` cell among them. The
`--check` sweep exits 1 and its diff against `ec/annotations/xdata-086x-dispatch-sites.csv`
rewrites **75 of that table's 114 rows** in 19 hunks, every one of them a
`window` cell that has run past its site into the next one.

## The two guards are not held equally, and the totals line sees neither

The last line of the runner is **byte-identical across all three runs**. A
totals line is a count of tests *run*, which a failing suite does not change
and an error escaping a case does not either; the runner prints it and the
reader is expected to read the verdict off the per-suite lines above. That is
`tools/README.md`'s own standing ("the totals are not a pass and never were"),
and this is the sharpest instance of it in the tree: **two suites going from
green to red, and then a third, move that number by nothing at all.** Anyone
tracking the totals sentence in `tools/README.md` to see whether a tree is
green is tracking the wrong thing, which is what
[`runner-red-suite-set.md`](runner-red-suite-set.md) argues in its own
"Left out on purpose" section.

So the measurement that matters is the **red set**, and the shape of it is the
finding:

| | the bounds disjunct | the reload disjunct |
|---|---|---|
| cases that go red with it gone | 2, both in one suite | 10 in that suite, 1 in `test_check_site_census.py` |
| the fifteen-address `--check` sweep | still exits 0 | exits 1, 75 of 114 rows |
| what a reader is told by the census | it fires **0** times over that sweep | it fires **75** of 114 |

The reload disjunct is held from three directions, one of which is the
committed data itself: a walk that runs past a `mov dptr` produces a different
`window` cell, and the committed tables are full of those cells. The bounds
disjunct has one direction, it is in another suite, and **the sweep the census
points a reader at cannot see it at all** — which is not a defect in the
sweep. Over the committed sweep the smallest `len(d) - i` at the top of a loop
is 94109 bytes, so no committed walk comes within 94109 bytes of needing the
check. The census's `0 / 10` firing counts and its `94109` are right, and they
are the reason the guard looks dead. The difference is that the *token* the
guard produces is on every row the census commits, and the guard is a
different thing from its token.

## What the new suite holds, and what it does not duplicate

`ec/tools/test_trace_xdata_refs.py`, six cases, **reading no firmware
image** — every buffer is built in the case, and `main()` is driven over a
7-byte file in a temporary directory rather than over the dump.
`ec/tools/test_walk_budget_census.py` is the terminator
half — one fixture per guard, each asserting **which guard fired**, because a
wrong token is a census row that names the wrong reason. The new file is the
other half — **which instructions came back** — and the two are not
duplicates: a walk that decodes the wrong window for the right reason passes
the new file and fails the old one, and a walk that names the right reason for
a window it decoded wrongly passes the old one and fails the new one.

What it holds, in the order the issue asked for it:

- **the over-ask yields what fitted**, on #805's derived vector
  `b"\x00\x00\x00\x00"`, asserted by offset and by `raw` bytes rather than by
  mnemonic text — the mnemonic table is `disasm8051.py`'s subject and
  `ec/tools/test_disasm8051.py`'s, and a case here coupled to `0x00`'s wording
  would go red for a change that is not a bounds defect;
- **the same walk says the buffer ended it**, as its own case rather than
  folded in, because it is that assertion which makes the first one a statement
  about the guard: "it stopped" is otherwise equally true of the budget and of
  a flow opcode;
- **`d[i] == MOV_DPTR` still ends a walk, and its absence runs on to
  `budget_end(8)`** — the negative half, on the same eight-instruction fixture
  with three filler bytes where the reload was, so neither line can go;
- **the loop's own bound is `max_insns` and not `len(d)`**, one case and two
  fixtures: the same bytes in a 0x40 buffer run to the budget and in a 7-byte
  buffer run to the buffer's end;
- **both call sites over a hand-built fixture** — `csv_table()`, whose
  `window` cell is asserted against what `walk_why()` returns rather than
  against a spelling and whose `terminator` cell is asserted to be
  `end of buffer`; and `main()` as a subprocess over a fixture file in a
  `tempfile.TemporaryDirectory()`, asserting exit 0, the printed window, the
  `window ended: end of buffer` line, and the stderr note a 7-byte buffer with
  no PD marker produces. That last one is the reason a reader of the output
  does not read `common` as a claim about the real dump.

The first half of the `max_insns` case overlaps
`test_walk_budget_census.py`'s
`test_a_run_longer_than_the_budget_names_the_budget_with_that_budget`, and it
is kept because the second half is the property: it is the half that would go
if `max_insns` were ever replaced by `len(d)`.

## The same two runs again, with the new suite in the tree

The three runs above are the tree **as committed at `99c01938`**, which is the
measurement the issue's claim has to be re-taken against and the one this
page reports. The two that decide whether the new suite is worth anything are
the same two mutations on a tree that carries it:

| | `bash tools/run-tests.sh ec/tools` last line | `ec/tools/test_trace_xdata_refs.py` | the fifteen-address `--check` |
|---|---|---|---|
| baseline | `30 suite(s) run, 966 tests; one or more FAILED.` | 6 tests, passed | exit 0 |
| bounds block gone | `30 suite(s) run, 966 tests; one or more FAILED.` | **FAILED — 4 errors, 1 failure** | exit 0 |
| reload block gone | `30 suite(s) run, 966 tests; one or more FAILED.` | **FAILED — 1 failure** | exit 1 |

The split inside the new suite is the one the cases were written for. With the
bounds block gone, **five of the six go red** and the one that stays green is
`BothGuardsTests.test_a_dptr_reload_ends_the_walk_and_its_absence_runs_on_to_the_budget`
— correctly, because that guard is still there. With the reload block gone,
**only that one goes red**. Neither guard's loss is caught by a case that
names the other, which is what "neither line can go" has to mean.

The totals line is byte-identical across all three rows, for the third time
and on a tree that has the new suite in it. That is the sentence this page
exists to make hard to forget, and
[`../../tools/README.md`](../../tools/README.md)'s twenty-eighth merged-tree
note records it beside the figures it did not move.

What the load-bearing difference is, in one line: `test_walk_budget_census.py`
goes red as **two `ERROR`s** — an `IndexError` escaping a case before its
assertion runs — while the new suite goes red as **one `FAILURE` and four
`ERROR`s whose own assertions name the guard**. Neither is sufficient on its
own. The first is invisible to anyone not already running that suite; the
second says what it is for.

## Two things in the census's file that this tree does not reproduce

Neither is a retraction of its conclusion — its conclusion is right and its
`0`/`10` firing counts and its vector all stand. Both are in how it *shows*
the guard, and both are what a reader following it literally gets on this tree.
They are recorded here rather than edited in place, because
`opcode-len-bounds-census.md` is #805's file and this work did not touch it;
the fixes are one line each and are named as follow-ups below.

**1. Its reproducing snippet's locator now finds a comment.** The snippet
locates the guard with `next(i for i, l in enumerate(lines) if "i + 2 >= len(d)" in l)`,
which takes the *first* match. #846 added a comment near the token constants
that quotes the same text, so the first match is no longer the guard:

```
census locator picks line 109: "# already prints for the same event, and the `i + 2 >= len(d)` disjunct's row"
statement locator picks line 311: '        if i + 2 >= len(d):'
```

Everything the snippet prints from the `cut` module is therefore measured with
the guard **present**, and the recorded block's own first line
(`guard at line 241: '        if i + 2 >= len(d) or d[i] == MOV_DPTR:'`) is a
record of the pre-#846 source rather than of this one. The tally it prints
afterwards is unaffected — `census()` below it re-implements the loop itself
and never reads `cut` — so the two sections of the snippet disagree with each
other: the vector says `IndexError`, the `or` is still there. The fix is to ask
for a statement rather than a mention, which is the second line above.

**2. The per-iteration trace under the derived vector does not match the run.**
The block shows four appends and then the guard firing on the fourth, and the
prose under it reads "the fourth iteration appends, `i` becomes 4, and the test
`i + 2 >= len(d)` is `4 >= 4` — true, and the walk stops with two
instructions", which cannot both be true of one walk. Measured against this
tree's loop:

```
walk(b'\x00\x00\x00\x00', 0) -> [(0, '00'), (1, '00')]
walk_why          -> end of buffer
  iteration 1: i=0 n=1, appended, i becomes 1
  iteration 2: i=1 n=1, appended, i becomes 2
             i=2, i+2=4 >= len(d)=4 -> end of buffer
```

Two appends, and the guard fires at the end of the **second**. The arithmetic
the block quotes is right and so is the count it prints — `2 instruction(s)` —
but they come from iteration 2, not iteration 4, and the four-iteration trace
in between belongs to a walk that never happened. The `IndexError` half of the
block is right for the wrong reason and right anyway: with the guard gone the
walk does reach a fifth iteration and does read `d[4]` out of a 4-byte buffer.

## What this does not say

- **No site "cannot raise."** The guard is load-bearing; that is a different
  statement, and this file repeats
  [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md)'s own bullet
  rather than paraphrasing it. The two runs above are runs on *this* tree with
  *these* fixtures; the committed sweep's `94109` is a property of committed
  inputs and of the range that was run, not a property of the code.
- **The two disjuncts are not equally pinned, and that is not a defence of
  either.** The table above is a count of what a reader finds today, and it
  moves the moment a suite is added. It is stated to correct a claim that is no
  longer true, not as a scale on how careful anyone has been.
- **The sweep bounds the table, not reading.** Per the caveat in
  `ec/annotations/registers.yaml`, a sweep that finds nothing means "not found
  by this method". The `0` is over 114 walks; the `10` is over all 262144 start
  offsets; neither is a claim about any other buffer.
- **No live test ran.** No EC was opened, no register read back, no hardware
  and no Windows involved. Every number here is a static read of a committed
  file, the output of a command over a committed file, or the output of a
  mutation run over a copy of this tree.
- **No behaviour changed.** The two code edits in this work are a new test
  file and a new page. Command 1 below exits 0 on the restored tree, which is
  the evidence for that sentence.

## Reproducing it

**In a git worktree, or a copy of the tree that still has its `.git` in it.**
`ec/tools/test_walk_budget_census.py`'s re-cut case resolves a pinned commit
with `git show`, so a directory without one is red for that reason and poisons
the red set being measured. The three runs, each followed by a restore:

```sh
# 1. the baseline, on the tree as committed
bash tools/run-tests.sh ec/tools

# 2. delete ONLY the `i + 2 >= len(d)` block -- three lines on this tree, the
#    `if`, its `why = BUFFER_END` and its `break` -- located by its source text
#    and NOT by a line number, and NOT by the first line that mentions the
#    phrase (see the locator note above). Then:
bash tools/run-tests.sh ec/tools
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
  0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check
#    -> exit 0, "this run reproduces it byte for byte"

# 3. restore, then delete ONLY the `d[i] == MOV_DPTR` block the same way, and
#    run the same two commands. -> the runner's red set gains two suites and
#    the --check exits 1 with 75 of 114 rows changed.

# 4. restore, and the sweep on the tree as committed
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
  0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check
python3 -m unittest discover -s ec/tools -p test_trace_xdata_refs.py
```

The two tables in *The two runs* and *The same two runs again* are from two
different trees and say so: the first is the tree as committed at `99c01938`,
the second is that tree plus the new suite. Both are the same two mutations,
run the same way, and both are recorded rather than merged because the
difference between them is the point.

A locator that is worth pasting rather than describing, because the phrase
occurs twice on this tree and the wrong one is a comment:

```sh
python3 - <<'EOF'
lines = open("ec/tools/trace_xdata_refs.py").read().splitlines(keepends=True)
g = next(i for i, l in enumerate(lines) if l.strip() == "if i + 2 >= len(d):")
j = g
while lines[j].strip() != "break":
    j += 1
print("cutting lines %d-%d:" % (g + 1, j + 1))
for l in lines[g:j + 1]:
    print("  " + repr(l))
open("ec/tools/trace_xdata_refs.py", "w").write("".join(lines[:g] + lines[j + 1:]))
EOF
```

The runner's totals for `ec/tools` were `29` suites and `960` tests on the tree
as committed at `99c01938` — which is the tree all three runs above were taken
on, and which does not carry the new suite — by
`python3 -m unittest discover -s ec/tools` as well as by the runner. The whole-runner
figures this work moved are recorded in
[`../../tools/README.md`](../../tools/README.md)'s twenty-eighth merged-tree
note.

## Follow-ups this opens

1. **The census's snippet locator, one line.** `next(... if "i + 2 >= len(d)"
   in l)` wants `l.strip() == "if i + 2 >= len(d):"`. Until then the vector
   block's `guard deleted` rows are measured with the guard present, and a
   reader who runs the snippet as written gets a vector section that disagrees
   with itself. #805's file; one line; not done here because this work did not
   edit that file.
2. **The vector block's per-iteration trace.** Four appends and a fourth-iteration
   guard are recorded where two appends and a second-iteration guard is what
   runs. Same file, same reason, and it is prose and a fenced block rather than
   a command, so it is not fixed by fixing the locator.
3. **`walk_branch_arms.py`'s `descend()` is the contrast case whose check runs
   after the read.** Already follow-up 2 in
   [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) and untouched
   here; it is named again only because it is the one other place in that table
   where a reader scanning for "index before bounds" lands.
