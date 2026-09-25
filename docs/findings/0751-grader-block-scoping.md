# A `--block` run exited 1 over a window it neither printed nor withheld, and did not say why (issue #498)

The write-up for [issue
#498](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/498), which is
about `ec/tools/grade_0751_isolation.py`'s closing summary being silent about
the one refusal `--block` does not narrow. It is a disclosure change: **no
byte is read differently, no window is graded or withheld differently, and the
exit code is unchanged at 1 on every fixture that was 1 before.** Nothing here
is a register behaviour and nothing here is evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value.

---

## The defect, on a committed fixture with nothing edited

`ec/tools/testdata/0751-isolation-run-unread-window/` is
`0751-isolation-run-unplaced-window/` byte for byte with one mark's label
changed: the first of that set's two block-less `restore` marks reads
`'restored it somehow'` in all three captures, a form §6 does not fix. The two
sets are therefore the same day with a single variable, and that variable is
the whole of what separates the two rows below.

    python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-unread-window/*.csv --block 0xA0

printed, before this change:

```
=== block 1 of 2, its integrity check ===  (value under test 0xA0)
    the other 1 block(s) were not checked in this run; run it without --block to check them all
  block 1/2: intact -- last mark 'restored 0x0751=0x10' is the restore

=== what this does and does not settle ===
  None of the §4.1-§4.3 bytes moved in any window: consistent with the static prediction, for this capture's window only (§5: a byte that does not move inside the window may still move at the next suspend, AC transition or EC reset).
```

and prints, after it:

```
=== block 1 of 2, its integrity check ===  (value under test 0xA0)
    the other 1 block(s) were not checked in this run; run it without --block to check them all
  block 1/2: intact -- last mark 'restored 0x0751=0x10' is the restore

=== what this does and does not settle ===
  A mark this cannot read is a mark no block can be attributed to, and the labels are the only thing that says which block a window is a window of: one the parse cannot place could have been a write -- in which case the capture is holding a block this run cannot name -- or a restore typed between a block's write and its restore, which would close that block early and leave it void rather than intact. So a capture carrying one cannot be read block by block: --block narrows what is graded, not what is known, and this refusal holds for the whole run whichever block was selected. The census above names every mark the parse could not read, per capture; the fix is the label, which has to be one of the three forms §6 fixes. The exit code is 1 until they do.
  None of the §4.1-§4.3 bytes moved in any window: consistent with the static prediction, for this capture's window only (§5: a byte that does not move inside the window may still move at the next suspend, AC transition or EC reset).
```

**The exit code did not change; what changed is that there is now a sentence to
read.** Before, a fold-in reader saw `intact`, no withheld banner, the clean
closing sentence, and a non-zero exit, and had to go back through the census to
find `UNREADABLE unplaced 'restored it somehow'` — the one place the refusal
was disclosed, and it was not joined to the other two facts anywhere in the
report.

The two halves, over the same bytes:

| run | exit | closing section | refusal disclosed |
|---|---|---|---|
| `unread-window/*.csv --block 0xA0` | 1 | the clean sentence, alone | only in the census |
| `unplaced-window/*.csv --block 0xA0` | 0 | the clean sentence, alone | no refusal anywhere |

## The correction to the issue's premise

The issue reports that "the tree states both conventions and picks neither." It
picks one, in two places the report did not cite:

- `unplaceable_marks`' docstring, `ec/tools/grade_0751_isolation.py:688-692` —
  *"Fatal for the whole run rather than for one block, which is the
  conservative direction and the reason for it: block attribution rests
  entirely on the labels, so a mark this cannot read leaves every block's
  completeness uncertifiable — not only the one it would have landed in.
  `--block` scoping narrows what is graded, not what is known."*
- `ec/tools/test_grade_0751_isolation.py:2221-2222` — *"a capture carrying one
  is still **fatal for the whole run** however it got there."*

So the exit code is not the defect. The **silence about it** is, and this is
option (b) from the issue: keep the capture-scoped exit and print the line the
withheld banner would have printed.

## Why the refusal is the run's, and not the block's

Not a matter of taste — the mechanism decides it. An unreadable label could
have been a **`write`**, in which case the capture is holding a block the run
cannot name and `--block 0xA0` may not be the block the caller meant. Or it
could have been a **`restore`** sitting between a block's write and its
restore, in which case the selected block closes early and is **void**, not
`intact`, and the `intact` verdict above it is the wrong answer rather than
merely an overreach.

Scoping `unreads` to `shown` would scope a fact that is not a property of the
selected block, and would let `--block` print `intact` and exit 0 over a block
that is void. That is the "says more than it read" shape this tool exists to
stop, introduced *by* the fix. It is also not smaller in the way that matters:
the census line "`--block` cannot select it" explains why a window was not
*selected*, not why the process exited 1, so scoping the exit code would leave
it exactly as unexplained while weakening the gate a fold-in reads.

## The change

Confined to the closing-summary block in `ec/tools/grade_0751_isolation.py`,
one new module constant, one comment, and one test.

- `UNREAD_MARK_NOTE`, beside `VOID_BLOCK_NOTE`, `MARK_SET_NOTE` and
  `INTACT_BLOCK_NOTE`, in the same voice and ending the way those two do — by
  saying what the exit code is. It carries the scoping clause (`--block
  narrows what is graded, not what is known`) and `unplaceable_marks`’ reason,
  and cites that docstring rather than restating it.
- Printed once in the closing section when `unreads` is non-empty, immediately
  after the withheld banner and before the movement sentence, so both reasons
  a run is refused read in one place. Beside the banner rather than inside it
  because the two are not one count: `withheld` is the selected block's and
  `unreads` is the run's.
- The note points at the per-capture `UNREADABLE` census lines, **not** the
  `unplaced:` line. The unreadable window is in `unreads` and so never gets the
  latter; a pointer there would send the reader after a line the run does not
  print. Measured: `unplaced-window/` prints "`--block` cannot select it"
  twice, `unread-window/` once.
- The comment above the return, which listed five refusals flat, now classifies
  them by scope: `void` and `withheld` are `--block`-scoped, `unreads` is
  run-scoped, and a `--block` that named no block and a capture named twice are
  refused above and are not in the expression at all.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, 57 tests before and 58 after, all
passing under `python3 -m unittest test_grade_0751_isolation`:

| test | what it holds |
|---|---|
| `test_an_unreadable_mark_refuses_a_block_run_and_says_why` | `unread-window/ --block 0xA0`: rc 1; the note in the closing section; the scoping clause and the exit-code sentence; `block 1/2: intact` and no `NOT GRADED` and no `were not graded`, so the note is demonstrably the thing joining the exit code to a reason; the census pointer resolves (one `cannot select it` here, two in the pair) |
| the same test, second half | `unplaced-window/ --block 0xA0`: rc 0 and the note **absent**, over the same bytes with one label different |

The second half is what makes "the note is printed exactly when this refusal
fires" a property of the tool rather than a fact about one fixture. The test
fails against the unfixed tool, which is the check that it is testing the
defect and not the fixture.

**The pre-existing pins that stayed green and were not edited** are the
evidence that nothing else moved. `test_a_mark_that_is_not_one_of_the_three_forms_is_an_error`
is the one this change could have broken silently: its hand-written `mark 3`
fixture has unreads, so it now carries the note too, and it asserts
`out.count('block: unplaced') == 2` and
`out.count('block: unplaced -- NOT GRADED') == 1`. **The note therefore does not
contain the literal string `block: unplaced`**, and a change that later adds it
will fail that test — which is the intended kind of coupling, not a lint to
route around.

## What must not change, and did not

The *unscoped* run over the same fixture still withholds 1 of 8, still declines
the run-level comparison in the `elif withheld:` branch, and still exits 1 —
that is right and it is untouched. The four tests #486 added stay green; none
of them asserts on `unreads`-free output that the note could reach.

Measured rather than asserted: the old tool from `HEAD` and this one were run
over each of the nine `0751-isolation-run-*/` fixture directories four ways —
unscoped, and `--block` at each of `0xA0`, `0x10` and `0x00` — and all 36 pairs
of reports were diffed. **Three changed, and each by exactly one added line:
the note.** They are the three `unread-window/` invocations that reach the
closing section (the fourth, `--block 0x00`, names no block in that capture and
is refused before the section prints, unchanged in both). No exit code moved.
The one-capture `mark 3` case in
`test_a_mark_that_is_not_one_of_the_three_forms_is_an_error` is the only other
reachable run with unreads, and diffing it the same way gives the same single
added line.

## Left out on purpose

- **The unqualified "consistent with the static prediction" sentence.** A
  `--block` run that grades one block of a day still prints it unqualified, and
  that is a real adjacent gap — but it is #495, which runs the *opposite*
  direction (a sentence that says more than it read, rather than an exit code
  that says more than it printed). The new note carries the scoping clause,
  which is what this issue asks for. Leaving that sentence alone keeps the two
  PRs off the same lines.
- **A new fixture.** `unread-window/` already holds the case and is what the
  issue names; a second would only widen the shared testdata tree.
- **`unplaceable_marks`' docstring.** Already states the chosen convention
  correctly; the new comment cites it rather than restating it.
- `ec/annotations/registers.yaml` is not touched: no register status is in
  question, and `MANUAL_FAN_CTRL` stays `present-untested` with its
  `static_refs*` counts at 29/29/0.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the command above and the test named. No live run,
no register readback, no hardware observation; no line of this change may be
read as a report of a capture, and none is one.
