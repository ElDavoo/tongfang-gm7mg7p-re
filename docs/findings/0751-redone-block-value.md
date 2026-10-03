# A value under test stops naming a block when the same value is written twice in a day (issue #721)

`ec/tools/grade_0751_isolation.py` takes `--block` as a *value*, and the value
is what it is for: `--block`'s own help spells it out (`0xA0`, `A0` and `a0`
are the same block), §6 stamps every dump with the `<value>` of the block it
belongs to and attaches the grader's output one block at a time, and every
per-block line in the report is named by the value its `write` mark carried.
Nothing in the mark stream distinguishes one block from another except that
value — `assign_blocks` opens a block at a `write` mark and names it by what
that mark says.

§3 also tells the operator what to do when a block comes out void: run it
again. And §3 fixes the three CSVs as **one file for all three blocks**, so
"run it again" reads as append a fourth block to the set the first one is in.
The re-done block carries the same three labels, so it is a second block with
the same value — and the value that was supposed to identify a block now
identifies two. `next((b for b in blocks if b.value == wanted), None)` takes
the first, which is the attempt that came out void.

The committed fixture `ec/tools/testdata/0751-isolation-run-redone-block/` is
`0751-isolation-run-3blocks/` with that re-done block appended, and the tool
over it printed:

```
  block 1 of 4: value under test 0xA0, roles control, write, restore
  block 2 of 4: value under test 0x00, roles control, write -- NOT GRADED, 3 problem(s): void
  block 3 of 4: value under test 0x10, roles control, write, restore
  block 4 of 4: value under test 0x00, roles control, write, restore
```

Two lines reading the same value, neither saying so, and `--block 0x00`
selecting `block 2 of 4` — the void one — and printing its two windows under a
header claiming to be the `0x00` block. Block 4 was not reachable by value at
all.

## The void is not what makes it a defect

The issue demonstrates the condition with a void first attempt. The defect
does not need it, and the case the issue did not demonstrate is the one that
would otherwise have shipped green. Put block 2's missing restore mark back —
one row per capture, the mark the first attempt is short — and every block on
the day is intact:

```
=== 4 block(s), one per no-op control arm (§3) ===
  block 1/4: intact -- last mark 'restored 0x0751=0x10' is the restore
  block 2/4: intact -- last mark 'restored 0x0751=0xA0' is the restore
  block 3/4: intact -- last mark 'restored 0x0751=0x00' is the restore
  block 4/4: intact -- last mark 'restored 0x0751=0xA0' is the restore
```

and the run exited **0**, with those two identical `value under test 0x00` lines
in the census. Nothing about that day is short: every mark is in all three
captures, every capture spells it the same way, every block ends on its
restore, every window is graded. So the condition is on the **value**, and
keying it on `block_verdict` would have left a day passing that
`3blocks/` holds at 1.

The same condition is reached a second way, and it is worth naming because it
is the check's other half rather than a separate defect. When the three
consoles type a mark more than `MARK_SPLIT_SECONDS` apart, `coalesce_marks`
does not fuse them: each console's `write` opens its own block, all of them
carrying `0xA0`, and every one of them is already `NOT GRADED` for `missing,
void`. That day reached the check before this change existed, and the refusal
below now applies to it too — which is right, and is what
`MarkSplitBoundaryTests`' `--block` half was rewritten to assert rather than
worked around.

## What it prints now

Over the same fixture:

```
  block 1 of 4: value under test 0xA0, roles control, write, restore
  block 2 of 4: value under test 0x00, roles control, write -- NOT GRADED, 3 problem(s): void -- 0x00 is the value under test of 2 block(s) of this run (2, 4), so it names no one of them and --block is refused on it
  block 3 of 4: value under test 0x10, roles control, write, restore
  block 4 of 4: value under test 0x00, roles control, write, restore -- 0x00 is the value under test of 2 block(s) of this run (2, 4), so it names no one of them and --block is refused on it
```

The clause is on **every** block carrying the value, not on the first, so
neither line is the only record that the repeat exists; and it names the
blocks by index, so the line points at them rather than describing the
condition abstractly.

It is a clause and not a paragraph, and deliberately says only the one thing
true of both shapes: that the value names no single block, and that `--block`
is refused on it. **The census it prints on is whole-capture**, so the clause
is on those lines whatever the run was scoped to — including a `--block` run
over one of the day's unambiguous values, which grades that block, exits 0, and
still names the repeat. Only the unscoped run has its exit code held at 1 by
the repeat itself, on the scope `void` and `withheld` already take, so that is
what the prose around the clause says rather than the clause itself. It does
**not** say what put the value in two blocks, because this cannot know.
§3's re-done block wants a second `<date>`; a split day wants the mark
distances the census already printed above. A sentence that named the redo as
the cause would be wrong on the split day, which is what the first draft of
this clause did.

## `--block` refuses rather than selecting

```
$ python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-redone-block/*.csv --block 0x00

--block '0x00' names 2 blocks in these captures, block 2 of 4 and block 4 of 4.
The value under test is what identifies a block, so a value this many blocks
carry names none of them one: this is not graded as the first of them, because
a first match over several is a verdict on whichever came first rather than on
any. Read the census above for what each of them is short of; where this is
§3's re-done block, the remedy is that block on its own <date> and its own set
of the three CSVs (§3). --block names one block of a value that is in one block.
```

The census prints first and the refusal points at lines the operator has just
read, which is the same order the no-match refusal beside it is in. Nothing is
selected: `selected` is left `None` for a repeated value so the census marks no
block `-- not selected in this run`, because marking one of them would name the
block the refusal is declining to choose.

### Why refuse, and not add a selector

The issue offers this choice too — a `--nth`, an index, a start timestamp — and
declines it, for three reasons that are about this repository rather than about
taste:

