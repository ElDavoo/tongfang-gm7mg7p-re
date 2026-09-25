# A stray `restore` the consoles spelled two ways, or that one console missed, was graded in full (issue #529)

The write-up for [issue
#529](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/529), about
`ec/tools/grade_0751_isolation.py` applying two of §3's three per-window mark
checks only to windows that fall in a block. It is a grading change: **one
window in a committed fixture is now withheld and one exit code moved from 0 to
1.** Nothing here is a register behaviour and nothing here is evidence about the
machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value.

---

## The reach, as the code stood

`main` handed `check_block_marks` the blocks and `unplaceable_marks` the
leftovers, and those were the only two things it handed anything to:

```python
    blocks, unplaced = assign_blocks(windows)
    unreads = unplaceable_marks(unplaced)
    for block in blocks:
        block.problems = check_block_marks(block, captures)
```

`check_block_marks` is where the two agreement checks live — its own docstring
names them, *"an action some capture did not record"* (`missing`) and *"an
action the captures spelled differently"* (`labels`) — and it iterates
`block.windows`. A window `assign_blocks` could not place is in no block, so it
reached neither loop. The window section then fell it through to
`report_window`, counted it in `graded`, and let its rows feed `moved_groups`.

The exit expression is `1 if (void or unreads or withheld) else 0`. A stray
whose label parses is in none of the three: it is not `void`, because a block
never opened it; not in `unreads`, because the parse read its label; and not
withheld, because no check reached it. So the run exited **0** over a capture
whose own census had just printed the defect.

That the census saw it is not in question — `report_census` prints the
diagnosis for both defects already. The gap was the *consequence*: the report
named the disagreement and then went on to grade the window it belonged to, in
the same confident format it uses for a result.

## Measured, on a committed fixture

`ec/tools/testdata/0751-isolation-run-unplaced-window-failures/` is
`0751-isolation-run-unplaced-window/` byte for byte with one thing wrong with
each of its two block-less restores: the 12:00 one is spelled
`restored 0x0751=0x0a` in the `0x0700` capture where the other two say `0x99`,
and the 12:04 one is absent from the `0x0F00` capture altogether. Both labels
still parse, so neither is an `unreads` case — this is the shape
`0751-isolation-run-unread-window/` cannot reach, which is a stray refused for
what the parse could not read rather than for what the captures said. Both
blocks are intact and their six windows are that set verbatim.

"Before" below is `git show HEAD:ec/tools/grade_0751_isolation.py` on the same
command, and "after" is this branch's file, so the transcripts name the
revision they were recorded against:

```
    python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-unplaced-window-failures/*.csv
```

Before, exit **0**, and the 12:00 stray printed in full:

```
--- mark 1/8: 2026-01-01T12:00:02+01:00  'restored 0x0751=0x0a / restored 0x0751=0x99' (...)
    block: unplaced
    window runs to the next mark
    no watched byte moved in this window
    ...
```

with the closing section's whole-capture sentence, unqualified, over a run that
had just been told by its own census that one of its strays was recorded three
ways:

```
  None of the §4.1-§4.3 bytes moved in any window: consistent with the static prediction, for this capture's window only (§5: ...).
```

After, exit **1**, and each stray is refused in its own place with the problem
that produced it:

```
--- mark 1/8: 2026-01-01T12:00:02+01:00  'restored 0x0751=0x0a / restored 0x0751=0x99' (...)
    block: unplaced -- NOT GRADED
    not graded -- the captures spell this action differently --
    2026-01-01-0751-isolation-0400-045f.csv: 'restored 0x0751=0x99';
    2026-01-01-0751-isolation-0700-07ff.csv: 'restored 0x0751=0x0a';
    2026-01-01-0751-isolation-0f00-0f5f.csv: 'restored 0x0751=0x99' --
    so the window it opens is not the action any of them recorded.
```

```
--- mark 5/8: 2026-01-01T12:04:00+01:00  'restored 0x0751=0x99' (...)
    block: unplaced -- NOT GRADED
    not graded -- recorded in 2 of 3 capture(s), absent from
    2026-01-01-0751-isolation-0f00-0f5f.csv. The capture(s) that missed
    it have their rows for this arm filed under whichever window their
    timestamps fall in, and nothing in the result ties them to the
    arm whose mark is gone -- so this arm can read quiet for
    want of a mark rather than because nothing moved.
```

and the closing section with the partly-graded branch, which is the one this
case now belongs to:

```
  2 of the 8 window(s) above were not graded: the mark set of the block they fall in does not hold, or the window falls in no block at all and either no label could be read for it or the captures disagree about the action it opened. What they would have shown is not reported here and is not to be quoted from this run.
  None of the §4.1-§4.3 bytes moved in any of the 6 window(s) that were graded: ...
```

## The change

Two functions and three lines in `main`, in `ec/tools/grade_0751_isolation.py`,
plus five places where leaving a string alone would have made the output say
something false.

- **`window_mark_problems(w, names, known)`**, the body of `check_block_marks`'s
  per-window loop, lifted out rather than copied. Both checks are properties of
  the marks alone — which captures recorded the action, and whether they spelled
  it the same way — and neither names a block, which is why a window in no block
  can be given the same two as one in a block. `check_block_marks` calls it per
  window and keeps its `void` loop.
  **Its name, signature and return shape are unchanged**, and that is the one
  place this could have broken a reader the implement stage cannot see:
  `test_grade_0751_isolation.py` calls it directly, `docs/findings/0751-grader-block-scoping.md`
  cites a line number inside its comment, and #450 and #451 are open against the
  same function.
- **`unplaced_window_problems(unplaced, captures)`**, beside
  `unplaceable_marks`, returning `{window: [text, …]}` — the shape
  `unplaceable_marks` returns, so the branch that reads it looks like the one
  above it. Its docstring says which checks come along and which does not.
- In `main`: the call beside `unreads`, and a third refusal branch in the
  `shown` loop, after the `unreads` branch and before the block branch. The
  order is for the reader — the two unplaced refusals sit side by side, and the
  block branch could not fire for these windows anyway since `w.block is None`.

**The exit expression is untouched.** `withheld` already feeds it, so the
refused stray turns the exit to 1 for free. That is why the refusal is counted
into `withheld` rather than added as a fourth term.

### `void` stays block-scoped, and that is a property of the check

`void` is *a block's last recorded mark in some capture is not the restore*,
tested through `block.marks_in(path)`. A window in no block has no block to
have a last mark in, so there is nothing for the check to be false about. It is
not skipped because looking found no case; it is not defined over a window.
`window_mark_problems`' docstring and `unplaced_window_problems`' say so, and
the census line for an unplaced window was reworded to name the one check that
does not reach it and why — the previous wording said *"no §3 integrity check
covers it"*, which this change made false.

## The scope decision, and its `--block` consequence

The new refusal is **window-scoped**, like a block's problems — **not**
run-wide like `unreads`. This is a judgement call, so the reasoning:

`unplaceable_marks` is run-wide because an unreadable label could *be* a
`write` or *be* a `restore`, so it can change the block structure and leave
every block's completeness uncertifiable — reasoned at
`grade_0751_isolation.py:689-695` and in `windows/tools/ec_watch-marks.md:60-66`.
A stray the consoles spelled differently, or that one console missed, cannot do
that: it is already in no block, and no block's completeness rests on it.
Making it run-wide would turn a `--block 0xA0` fold-in attachment into exit 1
over a defect in a window that attachment does not print, which is a stronger
claim than the evidence supports.

Measured, over the same fixture:

| run | exit | what the window section says |
|---|---|---|
| unscoped | 1 | both strays `block: unplaced -- NOT GRADED` |
| `--block 0xA0` | 0 | neither stray printed, not printed nor withheld; block 1 `intact` |
| `--block 0x10` | 0 | as above, block 2 `intact` |

**Scoping the refusal does not lose the finding.** `report_census` prints whole
even under `--block` — that is its own documented choice, so a run that scoped
itself can be seen to have done so — and it already names the absent capture
for the 12:04 stray and the disagreeing value for the 12:00 one. The refusal is
withheld; the diagnosis is not. A reader who runs the whole capture gets both.

If a reviewer reads the scope the other way, the change is one term: hoist
`unagreed` out of the `shown` loop into a run-wide count and add it to the
return at the end, the way `unreads` is handled. That is recorded here rather
than left implicit because it is a real alternative and the exit expression is
the only thing standing between the two.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, 69 tests before and 72 after, all
passing under `python3 -m unittest test_grade_0751_isolation` from
`ec/tools/`:

| test | what it holds |
|---|---|
| `test_a_window_in_no_block_fails_the_same_agreement_checks` | `unplaced-window-failures/`: rc 1; two `block: unplaced -- NOT GRADED`; the `labels` refusal naming the `0x0a` spelling per capture and the `missing` refusal naming the `0f00` capture; both blocks `intact` with all three of their windows printed in the usual format; `2 of the 8 window(s) above were not graded` and `6 window(s) that were graded` |
| `test_a_window_in_no_block_whose_marks_agree_is_not_refused` | `unplaced-window/`: rc 0 and **`NOT GRADED` absent**, all eight windows graded, both strays under a plain `block: unplaced`. Then `unread-window/`: still exactly one `block: unplaced -- NOT GRADED`, 1 of 8 withheld and 7 graded, the 12:04 stray still graded |
| `test_the_unplaced_window_problems_name_their_kind_per_window` | the function directly: one entry per failing window keyed by the window, one problem each, the kinds `['labels', 'missing']` in mark order, and **`{}` over `unplaced-window/`** |

**The clean half is the one that matters most.** Nothing in the tree asserted
`NOT GRADED` is *absent* over `unplaced-window/` before this — the clean half
of the unreadable-mark test stands on rc 0 plus a census count — and a check
that has quietly started refusing everything looks exactly like a check that is
working. The last assertion above, `{}` over the clean set, is the same
property from the other side and is the one that fails if the check fires on
marks that agree.

Both new failure tests were run against `git show HEAD`'s copy of the tool and
fail there — the first on `rc 0 != 1`, the third on the function not existing.
The clean test passes on both, which is what a regression guard should do.

The 69 pre-existing tests stay green and none was edited, which is the evidence
that nothing else moved. Measured rather than asserted: the old tool and this one
were run over each of the ten `0751-isolation-run-*/` directories four ways —
unscoped and `--block` at each of `0xA0`, `0x10` and `0x00` — and all 40 pairs
diffed. **Sixteen are byte-identical. Of the 24 that changed, exactly one moves
an exit code**: the new fixture, unscoped, 0 → 1, which is this issue. Every one
of the other 23 differs only in the two strings this change had to reword
because the old wording would have said something false — the withheld
banner's stated reason (14 runs) and the census line's clause about what
covers an unplaced window (12 runs, two of them showing both). **No window
body, no block verdict and no count differs anywhere else**, and no other
fixture has a window graded or withheld differently.

## Left out on purpose

- **The `rem` block in §6 of the procedure doc**
  (`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md:630-635`) describes
  the refusal in block terms and is now incomplete. The section's §3 text
  (`:176-181`) and that `rem` block's first sentence already say *"every action
  in all three CSVs, every capture spelling it the same way"* — the contract
  this change makes the tool meet, and nothing there is falsified — so the
  repair is a sentence in a long shared file this branch has no reason to be
  near. Named as a follow-up instead.
- **`windows/tools/ec_watch-marks.md`.** `:107-108` (*"the mistyped digit that
  survives is what the three-console comparison is for"*) is *supported* by this
  change, and `:109-111` names `parse_mark`, `unplaceable_marks` and
  `build_windows` as the three relevant functions, none of which this touches.
- **`ec/annotations/registers.yaml` is not touched**: no register status is in
  question, and `MANUAL_FAN_CTRL` stays `present-untested` with its
  `static_refs*` counts at 29/29/0. A refusal is not a verdict.
- **Making the new refusal run-wide** — named and argued against above; one term
  in the exit expression if read the other way.
- **Extending `void` to windows in no block** — it has no meaning there, and the
  docstring says so rather than the check being quietly skipped.
- **A second fixture directory for the second defect kind.** The two defects are
  two *kinds*; the test discriminates on the per-window refusal text rather than
  on the directory name, and a second directory would double the README row and
  the test code to learn nothing more.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the command above, against the revision each
transcript names, and the test named. No live run, no register readback, no
hardware observation; no line of this change may be read as a report of a
capture, and none is one. What §3's six mark rounds would do on real
consoles is what this change makes the grader able to notice, and the next
§6/§7 day is the run that would show it.
