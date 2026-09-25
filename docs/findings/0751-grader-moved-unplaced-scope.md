# A run that moved and graded a window in no block printed the movement over the whole capture and nothing that said so (issue #725)

The write-up for [issue
#725](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/725), which is
about `ec/tools/grade_0751_isolation.py`'s `moved_groups` branch scoping its
movement line to nothing at all when some of the run's graded windows are in no
block and none of them were withheld. It is a disclosure change, and the same
kind as [#530's](0751-grader-unplaced-window-scope.md): **no byte is read
differently, no window is graded or withheld differently, and the exit code is
unchanged** on every committed fixture. Nothing here is a register behaviour and
nothing here is evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value, and §7 is where the call is made.

It is the `moved_groups` half of the sentence
[`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md)
(#530) named one line of and left open, on the path #530 did not touch. #530
fixed the no-movement chain and narrowed the withheld arm; this is the fourth
change in the same paragraph, after
[`0751-grader-partial-grade-claims.md`](0751-grader-partial-grade-claims.md)
(#477), [`0751-grader-block-scope-claims.md`](0751-grader-block-scope-claims.md)
(#497) and [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md) (#498,
landed as #502), and the first of them to reach this branch.

---

## The defect, on a committed fixture with nothing edited

`ec/tools/testdata/0751-isolation-run-unplaced-window/` is §6's two-value day
with two `restored 0x0751=0x99` marks in no block, both of which parse and so
are read and graded. The run reports **8 marks, 0 withheld, 8 graded, 2 of them
in no block**, both blocks `intact`, and exit 0. `0751-isolation-run-3blocks-moved/`
is the only committed set where something moved, and it withholds 2 of its 8
windows and has `graded_unplaced == 0`. **The two facts do not meet in any
committed fixture**, so the path they make between them had no test on it.

It is one row away. The address and step are `3blocks-moved/`'s own, and
`0751-isolation-example-active.csv` records the same pair, so the row is not
invented here:

    cp -r ec/tools/testdata/0751-isolation-run-unplaced-window /tmp/moved
    sed -i 's/^\(2026-01-01T12:00:40\.000+01:00,MARK,,wrote 0x0751=0xA0\)$/\1\n2026-01-01T12:00:43.000+01:00,0x0784,0x50,0x28/' \
        /tmp/moved/2026-01-01-0751-isolation-0700-07ff.csv
    python3 ec/tools/grade_0751_isolation.py /tmp/moved/*.csv

The `sed` inserts the row *below* the 12:00:40 write mark rather than appending
it to the end of the file. The tool reads timestamps and not file order, but the
row belongs inside block 1's write window, which opens on that mark and closes
at the 12:01:10 restore — a row appended at the end of the file would land in
the last window of the day instead and grade a different run. The timestamp, not
the position, is what puts it in block 1's window; the position is only what
keeps the file readable.

"Before" is the tool at `061b2213`, this branch's merge base with `main`, and
"after" is the file on this branch; the transcripts name the revision each was
recorded against rather than leaving the reader to assume the one checked out.
The "before" lines are the output of
`git show 061b2213:ec/tools/grade_0751_isolation.py` on the same command:

```
=== what this does and does not settle ===
  2 of the 8 graded window(s) above are in no block: a window is a window of a value under test only by the mark that opened it, so these rows are real and the arm they belong to is unknown, and the static prediction is a claim about the whole capture. The census above names each of these by timestamp and label, in no block and so beyond what `--block` can select.
  At least one of the §4.1-§4.3 bytes moved after a mark: PL1/PL2/PL4 (§4.1).
  That contradicts the static prediction in ec/annotations/manual-fan-ctrl-0751.md §5 if it is the PLs, or §4.2 if it is the fan table -- capture it in full, it is the more interesting outcome.
```

and prints, after it, one line between the movement and the attribution:

```
  That is the 8 window(s) that were graded. The 2 in no block are part of it, and this run cannot say which arm they are a window of. The static prediction is a claim about the whole capture, and this output does not make it over a run in which 2 of its 8 graded window(s) are in no block.
```

**The exit code did not change; what changed is that there is now a sentence to
read.** Before, a reader saw `intact` twice, eight graded windows of which two
carried `block: unplaced`, exit 0, a movement line carrying no denominator, and
underneath it the tool's whole-capture claim. The count line two lines above had
already said 2 of those 8 are attributable to no value under test.

## Which of the two readings was taken, and why

The issue offers (a) extend the movement line's scope the way `elif withheld:`
does, or (b) record why the bare form is correct here. **Reading (a).** (b) is
not defensible, and the tree says so: the sentence directly under the movement
line is a whole-capture claim, and the count line two lines above it has just
said two of the run's eight graded windows are a window of no value under test.
That is the same class of claim over a partly-unattributed set that #530
removed from the no-movement path — on the path #530 did not touch. And the
"Left out on purpose" bullet in #530's write-up already named this case as the
one it was waiting for:

> No committed fixture does: `3blocks-moved/` is the only one that both moves and
> withholds and it has no unattributed graded window, so a change there would be
> untested prose. It is left for a fixture that reaches it rather than written
> blind.

This is the fixture that reaches it, and it is a copy of a committed set with
one committed row added rather than a new directory — see *Why no new
`testdata/` fixture* below.

## The constraint that decided the wording

**`moved_groups` is a union of group *names* over `shown` and carries no window
identity.** The `if withheld:` arm can print "the withheld windows are not part
of it" because a withheld window never reaches `report_window`, so it cannot
have fed `moved_groups` — that is true by construction, before the tool has to
know anything. It is not true here. The two unattributed windows **are**
printed, and their rows **do** feed `moved_groups`.

The same `0x0784` row therefore produces the same movement line whether it
lands in a block's own write window or in the 12:00 stray, and the tool cannot
tell the two apart. Measured, not argued — the same recipe over a second copy,
with `12:00:05` instead, which is inside the 12:00 stray, between the
`restored 0x0751=0x99` at 12:00:02 and the next mark at 12:00:10:

    cp -r ec/tools/testdata/0751-isolation-run-unplaced-window /tmp/stray
    sed -i 's/^\(2026-01-01T12:00:02\.000+01:00,MARK,,restored 0x0751=0x99\)$/\1\n2026-01-01T12:00:05.000+01:00,0x0784,0x50,0x28/' \
        /tmp/stray/2026-01-01-0751-isolation-0700-07ff.csv
    python3 ec/tools/grade_0751_isolation.py /tmp/stray/*.csv

    same marks, same block structure, same `PL1/PL2/PL4 (§4.1)`, same
    `2 of the 8`, same exit 0 -- and the closing sections are byte-identical.
    The two reports differ only above that line, in which window's body the
    row landed in, which is the whole of what `--block` cannot reach in either.

So a sentence of the shape "That is the 6 window(s) … that belong to a value
under test" would be **true of the first placement and false of the second**,
and the tool cannot say which one it is in. That is why the sentence names
`graded` — the true denominator, and the only one available — says the
unattributed windows **are part of** it, and says why the arm they belong to is
not one this run can name. `placed = graded - graded_unplaced` would have been
the natural local here and is not in the code: on this path nothing is excluded
from the movement, so there is no subset to count.

The sentence must therefore print **identically** in both placements, and the
test pins that equality over the closing section rather than a paraphrase of
it. A restatement would pass a sentence that had quietly grown a window
identity.

**"A run it only read part of" is not reused, and the reason is the same one
#530's write-up gives.** That clause is the withheld branch's and is true
there: this run refused a window. Here it read **every window it was shown**, so
the clause would be false — and the decline is taken in the no-movement
`elif graded_unplaced:` arm's own words instead, which are about the narrower
gap:

    The static prediction is a claim about the whole capture, and this output
    does not make it over a run in which 2 of its 8 graded window(s) are in no
    block.

## Why the arm is placed where it is

Last in the chain, after `elif withheld:` and after
`elif selected is not None and len(blocks) > 1:`, and both of those are left
**byte for byte**. The two are the more specific: a withheld window or a
selected block is a reason this run is already smaller than the day, and this
arm adds an attribution gap to a run that *is* the whole capture. A run that
both selected a block and graded an unattributed window cannot exist, so the
order is not load-bearing — it is the minimal diff.

It is also structurally unreachable from a `--block` run, the same argument the
count's own comment makes: `shown` is `[i for i, w in enumerate(windows) if
w.block is selected]`, and `w.block is None` cannot be in it. So no guard is
needed, and the arm adds nothing a `--block` run can reach.

The `That contradicts the static prediction …` / trigger-group split below is
**untouched**. Scoping is not retracting: a PL that moved inside a window is
still the more interesting outcome, exactly as
`test_a_per_block_movement_is_scoped_before_the_attribution` already argues for
the `--block` arm. This change states what the run can say about *where* the
claim is over; it does not tell the operator to capture less.

The count print at `:2568-2584` is also untouched, and its comment stays true
rather than nearly so — "every branch reachable with it non-zero states its own
scope below" is now true of four branches rather than three.

## Why no new `testdata/` fixture

The committed bytes are the fixture. `0751-isolation-run-unplaced-window/*.csv`
is on disk, reproducible offline, and the derived run is one row away, and the
test builds it with `copies_of` + `insert_after` — the two helpers
`staged_copies` uses, whose docstrings state the rule this case falls under:
"a case that is about one row in one capture is a property of that row rather
than a second shape of the day."

A fourth derived directory under `unplaced-window/`'s naming was the other
reading. It would buy a `testdata/README.md` row and a fourth set for the
equality to hold, for a shape the helper already provides, and the naming
convention's whole job is to be the thing a fixture is when it is worth
carrying around on its own. The written-up recipe above reproduces the case
from the committed bytes in three commands, which is what a directory would
have been for.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, 93 tests on this branch's merge base
and 94 after, all passing under
`python3 ec/tools/test_grade_0751_isolation.py`:

| test | what it holds |
|---|---|
| `test_a_movement_in_the_graded_windows_of_a_partly_unplaced_run_is_scoped` | `unplaced-window/` with one `0x0784` row, three legs. **First**: rc 0; #530's count still `2 of the 8` and still only a count; the movement line unchanged at `PL1/PL2/PL4 (§4.1)`; the new scope naming all 8 and the 2 as part of it; the capture-level comparison declined in the no-movement arm's words and **not** the withheld arm's (`a run it only read part of` asserted absent); `That contradicts the static prediction` still printed and `host-written reload mailbox` still absent; and the other four siblings' texts — `were not graded`, `That is the 6 window(s) that were graded`, `That is block`, `No window in this run was graded` — plus the no-movement arm's narrowing, so a run that moves cannot pick up a `None … moved` sentence. **Second (the load-bearing one)**: the same copy with the row at `12:00:05`, inside the stray, and the two closing sections asserted **equal**. **Third**: `--block 0xA0` over the first copy, rc 0, the per-block sentence at its 3 windows, and the new arm absent |

The second leg is the one that fails if anyone writes the withheld arm's
phrasing: "that is the 6 windows that belong to a value under test" is true at
`12:00:43` and false at `12:00:05`, and the equality is what makes the
difference visible to a test rather than to a reader. The first leg's negative
for that phrase is not a substitute for it — `That is the 6 window(s) that were
graded` is a different string, and a sentence could pass it while still
narrowing the movement to 6.

The test fails against the unfixed tool, on the missing scope line and nothing
else.

## What must not change, and did not

Measured rather than asserted: this branch's tool and
`git show 061b2213:ec/tools/grade_0751_isolation.py` were run over **every**
`ec/tools/testdata/0751-isolation-run*/` directory four ways — unscoped, and
`--block` at each of `0xA0`, `0x10` and `0x00` — and all **48** pairs of
reports were diffed. **All 48 are byte-identical and no exit code moved.**
(48 is 12 directories × 4: the eleven `0751-isolation-run-*` sets plus
`0751-isolation-run/` itself, which is what `0751-isolation-run*/` matches.
The 40 in the earlier write-ups in this family is the same measurement over
the sets that existed on the tree they were written against.)

That number is the point: the change is a disclosure on **exactly one
uncommitted combination** and nothing else. `3blocks-moved/` has
`graded_unplaced == 0`, so the arm is silent there; `unplaced-window/` and
`unread-window/` move nothing, so the `moved_groups` branch is not entered. If
any pair had differed, the arm would be reaching further than intended and the
change would be wrong.

`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` is not touched: §6's
fenced file list and `0751-isolation-run/` are held equal by the test suite, no
fixture was added to that directory, and §6's command line is unchanged. A
`--block` run over a `0x0751` value still gets the per-block sentence, as the
test's third leg shows.

## Left out on purpose

- **The `if withheld:` arm when `withheld > 0` *and* `graded_unplaced > 0`** —
  that is [issue #724](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/724)'s
  half, a different sentence with a different fix: `That is the {graded}
  window(s) that were graded` names a set that includes an unattributed window.
  It is reached from the same branch and by the same count, and it is
  deliberately not touched so the two do not fight over one sentence. **This arm
  is that path's counterpart and not its fix** — a reader who wants the withheld
  case over the same set of `graded` windows wants #724.
- **The `UNPLACED_GRADED_NOTE` count line, the no-movement chain, and the
  trigger-group / `That contradicts …` split** — unchanged, and the third test
  above is what would notice.
- **A new `testdata/` directory and a new `testdata/README.md` row** — the
  reading above. The `elif graded_unplaced:` clause in the `unplaced-window/`
  row names *that branch* and stays true; it is amended to say so, not to admit
  a second fixture.
- **`ec/annotations/registers.yaml`** — this is not a register-status change.
  `MANUAL_FAN_CTRL` stays `present-untested`. **There is no row edit to look for**
  — none was missed. There is no register behaviour anywhere in this.
- **`ec/annotations/manual-fan-ctrl-0751.md`** — §5 is quoted by the sentence
  this change leaves in place, not restated or re-derived here.
- **`ec/README.md`** — its entry describes `--block` scoping and the dump
  groups; it does not enumerate the closing section's cases, so nothing there
  goes stale. Leaving it alone is also one fewer shared file open against the
  other agent PRs.
- **#706, #707, #500, #506, #495, #515** — not duplicated here.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the commands above against the revisions each
transcript names, and with the test named. No live run, no register readback, no
hardware observation; no line of this change may be read as a report of a
capture, and none is one. `0x0784` is a row in a file someone wrote by hand, and
the `0x50 -> 0x28` step is the step
`0751-isolation-example-active.csv` records, not a measurement of this machine's
PL bytes. `confirmed-inert` is §7's call, made by a human holding the rest of
the notes, and nothing here bears on it either way.