- **`--block`'s own help is the claim that the value identifies a block.**
  `0xA0`, `A0` and `a0` are the same block; there is no second axis in the tool
  to hang a disambiguator on. A selector for "the other one" legitimises
  appending a re-done block into a shared set, which is precisely what the
  runbook change here removes.
- **The tool already has a settled direction for "this input does not say which
  block a row is about": name it and refuse.** A repeated capture is refused
  outright, a repeated `--dump-pair` is named and skipped, a `--block` naming no
  block is refused, a mark the parse cannot read refuses the whole run. A value
  naming two blocks is the same class of fact.
- **Both attempts were already distinguishable in the output.** The census and
  `report_blocks` both carry `block {i} of {total}`; what was missing was a line
  saying the value had stopped identifying a block, and a `--block` that acted
  on the fact. That is a smaller diff than a selector, and it is the one that
  leaves the tool's own vocabulary alone.

The cost of the choice is real and is not hidden: an operator who genuinely
wants the second `0x00` block has no way to grade it from a day that holds both.
The answer is the one §3a already uses for the same collision — its
service-stopped pass takes its own `<date>` rather than being a fourth block of
§3's — and §3 now says so for the re-done block.

## `VOID_BLOCK_NOTE` no longer sends the operator back where it started

The note ended *"Redo the void block per §3"*, and with §3's three CSVs being
one file per run, that read as an instruction to append into the set the run is
refusing. It now reads:

> Run the block again per §3, on its own `<date>` and its own set of the three
> CSVs rather than appended to this one: a second block of a value already in
> this set stops the value naming a block, which the census above names and the
> exit code reflects.

The sentence is pinned twice over — by the two existing cases that had pinned
the old one, each of which now also asserts the old sentence is **absent**, and
by a case that holds the runbook's §3 and the note to the same remedy — so a
tool that still told the operator to redo into the file it refuses fails rather
than passes.

## The dump half needed no tool change

§6 names the dump files by `<value>` alone and §3's steps 0 and 6 redirect
with `>`, so a re-done block's dumps would overwrite the first attempt's. That
dissolves under the same decision as the CSV half: a re-done block on its own
`<date>` writes its own set of the files §6 lists and can overwrite nothing,
and §6 now says so where it explains that `<value>` is all a dump has.

Adding an attempt discriminator to `DUMP_VALUE` would be a way to keep filing
re-done blocks under one name — the state being removed — and a dump is a
whole-range read with no marks in it, so its file name is the only thing that
says which block it belongs to. `verdict_marker` already handles two blocks
sharing a value, and the suite asserts that path over this fixture rather than
over a clean day.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`'s `RepeatedValueTests`, over the new
fixture:

- the census names the repeat on both lines, with both indices;
- a repeat holds the exit code with no void block anywhere in the day (the
  tempfile variant of the fixture with block 2's restore put back);
- `--block` on the repeated value exits 1, names both blocks, and prints
  neither block's windows — asserted as **absences**, which is the load-bearing
  half, since a reworded refusal that still printed block 2's windows would
  satisfy a positive assertion about the refusal text alone;
- `--block` on either unambiguous value still grades and still exits 0, so §6's
  per-block attachment survives the change for a day with no re-done block in
  it;
- the re-done block's own integrity verdict and its three graded windows stand;
- a `--dump-pair` filed under the repeated value still reads, and
  `verdict_marker` still names both blocks;
- §3's runbook text and `VOID_BLOCK_NOTE` say the same remedy.

The two existing cases that pinned `'Redo the void block per §3'` are rewritten
in this change, and each asserts its absence as well as the new sentence.

`RepeatedValueTests` is a new class in the existing suite file rather than a
new `test_*.py`: it tests the same tool through the same `run()` helper and the
same runbook readers as `GradeTests` and `MarkSetTests`, and a suite split
across files would want its own copy of all of that.

## Open: should a dump be filed by block index rather than by value?

Not answered here, and deliberately not half-answered. A `--dump-pair` filed
under a block *index* would give two `0x00` blocks each their own bracket, and
the grader could then report per-attempt §4.1-§4.3 movement rather than one
figure spanning both attempts — which is a real question, because the two
blocks' write windows are different lengths and §4.4's comparison is over one
window. What is missing before it can be asked properly is the same thing
missing from the CSV half: a decision about what a re-done block **is**. This
change's answer is that it is a second run with its own `<date>`, and on that
answer the question does not arise for a well-formed day. It would arise the
moment an operator appends one anyway, and the refusal above is what that
moment produces instead.

## The issue's line numbers have drifted

Corrected here rather than carried into the prose, in the shape
`docs/findings/0751-append-unchecked-marks.md` uses:

| issue says | it is at |
|---|---|
| `grade_0751_isolation.py` `VOID_BLOCK_NOTE` | `VOID_BLOCK_NOTE` |
| `grade_0751_isolation.py`'s `--block` selection | the `selected = next(...)` line in `main`; the repeat is `repeated_values`, beside `assign_blocks` |
| `manual-fan-ctrl-0751-isolation.md`'s redo sentence | §3, "The run, one variable at a time" |
| `ec_watch-marks.md`'s ways list | the same heading there as `docs/findings/0751-append-unchecked-marks.md`'s, which this change makes "Five ways…" in both |

Cited by function and heading throughout, per `CLAUDE.md`.

## **None of this is a live test.**

Every output above is fixture arithmetic over committed CSVs: rows written by
hand into `ec/tools/testdata/0751-isolation-run-redone-block/`, read by the
tool, with no EC involved. Nothing was read back from a register, no capture
was taken, no block was run at a laptop, and no sentence here is evidence about
`0x0751` or about the EC. The run this would matter to is issue #663's, and
that one is a human's.