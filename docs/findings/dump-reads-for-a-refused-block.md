# A read taken for a block whose windows were refused (issue #499)

The write-up for [issue #499](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/499),
which asked `grade_0751_isolation.py` to carry a block's verdict onto the
`--dump` readback and the `--dump-pair` bracket filed under it. It is a
reporting and attribution change: **no EC was read, no register was read back,
and nothing here is a statement about `0x0751` or the machine.**

`docs/findings.md` §23 has the summary. This file has the judgement the issue
left open, and the two scoping rules the change turns on.

---

## The problem, stated precisely

§3's per-block integrity check reads a block as **void** when its last mark is
not the restore: the capture is short a mark, its last window never closes, and
the block is not a finished one. `report_blocks()` prints that verdict and
`main()` withholds the block's windows because of it, and the exit code is 1.

`report_dumps()` and `report_dump_pairs()` were told a block's **value** and
never its verdict. So over §6's own per-block command form — the one §6 tells
the operator to run, once per value, and the one #380's run produces — a void
block got its §4.6 readback and its whole-block bracket read, and printed in
the usual result format, under a section two over from the one that had just
refused it:

```
=== 0x0751 across the dumps (§4.6) ===
  block 0xA0, from the <value> in these files' §6 names
  ...-a0-after-0700.txt: 0x0751 = 0xA0
  the last dump still holds the written 0xA0. Per CLAUDE.md that is a readback,
  not evidence the EC acted on it.

=== whole-block dump pairs (§4.1-§4.3) ===
  block 0xA0, from the <value> in these files' §6 names

  ...-a0-before-0700.txt -> ...-a0-after-0700.txt, 16 address(es) compared
    ...
    other addresses that differ (1), not graded here -- read them against §4.4
    and §4.5 by hand:
      0x0751

=== what this does and does not settle ===
  2 of the 2 window(s) above were not graded: ... not to be quoted from this run.
  No window in this run was graded, so this output says nothing about §4.1-§4.3
  for it -- which is the honest answer here, and not a quiet one.
  The whole-block dump pairs above were read as a second, wider bracket on the
  same §4.1-§4.3 bytes. ...
```

The last two lines are the sharpest form of it: the closing section says this
output says **nothing** about §4.1-§4.3 for the block, and then immediately
reports a read of §4.1-§4.3 for it. A void block is not a remote outcome —
`0751-isolation-run-3blocks/` is built around a restore mark typed after the
watcher exited, which `report_blocks` names as the usual cause.

## Why read-and-mark, and not refuse

The issue left this open ("whether the right answer is 'refuse' or 'read and
mark' is a judgement to make from §4.6's own argument"). This takes **read and
mark**, for three reasons drawn from the tool's own argument.

**The §4.6 readback is a claim about a byte in a file, not about a window.**
"The last dump still holds the written 0xA0" is true or false of two files on
disk, and it is true here whatever the CSV mark set did. A void block is a
statement about the *captures*; §4.6 is a statement about the *dumps*. And the
whole `--dump` mechanism's stated purpose is to report what the files say:
withholding a true fact the operator can use is a loss, not a caution.

**The whole-block bracket is already declared to be a different read, not a
weaker form of the windowed one.** `report_dump_pairs`' own docstring says the
two are complementary, each with a gap the other does not close. A void block
does not make the two dump files agree, stop covering the addresses, or become
the same file. The bracket is still the wider, complementary read it was a
moment earlier.

**Refusal in this tool is reserved for inputs that cannot bear the read.** A
capture given twice (fatal), a pair given one file twice, a pair whose two
names disagree, a `--block` in no block — every one of those is a case where
the read is *meaningless or misattributed by construction*. A void block is not
that. The read is well-defined; it is just not a statement about the block's
windows. The file's established posture is "print the fact, scope the claim";
refusal is the exception.

The one thing not allowed to survive is the **unmarked** read, which is the
defect. So the change is an attribution on two group lines plus a scoped
closing sentence — not a silent read, and not a silent refusal.

## "Refused" has two reasons, and the marker has to key on both

`report_blocks` withholds a block's windows on `block.problems`, not on the
restore check alone — and its own docstring says so: *"A block whose mark set
does not hold is intact here and not graded anyway, which are two different
facts and are printed as two: the restore is there, and an action before it is
missing from a capture. Only the second one withholds the windows."*

So a marker keyed on `block_verdict` alone leaves the same defect standing for
the other refusal reason. `0751-isolation-run-missing-mark/` and
`0751-isolation-run-disagreeing-marks/` are both that shape: one block, its
restore present, an action missing from one capture or spelled two ways in the
middle of it — `block_verdict` calls it `intact`, and `main` withholds all
three of its windows anyway. A read filed under such a block would have gone
out unmarked, which is the defect this issue is about, reached by the other
road.

`block_marker` therefore keys on `block.problems` and names the reason it
finds:

- `VOID, its windows were withheld above`
- `its mark set does not hold, its windows were withheld above`

Neither set carries a dump of its own, so this case is pinned two ways: on
`block_marker` directly, against the real `problems` lists
`check_block_marks` writes for those two fixtures, and end to end by handing
the `0xA0` dumps to those captures — the value under test in both, and the
read is over the dumps either way, which is the whole claim.

This is a finding the issue did not name, and it is the kind that a
"read and mark" change gets wrong by looking like it landed: the void case
looks covered while the mark-set case is not.

## The two scoping rules

**A group this run did not check is given no verdict at all.** This is the
part that is easy to get wrong in the direction that looks more helpful.
`verdicts_for(blocks, selected)` is built from the *same block set
`report_blocks` checked* — every block unscoped, the selected one alone
otherwise. On a `--block 0xA0` run over `3blocks/`, blocks `0x00` and `0x10`
were never looked at, so a group naming `0x10` gets the existing
`belongs to block 0x10, not the block under test (0xA0) -- not read` line and
no verdict. An index over every block would print "0x00 is VOID" about a block
the same report had said it did not check — the defect this exists to fix, one
step removed.

**A value in no block is not the same as a block with nothing to mark.** A
`--dump` naming a value this run has no block for printed, before and after,
exactly like a normal result. `verdicts` distinguishes the three states: an
entry with a non-empty marker (a block whose windows were withheld), an entry
with an empty marker (checked, nothing to mark), and no entry (not checked, or
no such block). Only the first prints a marker; the third says so in words.

## The shape of the change

- **`block_verdict(block)`** is the predicate `report_blocks` had inlined, and
  `report_blocks` now calls it. The two dump sections need the same answer, and
  a second copy of it is a thing that drifts. It stays the restore check alone
  — the section above it distinguishes the two refusals and still does.
- **`block_marker(block)`** turns one block's refusal into the words to carry,
  keyed on `block.problems` (previous section). `verdict_marker(here)` does the
  same for a value's blocks, and is empty when all of them were printed — there
  is nothing to mark, and the common path stays byte-identical to what it
  printed before.
- **Two blocks can share a value** (the same value written twice in a day, which
  `Block.index` exists to tell apart), so the marker names both rather than
  only the refused one: a read spanning a refused and a printed block is not a
  read of one block. No committed capture has this shape, so it is asserted on
  the builder rather than on a run.
- **`verdicts=` is keyword-defaulted** on both readers, so a caller that has no
  index degrades to today's output rather than to an exception. The tests that
  reach the readers directly keep working unchanged.
- **The marker rides on the existing two-space group line**, appended and never
  moved or re-indented, because the group line is the whole of the attribution
  — `dump-pair-block-attribution.md` found the bracket body itself cannot show
  which block it is about. Appending keeps
  `test_the_readback_is_taken_from_the_dumps_of_the_block_being_graded`'s exact
  string matching, and the bracket bodies stay byte-identical, so `group_body()`'s
  cut on `    {name}:` and the "no third category" invariant both stand.
- **The closing `graded_pairs` sentence stays.** The pair *was* compared, so
  `graded_pairs` does not drop and the sentence does not go; it gains a scoped
  companion when the run graded no window at all, on the same reasoning as the
  `moved_groups` companion above it.
- **Exit code is unchanged.** A void block already returned 1.

## What this does not establish

**No live run, and no claim about the machine.** Every input is a committed
hand-written fixture and the tool's own stdout over it. The reproduction is
offline: no file is written, no EC is read, and nothing outside
`ec/tools/testdata/` is touched. `0x0751` stays `present-untested` in
`ec/annotations/registers.yaml`, and no line of this is a §7 verdict — §7's
`confirmed-inert` still needs #380's run.

**A `VOID` marker is a statement about this run's windows, not about the
machine.** The wording is deliberately "its windows were withheld above" and
never anything that would let it read as "nothing happened in that block" —
that is the inverse of the calibration rule the repo states for static scans,
and a block withheld for want of a mark is a hole in the record, not a finding
about a register.

## The new fixture, and why it is a copy

`ec/tools/testdata/0751-isolation-run-void-block-with-dumps/` holds the three
CSVs copied from `0751-isolation-run-void-block/` and the two `a0` dumps copied
from `0751-isolation-run-multi-block/`, the dumps keeping their **original
basenames** so `DUMP_VALUE` still attributes them to block `0xA0`.

The copy is the repo's own precedent, not laziness: `3blocks-moved/` is
"3blocks/ with one row added" and `missing-mark/` is "byte for byte in the
0x0700 and 0x0400 captures". It buys two things — a failure names its case,
and a future edit to `multi-block/`'s `a0` dumps cannot silently move the void
case under it. The narrower reading (compose `VOID_BLOCK` + `MULTI_A0_DUMPS` in
the test, zero new bytes) was considered and **left out**: it makes the void
case a hostage to another fixture's edits. The trade-off is duplicated
constructed bytes, which this directory already accepts by design and its
README's "written by hand" rule already covers.

It is deliberately **not** in §6's fenced file list. `test_grade_0751_isolation`
holds that list and the `0751-isolation-run/` directory equal on both sides, and
§6's command line is unchanged — that is the point of the change. The tool
annotates its own output; the operator's command line and §6's file list are
untouched.

## Follow-ups, named rather than done

- **A pair for a refused block is still exit code 0, while the block itself is
  exit code 1.** That is the pre-existing shape and it is now visible rather
  than hidden, but making it fatal is a change to the exit-code contract — the
  same argument #475's disagreeing-pair follow-up makes — and not this issue's
  call.
- **`report_readback`'s `--dump-pair` hint is still not block-aware** (#494),
  so it can point a `--block 0x10` run at an `a0` file. Sibling defect, own
  issue; scoping it is a wording change inside a section two tests pin.
- **The closing `graded_pairs` sentence has three states** — read for a graded
  block, read for a refused one, not read at all — and the first and third are
  still one boolean. If the scoping clause grows a second branch, the count and
  the sentence should be one value rather than a flag beside a boolean.
- **The `void` marker, `VOID` and `NOT GRADED` are three spellings of two
  facts**, and the dump sections now carry a third place to keep them in step.
  `block_marker()` and `verdict_marker()` are the natural home and now own the
  dump sections' wording; what they do not own is the window section's
  `NOT GRADED` and the block section's `VOID`, which are three spellings of one
  decision made in three places.
- **Neither `missing-mark/` nor `disagreeing-marks/` carries a dump**, so the
  mark-set marker is pinned on the builder and by composing those captures with
  the copied `a0` dumps. A directory that put the dumps beside the marks would
  hold it more directly, at the cost of a fourth near-duplicate capture set for
  a case two of the existing ones already describe.
