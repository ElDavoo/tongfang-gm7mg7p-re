# A whole-block bracket is not a second reading of the same bytes (issue #475)

The write-up for [issue #475](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/475),
which asked `grade_0751_isolation.py` to group `--dump-pair` by block the way it
already grouped `--dump`. It is a reporting and attribution change: **no
fixture was added, no capture was re-read, and nothing here is a statement
about `0x0751` or the EC.**

`docs/findings.md` §22 has the summary. This file has the reasoning, and the one
property that made the grouping the only fix available.

---

## The problem, stated precisely

§6 of `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` stamps every dump
with the `<value>` of the block it belongs to, and `dump_block()` reads it back
out of the file name. `report_dumps()` groups its `--dump` files on that value,
prints `block 0xA0, from the <value> in these files' §6 names`, and on a
`--block 0x10` run handed the `a0` dumps prints

```
belongs to block 0xA0, not the block under test (0x10) -- not read for §4.6 here
```

and takes no readback from them. That half was already right — it came in with
#457, which added the grouping to `--dump` and the test
`test_the_readback_is_taken_from_the_dumps_of_the_block_being_graded` with it —
and this issue is that fix, one section over.

`report_dump_pairs()` took the `--dump-pair` files with no block argument at
all. Every pair was read and compared, under one
`=== whole-block dump pairs (§4.1-§4.3) ===` heading, with no group line and no
`block:` header of any kind. So in the whole-day form §6 documents — one plain
invocation over all three values' files — every window above the section carried
a `block:` line and the three brackets below it carried nothing.

## Why a mis-filed bracket is a result, not a redundancy

The obvious objection is that the whole-block read is a *second* reading of the
same question the windows answer, so reading a pair twice is harmless. It is
not, for two reasons.

**It is wider than the window.** A bracket covers the whole block from step 0 to
step 6; a window covers one arm of it. They are complementary readings, each
with a gap the other does not close, and the bracket answers for bytes no window
in the report was about. Filed under the wrong block, it is an answer about
bytes the run's heading never claimed to be reading.

**And nothing inside the bracket shows it is mis-filed.** This is the part
worth stating, because it is what makes the fix a grouping rather than a
stronger report. The two dump pairs in
`ec/tools/testdata/0751-isolation-run-multi-block/` read the same two bytes in
the opposite order — `a0-before`/`a0-after` read `0x0751 0x10 -> 0xA0`, and
`10-before`/`10-after` read the same page as `0xA0 -> 0x10`. Run through the
committed tool, the two print **byte-identical brackets** apart from the two
file names and the value in the group line above them — the `<value>` in each
name elided here, and the `10` pair's group reads `block 0x10` where this one
reads `block 0xA0`, with every line under it identical:

```
  block 0xA0, from the <value> in these files' §6 names

  <value>-before-0700.txt -> <value>-after-0700.txt, 16 address(es) compared
    PL1/PL2/PL4 (§4.1): not covered by this pair
    fan table (§4.2): not covered by this pair
    fan-table reload trigger 0x0F5D-0x0F5F (host-written; see below): not covered by this pair
    fan-table bracket byte 0x07C6 (§4.3): not covered by this pair
    fan duty / temperature bytes (§4.4/§4.5) -- context, not graded here:
      CPU_TEMP 0x043E / GPU_TEMP 0x044F -- confirmed (§4.5): not covered by this pair
    other addresses that differ (1), not graded here -- read them against §4.4 and §4.5 by hand:
      0x0751
```

The "other addresses that differ" bucket names `0x0751` **as an address only**.
The values — `0xA0` and `0x10`, the one fact that distinguishes the two files —
are in the §4.6 readback, which is a different section answering a different
question. So the bracket a reader would be checking is indistinguishable in its
body from the right one, and the calibrated claim is not "a mis-filed bracket
becomes visible in its output" but: **the group line above it and the refusal
to compare are the entire attribution, and without them there is none.** The
test `test_both_blocks_pairs_are_grouped_in_one_unscoped_run` pins that
identity, so the property cannot be quietly lost later, and the scoped case
asserts on the label and on what is *absent* rather than on a value — there is
no value-level difference to find.

The alternative fix — printing the differing addresses' values in the bracket —
was not taken. It changes a line `differing_addresses()` reads flat and an
existing test pins, and it cuts against the "no third category" invariant in
`report_dump_pairs`' own docstring. The label plus the refusal is sufficient,
and that is the property worth having.

## What a pair's block is

`dump_pair_block(before, after, fallback)` answers the question once per pair,
in the same `(value, how)` shape `dump_block()` returns, and it **asks
`dump_block()` rather than re-implementing it** — so the two sections cannot
drift on what a name beats:

| the two file names | `(value, how)` |
| --- | --- |
| both name the same block | that block, `name` |
| one names a block, the other carries none | the named one, `one-name` |
| both name, and they disagree | `None`, `disagree` |
| neither names one | `--block` else `--wrote` as `flag`, else `None` as `none` |

Two decisions in that table are worth their reasons.

**One name and a silent other side is that block's.** The name is the more
specific of the two statements, which is the reading `report_readback`'s
docstring already gives for a file name against `--wrote`. The report says
which of the two it used, because "these files' §6 names" would be false for the
half that carries none.

**The fallback is only consulted when neither name speaks.** A pair that names
its own block is never quietly re-filed under the run's `--block` — otherwise
the flag would overwrite the more specific statement. §6 stamps both files, so
the fallback only ever serves a hand-written command line; the tests cover it
from both sides, under `--block 0xA0` and under `--block 0x10`.

**Two names that disagree is an input error, named and not compared, and it is
not fatal.** Not resolving it by picking one is the point: a pair is one block's
before and after, so a `0xA0` before-dump and a `0x10` after-dump bracket two
different blocks, and either pick files a bracket over the wrong bytes with a
clean face. Non-fatal matches the one `--dump-pair` error the flag could
already see on its own — the same file twice — where the window report and the
§4.6 readback the operator also needs still get printed. Making it fatal like
`--block`/`--wrote` is a real design call and was not taken here: those two name
the value under test for the *whole run*, so one of them being wrong means no
window in the report is gradeable, which is not true of one pair out of three.
That asymmetry is the reason the two are treated differently, and it is the
follow-up below rather than a decision smuggled in.

## The shape of the change

`report_dump_pairs(pairs, block_value=None, wrote=None)` grew the grouping
`report_dumps()` has: first-seen order, a group line per group, then per pair
either the mis-attribution notice and a skip, or the existing bracket unchanged.
Three things deliberately did not move:

- **The heading string is byte-identical** —
  `=== whole-block dump pairs (§4.1-§4.3) ===` — because both §4.6 readers in
  the test suite cut the section on it, and `whole_block()` is one spelling of
  that split for the tests. The same reasoning `report_dumps`' docstring gives.
- **Every line inside a pair body keeps its indentation**, so `group_body()`
  still cuts on `    {name}:` and the six-space value lines still belong to it.
- **The closing paragraph is still printed once, after the last group**, so
  `dumps_section()` and `whole_block()` keep working unchanged.

`graded` now counts only pairs actually compared in scope, so the closing
summary cannot report a whole-block read for a `--block` run that took none: a
scoped run handed only another block's pairs is 0, and the summary line is
absent. The group key is `(value, how)` rather than the value alone, because a
`name` group line would otherwise be printed over a `flag` or `disagree` member
and claim a file says something it does not.

## What this does not establish

**No live run, and no claim about the machine.** Every input is a committed
hand-written fixture and the tool's own output over it. No EC was read, no
register was read back, and `0x0751` stays `present-untested` in
`ec/annotations/registers.yaml` — this is a report-attribution fix and nothing
in it is evidence about a register. Nothing here is in §7's status vocabulary.

**The `a0`/`10` bracket identity is a property of these two fixtures**, not a
general statement that whole-block reads never differ between blocks. It is
recorded because it is what makes the grouping load-bearing on the fixture the
issue names, and it is pinned by a test so it stays true of them.

## Follow-ups

- **`report_readback`'s `--dump-pair` hint is still not block-aware.** When the
  block's own last `--dump` does not reach `0x0751`, the §4.6 section names "a
  `--dump-pair` that does cover it" without checking that pair's block, so a
  `--block 0x10` run can be pointed at an `a0` file. Same class, smaller: it is
  advice rather than a verdict, and it fires only when the block's own last
  `--dump` is short. Scoping it is a wording decision about a hint inside the
  §4.6 section two tests pin, so it is named here rather than done.
- **A name disagreement is still exit code 0.** The argument above is the one
  that made it non-fatal, and it holds for one pair out of three and not for a
  `--block`/`--wrote` pair. Whether the two should answer differently is a
  change to the tool's exit-code contract, not a report fix, and is out of scope
  for the issue that asked for the grouping.
