# A partly-graded run said "consistent with the static prediction" anyway (issue #477)

The write-up for [issue
#477](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/477), which is
about `ec/tools/grade_0751_isolation.py`'s closing summary having two cases
where the report has three. It is a prose and branch-structure change: **no
byte is read differently, no window is graded or withheld differently, and the
exit code is unchanged at 1.** Nothing here is a register behaviour and
nothing here is evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §5 is the static
prediction and §7 is the call the output feeds.

---

## The defect, on a committed fixture with nothing edited

`ec/tools/testdata/0751-isolation-run-3blocks/` is a three-value day: blocks
`0xA0`/`0x00`/`0x10`, all three blocks' marks in one set the way §3 takes
them, and block 2's restore mark absent in all three captures — what a mark
typed after that watcher had exited looks like, printed by `ec_watch.py` and
written to no CSV. So 2 of its 8 windows are withheld, 6 are graded, and
nothing §4.1-§4.3 names moves in any of the 6.

    python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-3blocks/*.csv

printed, before this change:

```
=== what this does and does not settle ===
  2 of the 8 window(s) above were not graded: the mark set of the block they fall in does not hold, or no block could be attributed to them at all. What they would have shown is not reported here and is not to be quoted from this run.
  None of the §4.1-§4.3 bytes moved in any window: consistent with the static prediction, for this capture's window only (§5: a byte that does not move inside the window may still move at the next suspend, AC transition or EC reset).
```

and prints, after it:

```
=== what this does and does not settle ===
  2 of the 8 window(s) above were not graded: the mark set of the block they fall in does not hold, or no block could be attributed to them at all. What they would have shown is not reported here and is not to be quoted from this run.
  None of the §4.1-§4.3 bytes moved in any of the 6 window(s) that were graded: that is what those 6 windows show, and the 2 window(s) withheld above are not part of it. The static prediction is a claim about the whole capture, and this output does not make it over a run it only read part of -- a run in which every window was graded is what would. §7's `confirmed-inert` needs all three values, and a block this report refused to read is one of the three, so the paragraph below is as far as this run goes.
```

**The banner was right in both.** "What they would have shown is not
reported here and is not to be quoted from this run" is exactly the truth
about a withheld window, and it is unchanged. What was wrong is the line under
it: "in any window" and "consistent with the static prediction" are claims
about the capture, and a run that read 6 of its 8 windows cannot make either
one. The two facts sat one line apart with nothing saying which was which, so
a reader had to notice the banner to know the sentence beneath it was about
6 windows and not 8.

## Why two cases were not enough

`#457` added a correct branch — "No window in this run was graded, so this
output says nothing about §4.1-§4.3 for it" — and it fired on
`elif withheld == len(shown)`, which is true only when *every* window was
withheld. A day with one graded block and one withheld block fell through to
the pre-existing `else` instead. Three cases were needed and two were there,
and the two that existed were the two ends.

The `moved_groups` branch was worse, and it was worse in a way that needed its
own fixture to show. It is tested *first*, so it is reached before any
withheld test at all: a run with a real §4.1 move and a withheld block
anywhere in the chain printed "At least one of the §4.1-§4.3 bytes moved
after a mark" and then "That contradicts the static prediction in
`manual-fan-ctrl-0751.md` §5 if it is the PLs" with nothing scoping either to
the windows that were graded.

**No committed fixture reached that combination.** Measured over the six
multi-capture sets, before this change:

| fixture | windows | withheld | graded | §4.1-§4.3 movement | exit |
|---|---|---|---|---|---|
| `0751-isolation-run-3blocks/` | 8 | 2 (block 2, `0x00`) | 6 | none | 1 |
| `0751-isolation-run-void-block/` | 2 | 2 | 0 | — | 1 |
| `0751-isolation-run-missing-mark/` | 3 | 3 | 0 | — | 1 |
| `0751-isolation-run-disagreeing-marks/` | 3 | 3 | 0 | — | 1 |
| `0751-isolation-run-multi-block/` | 6 | 0 | 6 | none | 0 |
| `0751-isolation-run-unplaced-window/` | 8 | 0 | 8 | none | 0 |

Three are all-withheld, two are clean, and the only partial one is quiet. So
the `moved_groups` scoping had nothing to run against, which is why
`ec/tools/testdata/0751-isolation-run-3blocks-moved/` exists: `3blocks/` with
one `0x0784` change row added inside block 1's (`0xA0`) write window — the
address and the step `0751-isolation-example-active.csv` records, so the two
agree — and every mark untouched. Same 2 withheld of 8, and now one of the 6
that were graded moved. It is constructed input, not a capture, and it says so
in its own header.

## The change

Confined to the closing-summary block in `ec/tools/grade_0751_isolation.py`,
plus one docstring paragraph.

- `graded = len(shown) - withheld`, computed once beside the accumulator.
  `len(shown)` and not `len(windows)`: it is the denominator the banner
  already uses, so the two counts agree by construction, and on a `--block`
  run it is that block's own windows.
- The withheld banner is byte-identical. It was correct in all cases and this
  does not touch it.
- `elif withheld == len(shown):` became `elif graded == 0:`. Equivalent —
  `moved_groups` is empty whenever nothing was graded, so the chain reaches
  the same branch either way — and it reads as the fact it is. **The sentence
  itself is byte-identical**; `test_a_mark_one_capture_never_recorded_stops_the_windows`
  asserts on it and was not edited.
- A new `elif withheld:` between that and the final `else`, for the partial
  case. It states the movement fact over the windows that were read, names the
  withheld count as outside the statement, and declines the run-level
  comparison rather than making a narrower one in the same words.
- Inside the `moved_groups` branch, the same scoping sentence is printed when
  anything was withheld, **before** the "That contradicts…" attribution, so
  the attribution reads as a claim about the graded windows.
- The final `else` is byte-identical, so a clean run still reads exactly as it
  did. The output of every previously-reachable fixture was diffed before and
  after: `void-block`, `missing-mark`, `disagreeing-marks`,
  `unplaced-window`, `multi-block`, §6's `0751-isolation-run/`, and the
  `example-active` and `example-mailbox-poke` captures are byte-for-byte
  unchanged.

The partial sentence opens on the same words as the clean ones —
`None of the §4.1-§4.3 bytes moved` / `At least one of the §4.1-§4.3 bytes
moved after a mark` — and diverges immediately after, so a reader who greps
for the opening still finds them and a test asserting the whole clean sentence
cannot be satisfied by a partial run.

## §7, and why the all-three-values gap is the consequence

§7 keys `confirmed-inert` on nothing moving across **all three values**, with
and without the vendor service (§3a). The withheld block in the fixture above
is `0x00` — one of the three. So a reader who took the prediction sentence at
face value could file a `confirmed-inert` claim resting on a block the same
report had just refused to grade, and the tool's strongest behavioural line is
the one that invites it. The new partial sentence closes the loop by pointing
at the §7 paragraph rather than restating it: the gap is named once, next to
the sentence that depends on it.

`docs/findings.md` §4 is the section recording what overclaiming cost this
repository, and `CLAUDE.md`'s calibration rule is explicit that a claim must
not be stronger than the evidence. This is that failure one level up: not a
claim about a register, but a claim about a capture the report read in part.
The fix is not allowed to introduce a *new* unqualified claim while removing
the old one, which is why each of the three sentences is a fact about the
subset it names — and why the partial one additionally says the withheld
windows were not read rather than guessing what they would have shown.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, 46 tests before and 49 after, all
passing under `bash tools/run-tests.sh ec/tools`:

| test | case | what it holds |
|---|---|---|
| `test_a_partly_withheld_run_says_what_its_graded_windows_show` | `3blocks/` | rc 1; the banner; the split named as 6 and 2; `'consistent with the static prediction'` **absent**; the all-withheld line **absent** |
| `test_a_movement_in_the_graded_windows_of_a_partly_withheld_run_is_scoped` | `3blocks-moved/` | rc 1; `PL1/PL2/PL4 (§4.1)` named as moved; the graded-subset scoping printed before the §5 attribution |
| `test_a_clean_multi_block_run_still_gets_the_prediction_sentence` | `multi-block/` | rc 0; the prediction sentence **and** §5's caveat |

The first two fail against the unfixed tool, which is the check that they are
testing the defect and not the fixture. The third is a pin, not a regression
test: **nothing in the repository asserted the clean sentence anywhere before
this change.** `grep` for `consistent with the static prediction` over the
committed tree found the tool and nothing else — the three
`assertIn('None of the §4.1-§4.3 bytes moved', out)` lines are on the opening
words only — so the strongest claim the tool makes could have been dropped or
reworded off every clean run without a failing test. The only two other
occurrences anywhere now are the two assertions this change added.

The pre-existing pins that stayed green and were not edited are the evidence
that the other two cases were not disturbed: the all-withheld assertion in
`test_a_mark_one_capture_never_recorded_stops_the_windows`, and the three
clean-run `assertIn('None of the §4.1-§4.3 bytes moved', out)` lines in
`test_quiet_capture_reports_nothing_moved`,
`test_pwm_and_temperature_movement_is_not_a_graded_result` and
`test_section6_command_line_over_section6s_file_set`. The change adds lines
to that suite and deletes none.

## Left out on purpose, and it wants its own issue

A `--block 0xA0` run over `0751-isolation-run-3blocks/` grades that block's
own windows and withholds nothing *within the run* — `graded == len(shown)`,
so no new branch fires — and still prints the unqualified prediction
sentence, while in fact covering 2 of the day's 8 windows. It is a real
adjacent question and it is a different one from this defect:

- this defect is a **withheld** window inside a run that read some of them,
  and the run-level count is wrong by an amount the report already knows;
- the `--block` case is a run that read exactly what it said it read. The
  denominator is right, the sentence is scoped to that denominator, and what
  is missing is any statement that the run was one block of a day.

The existing sentence already carries "for this capture's window only", the
§7 paragraph already says the output is an input to the call and not the
call, and widening this change into `--block`'s semantics would buy no part of
what this issue asks for. **Flagged, not fixed** — it is the one thing in this
neighbourhood worth an issue of its own.

Also unchanged, deliberately: `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`
does not quote the closing-summary text verbatim and §7's `confirmed-inert`
wording was already correct; `ec/annotations/registers.yaml` does not move —
no register status is in question, only what a report may say about the
windows it read; and `ec/README.md`'s `grade_0751_isolation.py` bullet
describes what the tool is and where its suite is, not how its closing summary
branches.

## Nothing here was run against hardware

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the command above and the three tests named. The
new fixture is a constructed input and is described as one in its own header
and in `ec/tools/testdata/README.md`; no line of this change may be read as a
report of a capture or a live observation, and none is one.
