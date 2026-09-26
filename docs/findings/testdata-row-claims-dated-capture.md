# A bare date in the testdata index's third column is resolved, and its literals are checked (issue #794)

The write-up for [issue
#794](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/794), which is
about `ec/tools/check_testdata_row_claims.py`'s own worst hole: the
`another capture's address` shape passed over **every** literal in a sentence
naming a dated capture in running prose, and the docstring said so itself —
*"the rule buys one correct row at the price of not checking that sentence at
all."* What this branch adds is **a census, a resolution and a retraction**: a
bare (unbackticked) date is resolved against `evidence/ec-watch/<date>-*` and
the sentence's literals are held to the files that date resolves to, so row 7's
two are checked rather than skipped, and a date that resolves to nothing is
today's `unresolved` **with the glob it searched** rather than a silent pass.

**Nothing here is a live test, and no capture is opened.** It is index/prose
agreement over committed text, the same class of claim as
[`testdata-third-column-claims.md`](testdata-third-column-claims.md): the CSVs
and `.txt` files under `evidence/ec-watch/` are read as text, exactly as
`carried_by()` already reads a fixture, and no EC, no firmware image and no
laptop is involved.

**Not claimed: that this would have caught #502 or #720.** Carried forward from
#747 verbatim, because both repairs were to this column and neither has been
read back as a diff this tool could have been run over. What it holds is the
tree as it stands.

## The census, measured on this tree, 2026-09-26

`grep -noE '`?20[0-9]{2}-[0-9]{2}-[0-9]{2}`?' ec/tools/testdata/README.md` over
the index gives **four** date tokens. The table's rows are lines 11+ (9 =
header, 10 = separator):

| line | row | spelling | sentence carries literals? |
|---|---|---|---|
| 7 | — (preamble above the table) | backticked `2026-01-01` | not a description cell; the tool never reads it |
| 13 | 3 | **bare** `2026-09-23` | **no** — "the shape the 2026-09-23 run actually saw, where the PWM drift was thermal" is its own sentence, and `CPU_TEMP` is not an address |
| 17 | **row 7** | **bare** `2026-09-23` | **2** literals: `0x0F58`, `0x0F5C` — the entire cost |
| 19 | row 9 | backticked `2026-09-23` | 5 literals, all about the row's own fixture — must stay that way |

**So: two bare dates, one of which costs anything, and the cost is exactly the
2 literals the run reported under the shape.** That is the whole sizing, and it
is small enough to check by hand before writing the rule — which is how the
other three censuses in this corner of the tree were sized too.

`evidence/ec-watch/` is **flat** — `find -mindepth 1 -type d` returns nothing —
and every capture is dated in its own filename, so `<date>-*` is a glob and not
a guess. `2026-09-23-*` resolves to **six** files, and per-file `grep -ic`:

```
2026-09-23-0751-isolation.txt                  0F58:0  0F5C:0
2026-09-23-ctgp-live.txt                      0F58:0  0F5C:0
2026-09-23-power-mode-cycle-0700-07ff.csv     0F58:0  0F5C:0
2026-09-23-power-mode-cycle-0f00-0f5f.csv     0F58:4  0F5C:6
2026-09-23-power-mode-cycle-0f00-final.txt    0F58:0  0F5C:0
2026-09-23-power-mode-snapshot-dc.txt         0F58:0  0F5C:0
```

**Both literals' verdict is `resolved`** — present in one of the six, so
present under the union. Both come off `unresolved` and onto `checked`, and
`another capture's address 2` leaves the shapes line entirely.

## The run, before and after

Before — #747's 2026-09-25 census, and re-measured on this tree with the
pre-change tool, which reads identically:

```
27 table row(s), 17 literal-bearing: 54 literal(s), 28 resolved, 0 missing, 26 unresolved
28 claim(s) checked, 14 claiming row(s), 26 passed over under the six shapes, each of them: not checked, not absent
shapes: capture/window bound 16, denial 3, another capture's address 2, dump-command argument 2, watched-set span 2, firmware code address 1
```

After, re-derived from the tool on this tree:

