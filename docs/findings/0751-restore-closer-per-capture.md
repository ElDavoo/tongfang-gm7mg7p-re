# A block that closed on the restore in two of three consoles read `intact` (issue #450)

The write-up for [issue
#450](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/450): the
`0x0751` grader's per-block verdict was a statement about whichever console's
mark the three fused labels were read from, so a block whose restore mark
reached two of §3's three captures printed the bare word `intact` — the word a
fold-in files. This is a change to what a report says about the files it was
handed, not to what it says about `0x0751` or about the EC.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §3 is the block and
§6 the file set and the labels.

---

## The reach, as the code stood

`block_verdict` was one line over the block's last *fused* window:

```python
    last = block.windows[-1]
    return "intact" if parse_mark(last.label)[0] == "restore" else "void"
```

and a fused window is built by `coalesce_marks`, which joins the consoles'
labels for one action with `" / "` and takes the group whole. `parse_mark`
returns on the first part that matches, so the role of a fused window is the
role of whichever console's spelling was read first, and its *existence* is
whichever console recorded a mark at all.

The three consoles are three processes reading three ranges, and §3's mark
rounds are typed into each of them by hand. Nothing about a mark's presence is
shared between them: one console recording it is not two. So a block whose
restore reached `0f00` and `0400` and missed `0700` had a fused last window
reading `restored 0x0751=…`, and `block_verdict` called it `intact` on the
strength of one of the two.

Which console is short is not fixed — it is whichever of the three failed to
record the mark, and `closers_note` names that one. But when it is `0x0700`
the consequence is the worst of the three: §3 starts its three watchers over
`--start 0x0700 --len 0x0100`, `--start 0x0F00 --len 0x0060` and
`--start 0x0400 --len 0x0060`, so **`0x0700` is the only capture of the three
whose sweep covers `0x0751`** and therefore the only one that can hold the
byte's own change rows. A restore mark that reached the other two and not this
one leaves that capture holding the byte's evidence for the arm with nothing
in it saying which arm the rows belong to. That is the case the fixture below
is built to hold; when `0f00` or `0400` is the short one instead, the
`0x0700` capture holds the restore and its rows stay attributable.

**The block was not silently graded, and the diff has to say so.** The checks
`check_block_marks` already ran were enough to refuse the run:
`window_mark_problems` raises a `missing` problem for the restore window, the
per-capture void check raises a `void` one, every window is withheld, and the
exit code is 1. The false green was confined to the verdict **word and the
sentence attached to it**, which is the whole of what this change is about
rather than a claim that the block graded. A reader taking the block section
into a fold-in was told `intact`; a reader of the census above it was told the
block is not graded.

Measured, on the fixture this change adds
(`ec/tools/testdata/0751-isolation-run-restore-short/`), against the grader as
it stood before this change (block 2's restore is in the `0f00` and `0400`
captures and not the `0x0700` one):

```
    git show origin/main:ec/tools/grade_0751_isolation.py > /tmp/grade-before.py
    python3 /tmp/grade-before.py ec/tools/testdata/0751-isolation-run-restore-short/*.csv
```

The census's per-block line:

```
  block 1 of 2: value under test 0xA0, roles control, write, restore
  block 2 of 2: value under test 0x00, roles control, write, restore -- NOT GRADED, 2 problem(s): missing, void
```

and the block section's verdict lines, further down the same output:

```
=== 2 block(s), one per no-op control arm (§3) ===
  block 1/2: intact -- last mark 'restored 0x0751=0x10' is the restore
  block 2/2: intact -- last mark 'restored 0x0751=0xA0' is the restore
```

Exit **1**. The two lines above are the same block read by two sections, and
only one of them is the sentence a fold-in takes.

## What the issue's other two identifiers are

Two names in the issue do not exist in the tree: there is no `mark_word`, and
the cited line numbers are of a revision where the file was shorter. The
function that reads a label is `parse_mark`, and the one that joins the
consoles' labels for one action is `coalesce_marks`. The substance is real; the
identifiers are not. Nothing was rebuilt against them.

The issue's second request — grading the label-equality rule §6 already states
— was already met and is pinned rather than reimplemented: it is
`window_mark_problems`' `("labels", …)` problem, it already gets a line of its
own on the window header, `report_census` prints each capture's spelling under
the action, and `0751-isolation-run-disagreeing-marks/` is its fixture.

## The change

**`Block.closers`** — `(capture, that capture's last mark in this block)` per
capture that recorded anything in the block, as a **property** over the block's
own marks rather than a field something assigns. Every mark carries the capture
it was recorded in (`m.source`), so the per-capture answer is already on the
block; deriving it means `block_verdict` is a statement about a block rather
than about what has been run over one.

That last point was not the first design and the difference is worth
recording. Storing the record and filling it in `check_block_marks` — the
caller that already reads `block.marks_in(path)` per capture to raise the
`void` problem — looks like the better anti-drift shape, and the change was
written that way first. It broke
`windows/tools/test_manual_fan_ctrl_probe.py`'s
`test_a_second_run_appends_to_the_same_capture`, which builds blocks from
`assign_blocks` and asks `block_verdict` what they closed on without running
any check over them: it got `void` over an empty record, for two blocks whose
marks are all present. A committed consumer of the function, with its own
`--self-test`, was answering "these blocks did not close" about blocks that
did. A property is the same single computation with that whole class of caller
wrong instead of right.

**`block_verdict`** returns three words over that record instead of one over
the fused window:

- `intact` — every capture that recorded anything in the block closed on the
  restore;
- `void` — none of them did. Its word and the sentence it opens with are
  unchanged and the capture note is appended to it, so
  `0751-isolation-run-3blocks/` still opens its line with `block 2/3: VOID --
  last mark is 'wrote 0x0751=0x00', not the restore` and still exits 1;
- `PARTIAL` — some did and some did not.

`PARTIAL` is a word of its own rather than a qualified `intact`, because
`intact` is the word a fold-in files and the whole point is that a fold-in
must not be able to file this one. It counts in `report_blocks`'s existing void
tally and routes to `VOID_BLOCK_NOTE`, which gained one clause naming the mixed
case: a block short its restore in one console is as unable to close that
console's last window as one short in all three.

**`closers_note`** appends the per-capture answer to every block line, and
every block verdict now names the captures its word rests on. The label a
capture that did not close ended on is quoted with it, since that is the row
the operator has to go and find. The existing sentences are *appended to*, not
rewritten, so the `block 1/1: intact -- last mark 'restored 0x0751=0x10' is
the restore` assertions and the `out.count(': intact -- last mark', N)` counts
elsewhere in the suite keep passing untouched; the new word deliberately does
not contain that substring.

**`block_marker`** gained a branch for the third word, so a `--dump` read under
a withheld `PARTIAL` block's value carries `PARTIAL, its windows were withheld
above -- the restore is not in every capture` rather than falling through to
the mark-set wording, which would send the operator after a mark the block has
in two consoles.

Measured, over the same fixture and the same command after the change:

```
=== 2 block(s), one per no-op control arm (§3) ===
  block 1/2: intact -- last mark 'restored 0x0751=0x10' is the restore; the restore is in 2026-01-01-0751-isolation-0700-07ff.csv, 2026-01-01-0751-isolation-0f00-0f5f.csv, 2026-01-01-0751-isolation-0400-045f.csv
    value under test 0xA0; roles control, write, restore
  block 2/2: PARTIAL -- last mark 'restored 0x0751=0xA0' is the restore, but not in every capture; the restore is in 2026-01-01-0751-isolation-0f00-0f5f.csv, 2026-01-01-0751-isolation-0400-045f.csv -- 2026-01-01-0751-isolation-0700-07ff.csv ends on 'wrote 0x0751=0x00'
    value under test 0x00; roles control, write, restore -- NOT GRADED, its windows are not printed
```

Exit **1** still, and the two blocks now read differently in one output rather
than across two runs — which is why the fixture is a two-block day and not two
directories.

## The fixture

`ec/tools/testdata/0751-isolation-run-restore-short/`. Block 1 is the
existing `0xA0` block, and it does not come from one existing set: it is
`0751-isolation-run/`'s byte for byte in the `0x0700` and `0f00` captures and
`0751-isolation-run-missing-mark/`'s in the `0x0400` one. The `0f00` capture
follows `run/` because the point of block 1 is a block that closed *everywhere*,
and `missing-mark/` is short its control-arm mark there. The `0x0400` capture
follows `missing-mark/`, whose `0x0402` row it carries where `run/` has `0x0438`
— a row inside block 1's own `no-op wrote 0x0751=0x10` window, so which set a
capture came from is visible in the report and not only here:

```
    for b in 0751-isolation-run 0751-isolation-run-missing-mark; do for r in 0700-07ff 0f00-0f5f 0400-045f; do
      echo "== $b/$r"
      diff <(grep -v '^#' ec/tools/testdata/$b/2026-01-01-0751-isolation-$r.csv | awk -F, '$1 < "2026-01-01T12:03"') \
           <(grep -v '^#' ec/tools/testdata/0751-isolation-run-restore-short/2026-01-01-0751-isolation-$r.csv | awk -F, '$1 < "2026-01-01T12:03"')
    done; done
```

That prints nothing for `run/`'s `0700` and `0f00` and the one `0x0438` /
`0x0402` line for its `0400`; the same three against `missing-mark/` print
nothing for its `0700` and `0400`, and for its `0f00` the two differences its
short control-arm mark leaves behind. Block 2 is a `0x00` block whose restore
mark is in the `0f00` and `0400` captures and not the `0x0700` one. The `0x0700`
capture keeps **both** of block 2's `0x0751` change rows — `0xA0 -> 0x00` and
`0x00 -> 0xA0` — so the issue's premise ("the capture that holds the byte's own
change rows has no restore in it") is a checkable property of the fixture
rather than an assertion
about the tool, and `RestoreCloserPerCaptureTests` reads it back out of the
files so editing a row fails the test.

No committed fixture reached this shape. `missing-mark/` loses the *control*
mark and holds its restore in all three; `disagreeing-marks/` loses nothing;
`3blocks/` loses the restore in all three; `unplaced-window-failures/` loses a
stray rather than a block's closing mark.

## What is not claimed

- **Nothing here says anything about `0x0751`.** A `PARTIAL` block is a
  statement about which files were handed in and which of them hold the mark
  that closes the block. It is not a §7 verdict: §7 moves `MANUAL_FAN_CTRL`
  off `present-untested` on fan duty or package power moving under a fixed
  load, which is a question about change rows this change does not touch.
- **No live run happened.** This repository has no laptop and no Windows host.
  The fixture is a shape written by hand; §3's three consoles were not run, no
  mark was typed at a machine, and no capture was taken. Every byte in the new
  directory is invented, as the header of each file says.
- **`PARTIAL` is not a claim that the restore happened.** It is the absence of
  evidence that it happened in *some* capture, which is what a missing mark
  leaves. A block can read `PARTIAL` with the byte correctly put back; the
  tool cannot tell that from the files, and does not say it.
- **Only the `PARTIAL` clause asks `parse_mark`; `intact` and `void` still
  quote the fused label.** A fused window can hold one console's mark *and*
  another's from the same action, and `parse_mark` reads whichever was typed
  first. That does not make the other two clauses false — a block that closed
  in every capture or in none has a clause that is a statement about the block
  and holds either way — but a block that closed in *some* of them can end on
  a fused label the parser reads as the short console's write, and calling that
  the restore on the line that names the write as what the short capture ended
  on is a sentence contradicting itself. Building all three from `Block.closers`
  instead is a wording change to two sentences this issue does not otherwise
  touch.
- **Per-capture *windowing* is out of scope.** Grading each capture's windows
  separately rather than the fused ones would rewrite `coalesce_marks`,
  `build_windows`, every window header and the census, and would break the
  side-by-side reading of three per-block attachments that §6 is built on. The
  verdict is what a fold-in files and what was unqualified here; the windows
  are a different question and worth their own issue.

## The procedure document

Two sentences of `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`
describe the rule this change makes per capture, and both said otherwise. §3's
paragraph on the check over the capture printed "an `intact` or a `VOID`
verdict for each", and §6's rule that the marks "must leave every block ending
on its restore" sat under an "All three are checked, per block and per
capture" that did not say the verdict word was per capture too — so a reader
following §6 could satisfy "per capture" with a block that closed in one of
three. Leaving the document describing two words while the tool prints three
is the drift every other doc-pair here is written to prevent.

## Where this unblocks something

Nothing in the EC, the BIOS or the Windows stack: this is a change to what a
report says about a capture. What it unblocks is the reading of a §3 day's
output by a person deciding whether a block can be filed. The verdict word was
the one field a fold-in quotes, and it was the one field that could not
distinguish a block that closed on every console from one that closed on one
of three — a distinction that decides whether the capture holding `0x0751`'s
own change rows can be said to have seen what happened to them.
