# A `--block` run said "consistent with the static prediction" for the whole capture (issue #497)

The write-up for [issue
#497](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/497), which is the
`--block` half of what [issue
#477](0751-grader-partial-grade-claims.md) fixed for a *withheld* window: a run
that graded every window it was shown printed the tool's strongest sentence
about a capture it had read a block of. It is a prose and branch-structure
change: **no byte is read differently, no window is graded or withheld or
attributed differently, and the exit code is unchanged** — an intact selected
block still exits 0. Nothing here is a register behaviour and nothing here is
evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §5 is the static
prediction and §7 is the call the output feeds.

---

## The defect, on committed fixtures with nothing edited

`ec/tools/testdata/0751-isolation-run-3blocks/` is a three-value day — blocks
`0xA0`/`0x00`/`0x10`, 8 windows — and §6's own command line ends in
`--block <value> --wrote <value>`, so an operator following §6 takes one
attachment per value. Block 1 of that fixture is intact, so a `--block 0xA0`
run over it has `withheld == 0` and `graded == len(shown) == 3`:

    python3 ec/tools/grade_0751_isolation.py \
        ec/tools/testdata/0751-isolation-run-3blocks/*.csv --block 0xA0

printed, before this change:

```
=== block 1 of 3, its integrity check ===  (value under test 0xA0)
    the other 2 block(s) were not checked in this run; run it without --block to check them all
  block 1/3: intact -- last mark 'restored 0x0751=0x10' is the restore

=== what this does and does not settle ===
  None of the §4.1-§4.3 bytes moved in any window: consistent with the static prediction, for this capture's window only (§5: ...).
```

`this capture` is the three-CSV set. The run had read 3 of the day's 8
windows, and had said so three lines above the sentence, in the block section
this change does not touch. The same three CSVs unscoped withhold 2 of 8, exit
1, and — since #477 — decline the comparison. `--block 0x00` reports `VOID`,
exits 1 and prints no prediction sentence at all, so that half of the issue was
already correct.

**The same subject defect exists one branch up, in `moved_groups`, and it is
the stronger of the two.** That branch is tested *first*, and its scoping line
is guarded on `if withheld:`, which a clean block run has none of. Over
`ec/tools/testdata/0751-isolation-run-3blocks-moved/` — `3blocks/` with one
`0x0784` row added inside block 1's write window — `--block 0xA0` printed:

```
  At least one of the §4.1-§4.3 bytes moved after a mark: PL1/PL2/PL4 (§4.1).
  That contradicts the static prediction in ec/annotations/manual-fan-ctrl-0751.md §5 if it is the PLs, or §4.2 if it is the fan table -- capture it in full, it is the more interesting outcome.
```

with no scoping at all. "That contradicts the static prediction" over one
value's three windows is a *larger* claim than the clean sentence was, and it
is the branch that pre-empts everything below it. Fixing only the clean case
would have left the same overclaim standing, higher up and reached first, so
both are in this change. Both are `print` calls and a guard; the attribution
text is unchanged and now arrives with a scope in front of it.

## The one-block guard, which the issue's own wording would have got wrong

The issue proposes `withheld == 0 and selected is not None`. Taken literally
that **regresses a correct case.** `ec/tools/testdata/0751-isolation-run/` —
§6's own set, the one the runbook's command line names, and the one its
offline-runnable examples use — is a **one-block** capture. There,
`selected is not None` while `len(blocks) == 1`, the block *is* the whole
capture, and the windows it graded are the whole mark stream. The
whole-capture comparison is exactly the claim that run can support, and it
already exits 0 with the clean sentence. A guard of `selected is not None`
alone would make a one-block day decline a comparison it can legitimately make
— a new overclaim, printed in the shape of a fix.

So the guard is **`selected is not None and len(blocks) > 1`**, and the second
clause has its own test. It is not obvious enough to leave uncommented: the
integrity check on a one-block run names "the other **0** block(s) were not
checked", so a per-block sentence there would decline a comparison over an
empty set of skipped blocks. A comment beside the branch records this, because
the next reader will otherwise simplify the clause away.

## The change

Confined to the closing-summary block in `ec/tools/grade_0751_isolation.py`.
The chain is `if withheld:` (banner) → `if moved_groups:` → `elif graded == 0:`
→ `elif withheld:` → `else:`, and both additions are placed so that **no
existing branch changes which case it reaches**:

- A new `elif selected is not None and len(blocks) > 1:` between the partial
  branch and the final `else`. By construction it is reached only when
  `withheld == 0` (both withheld branches are above it) and `graded > 0`
  (`elif graded == 0:` is above it) — the issue's condition, with the one-block
  day excluded. The final `else` keeps its sentence **byte-for-byte**, which
  is what keeps `test_a_clean_multi_block_run_still_gets_the_prediction_sentence`
  green on untouched assertions.
- Inside the `moved_groups` branch, the scoping line guarded on `if withheld:`
  gains an `elif` sibling for the same guard, printed **before** the
  `That contradicts …` attribution — at the same place the withheld scoping
  line is printed, so the attribution reads as scoped in both cases. `elif`, not
  a second `if`: the two scope the same movement claim, and a run that both
  selected a block and withheld part of it is scoped by the more specific of
  the two, not twice.

The new clean sentence opens on the same words as every other one
(`None of the §4.1-§4.3 bytes moved`) and diverges after them, so a test
asserting the whole clean sentence cannot be satisfied by a per-block run, and
a reader who greps for the opening still finds it.

Every clause of both new sentences is a fact the run holds: the block's index,
the value under test, the count it graded, the number of blocks it did not.
Neither says what the ungraded blocks *would* have shown — that is the refusal
the withheld banner already models, and inventing it here would be a guess.
`docs/findings.md` §4 is the section recording what overclaiming cost this
repository; `CLAUDE.md`'s calibration rule is explicit that a claim must not be
stronger than the evidence, and this change is required not to introduce a new
unqualified claim while removing the old one.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, 57 tests before and 60 after, all
passing under `bash tools/run-tests.sh ec/tools`:

| test | case | what it holds |
|---|---|---|
| `test_a_clean_per_block_run_does_not_claim_the_whole_capture` | `3blocks/` `--block 0xA0` | rc 0; the block index, value and graded count in the sentence; the same decline the withheld branch makes; `'consistent with the static prediction'` **absent**; neither withheld shape reached; the other 2 blocks still named as unchecked |
| `test_a_per_block_movement_is_scoped_before_the_attribution` | `3blocks-moved/` `--block 0xA0` | rc 0; `PL1/PL2/PL4 (§4.1)` named as moved; the per-block scope printed **before** the attribution; the attribution itself still present |
| `test_a_block_run_over_a_one_block_capture_still_compares` | `0751-isolation-run/` `--block 0xA0` | rc 0; the clean whole-capture sentence and §5's caveat **present**; the per-block sentence absent |

The first two **fail against the unfixed tool** — that is the check that they
test the defect and not the fixture. The third is green before *and* after,
which is the point of it: it is a pin on the guard, not a regression test, and
it fails the day someone drops `and len(blocks) > 1`.

`test_a_clean_multi_block_run_still_gets_the_prediction_sentence` was left
**byte-for-byte unchanged**, not edited and not reformatted. It is the
evidence that a clean *whole-capture* run is still the case that makes the
comparison, which is the other half of what the issue asks for.

### The before/after diff of every previously-reachable fixture

Every fixture was run both ways and diffed. **Exit codes and stderr are
unchanged everywhere.** Fifteen of the twenty invocations have byte-for-byte
identical stdout, including all nine unscoped runs, `--block 0xA0` over §6's
one-block `0751-isolation-run/`, `--block 0xA0` over `void-block/`, and the
`example-active` and `example-mailbox-poke` captures. The five that change are
all multi-capture `--block` runs, and each change is the new scoping:

| invocation | line that moves |
|---|---|
| `3blocks/` `--block 0xA0` | the clean sentence, replaced by the per-block one |
| `3blocks-moved/` `--block 0xA0` | one line **added** between the movement and the attribution |
| `multi-block/` `--block 0xA0` | the clean sentence, replaced (a second 2-block shape) |
| `unplaced-window/` `--block 0xA0` | the clean sentence, replaced |
| `unread-window/` `--block 0xA0` | the clean sentence, replaced |

The last one is worth a note, because it is the case #477 argued about. On
`unread-window/` the withheld window is a stray in **no block at all**, so
`--block 0xA0` cannot show it and `withheld == 0` on that run: the new branch
is reached, and correctly so. The run read three whole windows of block 1 and
nothing else, which is exactly what the sentence says. That the unscoped run
over the same CSVs still withholds 1 of 8 and still declines the comparison is
unchanged — it is the unscoped run that still exits 1.

## Left out on purpose

- **How `--block` filters, numbers or selects.** Not in question and not
  touched; the run read exactly what it said it read before this change and
  does after it.
- **A new fixture, and `ec/tools/testdata/README.md`.** The issue anticipated
  one. There is no need: `3blocks/` reaches the clean case, `3blocks-moved/`
  the moved one, `multi-block/` a second multi-block shape, `unplaced-window/`
  and `unread-window/` two more, and `0751-isolation-run/` the one-block guard.
  Five committed fixtures already reach every case, so the README is unchanged
  and one shared file is not edited.
- **`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`.** §6 does not
  quote the closing-summary text verbatim and its command line is unchanged —
  `--block <value>` is what §6 already told a human to type. §7's
  `confirmed-inert` wording was already correct: it keys the call on "nothing
  moves across all three values, both with and without the service", and says
  to say it in those words. Nothing there needed changing; the sentence above
  it in the tool's own output is what failed to match it.
- **`ec/README.md`.** Its `grade_0751_isolation.py` bullet describes what the
  tool is and where its suite is, not how its closing summary branches.

## Nothing here was run against hardware

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the commands above and the tests named. No fixture
was added by this change, and every fixture named here is a constructed input
described as one in its own header and in `ec/tools/testdata/README.md`. **No
line of this change may be read as a report of a capture or a live
observation, and none is one.** §6's day has still not been run on the machine;
`MANUAL_FAN_CTRL` stays `present-untested` and
`ec/annotations/registers.yaml` does not move — no register status is in
question here, only what a report may say about the windows it read. That run
is issue #380's and stays a human's step at the machine.