```
$ python3 ec/tools/check_testdata_row_claims.py --check
27 table row(s), 17 literal-bearing: 54 literal(s), 30 resolved, 0 missing, 24 unresolved
30 claim(s) checked, 15 claiming row(s), 24 passed over under the five shapes and a dated capture that resolves to nothing, each of them: not checked, not absent
shapes: capture/window bound 16, denial 3, dump-command argument 2, watched-set span 2, firmware code address 1
dated-capture claims, each held to the captures its date names and never to the row's own fixtures:
  2026-09-23-* (6 capture(s) under evidence/ec-watch): row 7 0x0F58 resolved, row 7 0x0F5C resolved
ec/tools/testdata/README.md: every address claim in the third column agrees with the fixtures its row names
```

**30 resolved / 24 unresolved, 30 checked, 15 claiming rows, 24 passed over,
five shapes with instances.** The other five shapes' counts are byte-identical
to #747's — 16, 3, 2, 2, 1 — which is the check that the change moved what it
was supposed to move and nothing else. **Claiming rows went 14 → 15**: row 7
now makes claims, which is the point.

## Two decisions, and why they are the hard ones

**A date, not a page.** `DATED_CAPTURE` (`(?<!`)\b20\d\d-\d\d-\d\d\b(?!`)`) does
**not** change. The index writes a *file* in backticks and a *capture* in
running prose, and the regex already tells the two apart by spelling. What
changed is what a match *does*: it was the reason a sentence's literals were not
checked at all, and it is now the selector of the file set they are checked
against. Row 9's backticked date is untouched by construction, and the
near-miss is preserved for the same reason it was introduced.

**Instead of, never unioned with, the row's own fixtures.** A dated sentence's
literals are held to the resolved capture set **or** to the row's fixtures,
never to both. The union would make row 7 trivially green via its own
`0751-isolation-example-moved-fan-after-0f00.txt` — the after-dump covers
`0x0F00-0x0F5F` — which is exactly the misattribution the exemption existed to
prevent. The suite pins both halves of this: one case has the capture carrying
the literals and the row's fixture carrying neither (fails if the date is
ignored), and one has the row's fixture carrying one of them and the capture
not (a `missing`, the run's only red verdict, and it fails if the two sets are
unioned). **The fix has to be able to fail, and which wrong implementation each
half catches is the reason there are two cases rather than one.**

**Union over the date, not a per-file read and not a prose-narrowed one.**
`<date>-*` matches all six files of 2026-09-23, and the sentence's own prose
("power-mode-cycle capture") is *not* used to narrow it. That is the same
discipline as the first column's `0x075B` union, and narrowing by a word in
prose would be the parser guessing — the exact thing the `BACKTICKED`-only entry
predicate exists to prevent. The cost is written down rather than designed away:
**one address in any of a date's files satisfies a claim about that date.** Row
7's sentence says "the shape the 2026-09-23 power-mode-cycle capture shows", so
a reader may reasonably want a tighter set than all six files, and the tool
does not give them one.

## The two near-misses, and why each stays

**Row 9's backticked `2026-09-23`** is a file the comparison is drawn from, and
its five literals are about the row's own fixture. It is untouched by
construction — `DATED_CAPTURE` cannot match it — which is the reason the rule
is spelled as a regex with lookarounds rather than as "a date in a sentence".

**Row 3's bare `2026-09-23`** resolves to the same six files and changes
nothing there, because the sentence carrying it holds no address literal at
all. It is in the census above because the census is over *date tokens*, not
over claims, and it is why the per-date breakdown below lists literals rather
than dates: a dated sentence with nothing in it has nothing to report.

## What the refusals now hold, and how each was checked

`test_check_testdata_row_claims.py` was 38 cases and is 42: four are new and
three are pre-existing cases rewritten, and it is the rewritten three that
carry the most weight.

- `test_an_address_belonging_to_another_capture_is_not_this_rows` **became**
  `test_a_bare_date_resolves_and_its_literals_are_the_captures` — the same
  row-7 sentence, now two `resolved` claims, and the claim's `files` field
  asserted to be the glob `2026-09-23-*` rather than the row's cell, so a report
  line cannot be read as a claim about the row's own fixture.
- `test_a_backticked_date_is_a_file_the_comparison_is_drawn_from` **stayed**,
  and is now load-bearing in a way it was not: a capture of 2026-09-23 now
  exists beside the fixture in that case and does *not* carry `0x07C4`/`0x07C6`,
  so reading the backticked date as a bare one would make both misses.
