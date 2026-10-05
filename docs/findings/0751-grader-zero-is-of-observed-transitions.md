# A grader zero said "the byte held still" about a capture that only records transitions (issue #384)

The write-up for [issue
#384](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/384), about
`ec/tools/grade_0751_isolation.py` calling a `(0 changes)` line "a byte that
held still", which is a claim about movement that an `ec_watch.py` CSV cannot
support. It is a **wording fix: no byte is read differently, no window is
graded or withheld differently, no figure moves, and no exit code changes on
any committed fixture.** Nothing here is a register behaviour and nothing here
is evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value, and §7 is where the call is made.

---

## The gap

`ec_watch.py` writes a change row when a byte *differs* between two of its
sweeps. A capture is therefore a log of recorded transitions, not a sampling
of levels, and the two are not the same kind of fact:

- a byte with no row in a window is a byte no sweep saw differ;
- a byte with no row that moved and came back inside one sampling period is a
  byte that moved, and the capture says nothing either way.

§3 already puts the period on the page and stops where this gap starts.
`--interval` is slept *between sweeps* and not between bytes, one sweep of the
three watchers is `0x100 + 0x60 + 0x60 = 448` `ECRR` reads, and under its own
bolded heading — **there is no safe interval to hand you from here** — how
long one IOCTL takes is not something this repo measures. #94 has since closed
its own half of that: `ec_watch.py` now skips the fan-tach page and sleeps
`--gap-ms` after every read, which is a conservative default borrowed from a
sibling board and not a measurement either, and `manual_fan_ctrl_probe.py` --
which §3 runs the three watchers beside -- is still unpaced. So the per-byte
sampling period is
`--interval` plus a sweep duration that is unmeasured, and the change states
that rather than inventing a threshold.

**The tool already knew this, and printed it on one branch only.** The
`--dump-pair` paragraph in the module docstring, `report_dump_pairs`'s own
docstring and its closing printed paragraph all say a byte that moves entirely
between two of `ec_watch.py`'s sweeps "is in no change row at all". That is a
different section, reached only when `--dump-pair` is given: **a run with no
dump pairs never prints it.** §6's own `--dump-pair` introduction says the same
and identifies the gap as "what the windows cannot show" — and then §4.4, three
hundred lines earlier, calls the zero "a byte that was watched and stayed
put".

Three sentences carried the claim, and none of them was the arithmetic:

| home | what it said |
|---|---|
| the module docstring | absence "would read as missing data rather than as **the strongest negative result the procedure can produce**" |
| `report_window`'s printed preamble | "so **a byte that held still is a zero here** and not a missing line" |
| §4.4 | "a byte that was watched and **stayed put** is not read as a byte nobody watched" |

Each is right about rows and wrong about movement. §6 restated §4.4's sentence
("a byte that held still reads as a zero rather than as a missing line") and
§7's `confirmed-inert` bullet cashed it in ("nothing moves across all three
values … and the surrounding bytes stay put"). **One claim, four homes**, which
is why a new file would not have held it: a pointer to a write-up cannot retract
a sentence that is still standing next to the figures a reader is looking at.

## The wording, and one constant for it

`ZERO_SCOPE_NOTE` is the sentence, and it is printed in both tool homes from
that one definition — the claim is made in two places and cashed in at a third,
and three spellings of it is three chances to fix the grammar and leave the
gap. Its content, in order: a zero here counts the change rows recorded between
these samples and is not a measurement of the byte; `ec_watch.py` writes a row
only when a byte differs between two of its sweeps; `--interval` is slept
between sweeps rather than between bytes; the per-byte period is `--interval`
plus a sweep duration nothing in this repo measures (issue #94), so a move that
completes inside one sampling period is in no change row at all; and the wider
`--dump-pair` bracket closes part of that gap and is complementary rather than
stronger.

The closing block prints it **unconditionally**, on every run whatever it
found. A caveat printed only on the branch that produced a zero reads as part
of that branch's answer rather than as a fact about every zero in the report,
and §7's call is made on a run that moved nothing.

**The parenthetical token is left alone**, deliberately. `(0 changes)` counts
what the report counted, which is true, and the scoped sentence says what it
does not cover. Changing the token would move two committed assertions for no
gain, so the sentences around them moved instead.

## What this does not touch, and why

- **`docs/findings.md`** — frozen at §97; `check_findings_frozen.py` fails any
  edit. This file and nothing else.
- **The runbook is the deliberate exception** to "new work goes in new files".
  §4.4, §6 and §7 are *where the wrong sentence is*, and the same rule's own
  reason — keep edits to shared files small — is answered by the smallest edit
  that retracts a sentence in place. Prose only: no fenced block, no command
  line and no file list is touched, so §6's first fence (asserted by two tests)
  and the rest of the file stay byte-identical.
- **`ec/README.md`** — its `grade_0751_isolation.py` entry describes `--block`
  scoping, the dump groups and the self-test entry point. It says nothing about
  the zero lines, so nothing there goes stale, and leaving it alone is one
  fewer shared file open against the other agent PRs.
- **`ec/annotations/registers.yaml`** — **this is not a register-status
  change.** `MANUAL_FAN_CTRL` stays `present-untested`; there is no row to edit
  and none was missed. §7's call needs a *behavioural* observation per
  `../../CLAUDE.md`, and a reworded sentence is not one.
- **`ec/tools/testdata/`** — no new fixture. Every case is a wording assertion
  over a committed fixture, so `check_testdata_index.py` wants no row.

## The measurement over the whole fixture set

Byte-identity is **not** the goal here — this change adds printed text on
purpose. The goal is that the diff over every committed fixture is confined to
the intended classes and nothing else. The merge-base tool and this branch's
tool, over each `ec/tools/testdata/0751-isolation-run*/` directory four ways
where three values are present (unscoped and `--block` at each), recording exit
codes:

```
git show $(git merge-base HEAD origin/main):ec/tools/grade_0751_isolation.py > /tmp/base_tool.py
for d in ec/tools/testdata/0751-isolation-run*/; do
  csvs=$(ls "$d"/*.csv)
  for w in unscoped $(grep -ho '0x0751=0x[0-9A-F][0-9A-F]' $csvs | sort -u | sed 's/.*=//'); do
    [ "$w" = unscoped ] && a=() || a=(--block "$w")
    python3 /tmp/base_tool.py $csvs "${a[@]}" > /tmp/z.base 2>&1; echo "$d $w base=$?"
    python3 ec/tools/grade_0751_isolation.py $csvs "${a[@]}" > /tmp/z.new 2>&1; echo "$d $w new=$?"
    diff /tmp/z.base /tmp/z.new
  done
done
```

Measured over the **46 pairs** that recipe produces:

- **every exit code agrees**, on all 46;
- every changed line falls into one of three classes — the reworded preamble
  sentence in `report_window`, the note added under it, and the note added to
  the closing block;
- **no numeric figure, no count, no exit code, no group name and no verdict
  sentence** moved on any run;
- every `window delta` line is **byte-identical in all 46 pairs**, which is the
  arithmetic half of the claim stated as a check rather than as an assertion.

Any pair differing in anything else would be a hunk reaching further than
intended, and the change would be wrong until it was not.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, four tests beside the two zero-line
cases issue #384 names. Each is written so that dropping the sentence turns it
red, which was checked by deleting the `print` and by deleting the §6
restatement rather than by reading the assertion:

| test | what it holds |
|---|---|
| `test_a_zero_line_says_what_the_zero_is_a_zero_of` | the caveat is in the preamble of **every** window, not one; and `a byte that held still is a zero here`, `a byte that held still reads as a zero` and `the strongest negative result the procedure can produce` are all absent |
| `test_the_zero_scope_note_moved_no_figure` | the control: both parentheticals and all three figures still print verbatim, and the `window delta` count is unchanged — the wording moved, the arithmetic did not |
| `test_the_closing_block_carries_the_zero_scope_on_both_branches` | the closing block carries it on a run that moved **and** on one that did not, beside the `confirmed-inert` sentence it belongs with, so it cannot end up only on the branch that produced a zero |
| `test_the_runbook_says_what_the_zero_is_a_zero_of` | §4.4, §6 and §7 each carry the sentence, the retired phrasings are gone from all three, and §7's `confirmed-inert` bullet is cut by the bullet and read rather than searched for across the section |

**"Hold it across the tool and the doc" is the fourth one.** Without it,
holding the sentence in three places is a review note rather than a red test,
and the next reword that reaches two of them is green.

**The two named cases pass unedited.** The issue says they "pin the figures,
not the sentence around them". **Measured: they pin more than that.**
`test_a_byte_that_held_still_is_a_zero_and_not_a_missing_line` asserts the
literal `'(0 changes, level not in these captures)'` and
`test_a_byte_that_held_still_carries_its_level_forward` asserts the literal
`'(0 changes)'` and `'max 0  (0 changes)'`, so changing the parenthetical token
would break both. That is the measurement behind leaving the token alone above,
and it is why the sentences around them moved instead. Both run unmodified.

The new tests assert claims, not censuses: none counts fixtures, none counts
the tree, and none would need editing when the next suite is added.

### Committed line pins

Growing this suite pushed down 38 committed `file:NNN` pins into
`ec/tools/test_grade_0751_isolation.py`, and **the tool's own three edits
pushed down a second registry**: `measure_mark_provenance.py`'s `CITATIONS`
table, which pins 19 lines of that file and is checked by
`test_measure_mark_provenance_citations.py` in both directions — a citation
naming a line that no longer carries its quoted text, and a scanned
`"MARK"` site no citation names. Both registries were re-anchored and each
census row carries the reason in the form the table already uses. The
re-anchored rows were read against the tree rather than moved by arithmetic,
except `0751-capture-row-shape.md`'s commit-qualified pin, which names a line
in the revision it qualifies and is left there; the two quoted `grep`
transcripts in `0751-path-taking-reader-fates.md` are a third place line
numbers live in these write-ups, and nothing in the tree checks them.

Two things that a uniform shift gets wrong, and this change hit both:

- **Pins above the insertion points did not move.** `0751-grader-self-test-gate.md`'s
  `:16-20` sits above the first of the two additions and is unchanged;
  applying the shift anyway re-anchors a pin to a line that was never the one.
- **A pin is not always in a table's left column.** The two `provenance`
  write-ups carry before/after mapping tables whose right column records where
  a line sat before #739. Only the live column moved; the historical one is a
  record and re-anchoring it would rewrite history.

## What this opens

**`ec/tools/grade_gpu_door.py` carries the identical sentence.** Its module
docstring says "a byte that held still is a line of zeros, not a missing line,
because absence reads as missing data rather than as the strongest negative
this procedure can produce" over a `net`/`total`/`max` line for all 24 watched
addresses, built the same way — and it names the endpoint gap ("a byte that went
somewhere and came back between them reads as quiet") but not the sampling
period gap. The same fix belongs there. Left out because it is a different
procedure with its own runbook and its own suite, and this change already has
three shared files open.

**Two more sites carry the phrasing, and the next issue is all three.**
`docs/hardware-tests/oem4-07a6-bit0.md`'s *The two figures are not
interchangeable* says "a byte that held still reads as `net +0 … (0 changes)`"
over the same shape, and `ec/tools/grade_timer_sweep.py` says it in both its
header and its closing note ("Nothing above is a register status. A byte that
held still was not reached on the paths watched over this span, which is not
absence."). All three read as a fact about movement over a capture sampled at
intervals, and none names the sampling-period gap. None is in this change's
scope: the runbook belongs to #94's procedure and `grade_timer_sweep.py` is a
third procedure again, each with its own suite. **That is the next issue.**

Also open, and unchanged by this: **measuring the sampling period** is issue
#94's, and no runner can reach the machine or the driver. Nothing here measures
one IOCTL and nothing here should be read as if it did. What remains in its
place is the disclosure, which is the whole of this change.

## Nothing here was run against hardware

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the recipe above and the tests named. No fixture was
added, edited or regenerated by this change, and no line of it may be read as a
report of a capture or a live observation.