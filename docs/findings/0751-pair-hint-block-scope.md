# §4.6's `--dump-pair` hint named another block's bracket, and pointed at a file the same run refuses to read (issue #1394)

The write-up for [issue
#1394](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1394). §22 of
`docs/findings.md` recorded this as a follow-up named rather than done, and the
sentence there stands; this is where it lands.

**Offline throughout, and nothing here is a claim about the machine.** No EC was
read, no §3 run was performed, no laptop or Windows box was reached, and no
register was observed. `0x0751` stays `present-untested` in
`ec/annotations/registers.yaml` and this changes no status. Every input below is
a committed fixture under `ec/tools/testdata/`, which is **hand-written input,
not a capture** — each file carries a `# CONSTRUCTED INPUT, NOT A CAPTURE`
header and `ec/tools/testdata/README.md` is where that rule is written down.
Every sentence is about which files were handed in and what the report said
about them.

---

## The defect, over committed fixtures

`report_readback` prints a coverage notice when the block's last `--dump` does
not reach `0x0751`, and then walks `pairs` for the first one whose two files
both hold the byte. The walk asked one question — coverage — and the answer was
acted on as if it settled the matter. It does not: the pair it names is a
`--dump` the operator is told to pass, and §4.6 grades only the block's own
dumps.

Reproduced on the tree as committed, exit code 0 in both runs. `0751-isolation-run-3blocks/`
carries only the three CSVs, so the `0x10` block's own `--dump` is written into a
temporary directory under §6's `<value>` name shape — the substitution
`test_a_pair_whose_before_alone_covers_0751_is_not_named` already uses, and for
the same reason: `test_section6s_file_list_is_the_fixture_set` holds
`0751-isolation-run/` *equal* to §6's file list, so a dump added there fails it.

```console
$ D3=ec/tools/testdata/0751-isolation-run-3blocks
$ DA=ec/tools/testdata/0751-isolation-run
$ T=$(mktemp -d); printf '0f00: 00 01 02 03\n' > $T/x-0751-isolation-10-before-0f00.txt
$ python3 ec/tools/grade_0751_isolation.py \
    $D3/2026-01-01-0751-isolation-0700-07ff.csv --block 0x10 --wrote 0x10 \
    --dump $T/x-0751-isolation-10-before-0f00.txt \
    --dump-pair $DA/2026-01-01-0751-isolation-a0-before-0700.txt \
                $DA/2026-01-01-0751-isolation-a0-after-0700.txt
```

```
=== 0x0751 across the dumps (§4.6) ===
  block 0x10, from the <value> in these files' §6 names
  /tmp/.../x-0751-isolation-10-before-0f00.txt: 0x0751 not covered by this dump
  the last --dump does not cover 0x0751, so the §4.6 readback was not taken -- nothing here says what the byte held after the write
    a --dump-pair does cover it: .../0751-isolation-a0-before-0700.txt -> .../0751-isolation-a0-after-0700.txt; both files reach 0x0751
      pass the after file as the last --dump to take the readback: .../0751-isolation-a0-after-0700.txt
```

Doing what that says — passing the `a0` after-file as the last `--dump` — is
then refused by the same run, three lines down:

```
=== 0x0751 across the dumps (§4.6) ===
  block 0xA0, from the <value> in these files' §6 names
    .../0751-isolation-a0-after-0700.txt: belongs to block 0xA0, not the block under test (0x10) -- not read for §4.6 here
  no dump was given for block 0x10, so §4.6's readback for it was not taken; the dumps named above are another block's
```

The section names the evidence and then declines to read it. An operator
following §4.6 gets a refusal instead of the answer §4.6 exists to give, and
§4.6 is the question the run is for.

## The rule was already written down; the tool was the clause that missed it

`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` states the rule twice.
§6's note says `--dump-pair` "does not feed §4.6, and the readback still comes
from the last --dump of the block being graded", and the prose below it says the
grader "takes §4.6's readback from the last dump *of the block being graded*".
The next paragraph extends the same rule to the whole-block section and quotes
the refusal line above verbatim, including that a pair is filed by the `<value>`
in its two file names.

`report_dump_pairs` already implemented that half. `dump_pair_block` is its
filing function, `report_dump_pairs` groups on what it returns, and the line in
the second transcript is its own refusal. The hint was the one caller that took
`pairs` and discarded the filing — the whole defect, and the smallest one in
this repository's history: a documentation clause catching up with itself.

## What was not free about it, and where the scoping was free

`report_readback`'s docstring said a `--dump-pair` "can be named in its place
because a file can stand in for a missing file", with no statement about *which*
pair. That sentence is the gap.

The rest of §4.6 does inherit `--block` scoping for free.
[`0751-readback-written-value-notice.md`](0751-readback-written-value-notice.md)
says so in its "Placement, and why it is in `report_readback`" section, and the
argument is sound for what that write-up is about: `report_dumps` has already
skipped the other blocks' groups before calling in, so the group line and every
per-dump row are reached only for the block being graded. The pairs are the
exception and always were — they arrive as one list the caller hands in whole,
and each has to be filed before it can be weighed against this block. So this
is a narrowing of that sentence's reach rather than a retraction of it, and the
older write-up is left as it stands; the two are about different lines.

## The change

`report_readback` now files each pair with `dump_pair_block(before_path,
after_path, pair_fallback)` and keeps only a pair whose filed value equals the
block the section is grading. Two details are load-bearing:

- **The fallback is threaded in, not re-derived.** `report_dumps` already
  computes `block_value if block_value is not None else wrote` and uses it to
  group the dumps; the same value is passed down as a keyword argument with a
  `None` default. A second derivation here could disagree with it, and the
  hint's claim is about the file the operator is being told to pass — so the
  hint and the `--dump` it recommends must agree on which block a file carrying
  no name belongs to.
- **`value is None` is not filtered at all.** A group with no §6 `<value>` and
  neither `--wrote` nor `--block` has no block under test, so there is nothing
  to scope the hint to. This is the calibrated reading — "no block is named
  here", not "the pair is another block's" — and it is what keeps the whole-block
  section's own unattributed group consistent with this one.

`dump_pair_block` already resolves a `disagree` pair to no value, so a pair whose
two names name different blocks is not named for free.

The block check runs **after** `pair_refusal`, not before it, and the order is
the point. A pair given one file twice is not a readback of anything whatever
block it belongs to, and that is an independent fact from which block filed it;
filing the pair first would answer "is this block's" with "no" and drop the
refusal on the floor. A section that then said only that the pair is another
block's leaves the operator to re-run and meet the same refusal, rather than
telling them the flag is wrong. `report_dump_pairs` checks the block first
because its refusal question is downstream of the grouping; here the refusal is
what the operator needs, so it decides first and the block decides after.

Where no pair of the block's covers the address and at least one pair of
another block's does, the pairs passed over are named with the block each belongs
to and the basis it was filed under. The line prints **only when a pair was
actually passed over**, so a run with no `--dump-pair` gets no new line. Its
wording is `pair_block_basis`, which says the five answers `dump_pair_block` can
give the way `report_dump_pairs` says them on its group lines: a pair has two
readers, and a second phrasing of the same five answers is how those two come to
disagree about which block a bracket is filed under.

What the line is about is the covering pairs that **can be read**, and it says
so. Two kinds of pair are on the command line and outside that set: one that
does not reach the address, which was never a candidate, and one `pair_refusal`
turned away, which is named with its reason two lines above. Counting past both
produces a line that denies a pair the same section has just named — the
mistyped `--dump-pair` shape §6's three-pairs-per-value command block makes easy
to write, reproduced under "After" above.

Two lines for a pair that **is** named are byte-identical to what they were, and
a refused pair keeps its refusal whatever block it is. §6's own advice does not
churn, and the runbook's command block still reads the same way.

## After, over the same fixtures

Same command, same exit code:

```
=== 0x0751 across the dumps (§4.6) ===
  block 0x10, from the <value> in these files' §6 names
  /tmp/.../x-0751-isolation-10-before-0f00.txt: 0x0751 not covered by this dump
  the last --dump does not cover 0x0751, so the §4.6 readback was not taken -- nothing here says what the byte held after the write
    no --dump-pair of block 0x10's reaches 0x0751 and is one to read; none of the 1 --dump-pair(s) given that cover it and can be read is this block's -- block 0xA0, from the <value> in these files' §6 names
```

"No pair of this block's reaches `0x0751` and is one to read" is a statement
about the pairs on this command line and not a general one — which is why the
line names the block the operator did give rather than stopping at the absence.
Both halves are scoped to *covering pairs that can be read*, and the wording
says so, because the pairs the line does not speak about are still on the
command line. The two that are not covered are named with a reason above the
line rather than counted into it, so the count here is of what the sentence can
answer for.

That scoping is not a refinement. A first version read `none of the N
--dump-pair(s) given is this block's`, counting the pairs passed over and
calling the count everything the operator handed in — and §6's own command block
hands in three pairs per value, so a mistyped `0x10` pair beside a good `0xA0`
one is a command line an operator writes rather than a shape the fixtures have
to be bent into. On that run the section named the `0x10` pair two lines above
as reaching `0x0751`, and then said none of the pairs given was this block's:

```
    a --dump-pair reaches 0x0751 and is not one to read from: .../0751-isolation-10-before-0700.txt -> .../0751-isolation-10-before-0700.txt
      both sides are the same file, so this pair is not graded: ...
    no --dump-pair of block 0x10's reaches 0x0751; none of the 1 --dump-pair(s) given is this block's -- block 0xA0, from the <value> in these files' §6 names
```

The operator is told their `0x10` pair does not exist, in the same block of
output that has just named it, and the count is one lower than the pairs on the
line. A refused pair is in neither set the sentence is about — it is not
something passed over, and it is not readable — so the honest form names what it
counts instead of counting past it.

And a `--block 0x10` run handed the `0x10` pair still gets the hint, byte for
byte, which is the direction that has to be unchanged for §6's advice to survive:

```
    a --dump-pair does cover it: .../0751-isolation-10-before-0700.txt -> .../0751-isolation-10-after-0700.txt; both files reach 0x0751
      pass the after file as the last --dump to take the readback: .../0751-isolation-10-after-0700.txt
```

## What this does not do

- **A group with no block named is not filtered.** A pair that names some block
  is still named there. Filtering on that group would read the pair's value as a
  mismatch against nothing, and would turn the hint off for every run that has
  no block to grade against.
- **§22's second follow-up is untouched.** §22 names it as "a name disagreement
  stays exit code 0", which is this tool's `disagree`: whether a pair whose two
  file names name different blocks should exit non-zero rather than 0. A
  separate question, and a design call about the tool's exit-code contract —
  `--block`/`--wrote` name the value under test for the whole run, and §22's
  own argument is that one of them being wrong leaves no window in the report
  gradeable, which is not true of one pair out of three. Left exactly as it is.
- **The runbook is not edited.** §6 of
  `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` states the rule twice
  — the command block's `rem` note and the prose below it — and this makes the
  tool match it; a new sentence would add nothing to a shared procedure doc
  another branch may be in.
- **No new fixture, and nothing added to `0751-isolation-run/`.** §6's file list
  is held equal to that set, so a dump added there fails
  `test_section6s_file_list_is_the_fixture_set`.

## The tests

The cases live in `PairHintBlockScopeTests` in
`ec/tools/test_grade_0751_isolation.py`, at the end of the file. The neighbour
they sit beside is `test_readback_not_taken_when_nothing_here_covers_0751` in
`GradeTests`, which holds the coverage half of the same comparison — and they
are not beside it for a reason worth stating rather than leaving for the next
reader to infer: line numbers in the findings write-ups, and the per-pin table
in `docs/findings/test-line-pin-census.md` on top of them, cite into this file
below `GradeTests`, and inserting there would move all of them onto the wrong
line without changing a word of the sentences citing them.
[`0751-readback-written-value-notice.md`](0751-readback-written-value-notice.md)
gave the same reason for `ReadbackNoticeTests`.

`test_a_block_run_is_not_handed_another_blocks_pair` is the gate: it asserts
both halves of the old hint absent, the new line present, and no verdict. It
fails on the unfixed tool, which is the check that it is a gate and not a
description. `test_a_pair_of_the_block_under_test_is_still_named` is the other
direction and pins the two named lines byte for byte.
`test_following_the_old_hint_is_still_refused_by_the_same_run` pins the
end-to-end shape — a hint can no longer point at a file the same run declines to
read. `test_pairs_of_two_blocks_are_each_named_with_their_own` covers the line's
plural form and the case where one block's pair is named while another's is not,
so the two cannot both fire on one run.
`test_a_pair_of_another_block_that_is_not_a_bracket_still_says_so` pins the
filter order above, and does so because the other order is the one that reads
more naturally: filing the block first is what `report_dump_pairs` does, and
copying it here loses the refusal line — which the sweep below caught.
`test_a_refused_pair_of_this_block_does_not_make_the_line_deny_it` covers the
scoping, and it needs its own case because the refusal case above cannot see it:
that one hands in a refused pair and nothing else, so the line never fires there
and its count is never exercised with a second pair present. Add one and the two
interact, which is where the unscoped wording denied the operator's own pair.
`test_no_pair_at_all_gains_no_line` and
`test_a_group_with_no_block_named_still_names_a_pair` pin the two ways the new
line stays silent, so a future change cannot leave it printing over a run with
nothing to account for.

## The sweep that found the scoping, and the case the suite could not have asked for

The suite pins the shapes the issue names and the ones I thought to write down.
It cannot say the change did something to a run nobody thought of, so the §4.6
line was swept over every two-`--dump-pair` command line the committed fixtures
build: each pair drawn from the covering files of `0751-isolation-run/` and
`0751-isolation-run-multi-block/`, both pair orders, the same temp-file
substitution the transcripts above use.

The sweep re-derives what the line ought to say from the command line rather
than reading the output back — `dump_pair_block`'s own predicate for the
filing, `pair_refusal`'s for readability — and compares. It is the check that
found the defect described under "After", and it is sensitive in both
directions: it reports every unscoped line as a denial, and every scoped line as
clean, so a version that fixed the wording and reintroduced the count would not
pass it either.

That sweep is the argument for the new test's own existence. The existing
refusal case hands in a refused pair and nothing else, so the line never fires
there; the count in it is only ever exercised once a second pair is on the line,
and no case did that. `test_a_refused_pair_of_this_block_does_not_make_the_line_deny_it`
is that case, and it fails against the unscoped wording.

An earlier version also filed the block before the refusal, following
`report_dump_pairs`, and that order loses the refusal line: a run handed a
mistyped pair of another block was told only which block the pair belonged to,
leaving the operator to re-run and meet the same refusal rather than being told
the flag is wrong. A real loss, and not one the issue asked for, so the order is
the one above and a test holds it.

`census_test_line_pins.py` reports the same headline before and after, which is
the mechanical check that no cited line moved and that this write-up added no
pin: it is written with the census's own rules — tool lines as
`ec/tools/grade_0751_isolation.py:NNNN`, tests by name, never as
`test_grade_0751_isolation.py:NNN`.

## A residual worth naming

A nameless pair on an **unscoped** run whose dumps' names and `--wrote` disagree
is filed by `dump_pair_block` under `--wrote`, and the hint will pass over it if
that is not the block the section is grading. This is a real narrowing and it is
deliberate: the fallback is `report_dumps`'s own, and the hint and the `--dump`
it recommends have to agree. What it costs is that an operator who names no block
in a pair's file names gets a narrower hint than one who does, and the section
does not distinguish "filed from a name that says 0x30" from "filed from
`--wrote 0x30`" at this level — it says which, but only in the group line above
for dumps. Worth an issue of its own; naming it here is what the follow-up pass
turns into one.