- `test_the_dated_claim_is_not_also_the_rows_own` is new, and is the `missing`
  case above — the one shape of this change that can turn the run red.
- `test_a_bare_date_resolving_to_nothing_is_unresolved_and_not_absent` is new,
  and is the calibration line made mechanical: `unresolved`, the glob
  `2026-01-01-*` in the report line, `dated capture not found` as the reason,
  `not absent` on the line, and `missing == 0`.
- Two more pin the per-date breakdown `main()` now prints, on scratch trees
  only — see below.

**`test_the_other_capture_rule` could not survive as written.** The rule's
direction is inverted: before #794, loosening it made the run check *more*;
now loosening it — pointing the run at a capture root with nothing in it —
takes row 7's two claims back out, so the run checks two *fewer*. It became a
sibling helper asserting `assertLess(after.checked, before.checked)`, and the
class docstring says why the sign differs rather than leaving a reader to
wonder whether the assertion is simply weaker.

**The mutations, run.** Three wrong implementations were applied to the tool
in place and the suite run over each, so the "can fail" claim above is
demonstrated rather than asserted: unioning the two file sets fails
`test_a_dated_claim_is_not_also_the_rows_own`; ignoring the date and holding
every sentence to the row's own files fails three cases; dropping the
`dated capture not found` reason fails three more.

**The committed tree has five shapes with instances, and the test says five.**
`test_the_committed_tree_exercises_every_shape` dropped
`another capture's address`; the sixth entry of the docstring's list — a dated
capture that resolved to nothing — has no instance here *by construction*,
because the one dated sentence in the tree resolves, so it is pinned in a
scratch case instead. The summary line's wording changed with it, and
`test_the_run_reached_something` reads the new label.

**No floor on the committed tree, and specifically not on the dated block.** The
per-date breakdown is asserted on a **scratch** tree, never as a count over the
committed one: the dated sentences there resolve, so an expected number of them
would turn every dated sentence a later PR adds into a failure — the same trade
`docs/agent-pipeline.md` records against a floor, and the reason
`test_the_run_reached_something` reads non-emptiness off the output rather than
a figure. The two cases there assert the *shape* of the block: which glob, how
many files it resolved to, and what became of each literal.

## Not claimed here, and what this does not do

- **That a fixture or a capture is what its row says it is.** Presence is
  **textual** — does the file carry `0xNNNN` anywhere, in any case — so a
  fixture that mentions an address in a comment satisfies the rule. The
  narrower question, "is there a row with this in the `addr` column", is
  `check_capture_claims.py`'s, over real captures, with a different owner.
- **Which of a date's files a sentence meant.** The union is over the date, and
  narrowing it by a word in the prose is declined on purpose (§ above). A
  sentence claiming a byte of one capture is satisfied by that byte in any of
  the date's files.
- **A second bare date in one sentence.** `DATED_CAPTURE` takes the first, as
  the rule it replaced took the sentence whole. There is no such sentence in
  the committed index; the limit is stated rather than met.
- **The other five shapes**, and the wording of a `missing` dated claim. Decided
  here rather than left open: the existing line is kept, because a disagreement
  is a defect in the index's prose about a fixture whichever fixture it is, and
  a reader is sent to the same place — the sentence. A follow-up may want
  distinct wording; that is not this issue.
- **Re-reading #502 or #720 as diffs.** Both repairs are to this column, and the
  disclaimer above is carried forward from #747.
- **Repairing any fixture, row or capture.** Nothing is wrong today. The
  committed index's row 7 sentence is **not edited** — it is true, it is now
  checked, and editing prose to make a tool green is the thing this repository
  forbids.
- **The gate wiring.** `docs/ci/agent-gates-testdata-row-claims.patch` is **not
  touched** — the tool's CLI is unchanged — and it remains a human's
  `git apply`. No gate is wired by this branch, and no commit runs this check
  in CI.
- **Live hardware, Windows, or the EC/BIOS/Windows stack.** Nothing here reads
  a register, opens a capture in any sense that touches hardware, or runs a
  capture-producing tool. No `status:` moved, so `ec/annotations/registers.yaml`
  is not touched at all.
- **Anything in another repository.** No PR or issue is opened anywhere; the
  upstream work the mission eventually means is unaffected by this change.
