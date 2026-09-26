# The carrier, the searched root, and the two file sets are named, and the closing sentence stops reading the same either way (issue #974)

The write-up for [issue
#974](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/974), which is
about `ec/tools/check_testdata_row_claims.py` saying less than it did. #794
gave a bare date in the index's third column a real file set to be held
against, and paid for it by writing the cost down as a **sentence** — *"one
address in any of a date's files satisfying a claim about that date"* — in
`docs/findings/testdata-row-claims-dated-capture.md` and in the tool's own
docstring. This branch does not design that cost away and does not change a
verdict. It makes the sentence a **number**: the dated block now names the file
that carried each literal, names the capture root the run was actually handed,
and the closing line names both file sets with a count each, so it can no
longer read the same whether the dated rule is there or the date is ignored.

**Nothing here is a live test, and no capture is opened.** It is report wording
over the same committed text, the same class of claim as
[`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md)
and [`testdata-third-column-claims.md`](testdata-third-column-claims.md): the
CSVs and `.txt` files under `evidence/ec-watch/` are read as text, exactly as
`carried_by()` already reads a fixture, and no EC, no firmware image and no
laptop is involved. **Corrected on merge, per `docs/findings.md` §4a** — #975
landed alongside this branch and made a *dated* claim columnar, so a dated
`.csv` is now parsed by `read_capture()` and the `.txt` members of a date carry
no column and are not read at all. The fixture read above is unchanged; the
sentence said every file under `evidence/ec-watch/` is read as text, and for a
resolved date that is no longer true of either half. Still no capture is
opened, and no hardware is involved on either reading.

**Not claimed: that this would have caught #502 or #720.** Carried forward from
#747 verbatim, because both repairs were to this column and neither has been
read back as a diff this tool could have been run over. What it holds is the
tree as it stands.

## The three defects, re-measured on this tree, 2026-09-26

### (a) The block said 6 files were eligible and not which of them carried the byte

`evidence/ec-watch/2026-09-23-*` is six files and per-file `grep -ic` gives:

```
2026-09-23-0751-isolation.txt                  0F58:0  0F5C:0
2026-09-23-ctgp-live.txt                      0F58:0  0F5C:0
2026-09-23-power-mode-cycle-0700-07ff.csv     0F58:0  0F5C:0
2026-09-23-power-mode-cycle-0f00-0f5f.csv     0F58:4  0F5C:6
2026-09-23-power-mode-cycle-0f00-final.txt    0F58:0  0F5C:0
2026-09-23-power-mode-snapshot-dc.txt         0F58:0  0F5C:0
```

**1 of 6**, in the file the sentence's own "power-mode-cycle" wording points
at. The block said `6 capture(s)` and `resolved`, and the reader had nowhere to
put that 1.

The narrower question underneath is real and is **not** claimed here: the
capture carries both literals as **change rows in the `addr` column** —
`2026-09-23T17:59:01.727+02:00,0x0F58,0x8C,0x6E` — and whether an address has
a row in the `addr` column rather than merely occurring as text is
`check_capture_claims.py`'s, over real captures, with a different owner. This
tool's question is textual and stays textual.

> **That last sentence was superseded on merge, and is corrected here rather
> than deleted, per `docs/findings.md` §4a.** #975 gave the `addr`-column
> question an owner *in this tool*: a dated claim is now held to the `addr`
> column of the date's `.csv` members, read with `read_capture()`, and the
> `.txt` half contributes no column. See
> [`testdata-addr-column-claim.md`](testdata-addr-column-claim.md). What the
> paragraph got right stands and is what makes the merge's own figure
> checkable: the file named on the dated line is the one carrying the literals
> **as change rows**, and it is the only carrier of the six under either
> reading, so `1 of 6` is the same number before and after. What it got wrong
> was the owner.

### (b) The block named the committed root for any run pointed elsewhere

`dated_report()` printed `repo_path(CAPTURES)`, the module constant, while
`check()` takes `captures=CAPTURES` as a **parameter** and `Result` carried no
root at all. Every run the suite makes is pointed at a scratch root
(`ScratchIndex.check()` passes `captures=self.captures`), so every scratch run
printed `evidence/ec-watch` for a directory it never opened. The two cases
asserted on that block — the glob and the capture count — could not see it,
which is why it survived the run they were written for.

### (c) The closing line was invariant under the change #964 made, at the row where the union's cost was paid

`every address claim in the third column agrees with the fixtures its row
names` became a sentence about **30** claims on the day a bare date started
redirecting two of them to files the row does not name. It reads exactly the
same whether the redirect is there or the tool ignored the date and held every
sentence to its own row — which is the misattribution the dated rule exists to
prevent, made invisible by a summary that cannot tell the two apart.

**The sharper half, and the reason the obvious fix does not work.** Row 7's own
`ec/tools/testdata/0751-isolation-example-moved-fan-after-0f00.txt` carries both
literals — on **line 8 only, a `#` comment in the fixture's own header**, and
the comment is a quotation of the sentence that is not about it:

```
# The three taking the same value is the shape the 2026-09-23
# power-mode-cycle capture shows -- those three track 0x0F58-0x0F5C through
# 0xC8/0x6E/0xAA in
# evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-0f5f.csv -- so this is the
```

So a union would satisfy a claim about a capture with a prose mention in the
row's own fixture, and with the date ignored the two verdicts **flip to
`resolved`**, the run stays green, and the dated-claim **count is 2 either
way**. This is the concrete form of (c), and it is what forces the wording
below.

**On the merged tree the same misattribution has a narrower door and is not
closed.** A dated claim is answered by the `addr`-column read, so the `#`
comment above no longer carries one at all; a union would have to reach a real
**row** in one of the row's own `.csv` files to satisfy a claim about a capture.
The rule's `or` rather than a union is unchanged and still the same decision —
`check()`'s own case holds both directions — but the sentence above is now
demonstrating that a *textual* union is unsound, not that a *columnar* one
would be. What the union still costs is unchanged, and it is what the dated
block now prices.

## The run, before and after

Before — re-derivable with `python3 ec/tools/check_testdata_row_claims.py
--check` on `26e970d5`:

```
27 table row(s), 17 literal-bearing: 54 literal(s), 30 resolved, 0 missing, 24 unresolved
30 claim(s) checked, 15 claiming row(s), 24 passed over under the five shapes and a dated capture that resolves to nothing, each of them: not checked, not absent
shapes: capture/window bound 16, denial 3, dump-command argument 2, watched-set span 2, firmware code address 1
dated-capture claims, each held to the captures its date names and never to the row's own fixtures:
  2026-09-23-* (6 capture(s) under evidence/ec-watch): row 7 0x0F58 resolved, row 7 0x0F5C resolved
ec/tools/testdata/README.md: every address claim in the third column agrees with the fixtures its row names
```

After, from the same command on the merged tree:

```
27 table row(s), 17 literal-bearing: 54 literal(s), 30 resolved, 0 missing, 24 unresolved
30 claim(s) checked, 15 claiming row(s), 24 passed over under the five shapes and the two dated refusals, each of them: not checked, not absent
shapes: capture/window bound 16, denial 3, dump-command argument 2, watched-set span 2, firmware code address 1
dated-capture claims, each held to the captures its date names and never to the row's own fixtures:
  2026-09-23-* (6 capture(s) under evidence/ec-watch, 2 with an addr column): row 7 0x0F58 resolved in 2026-09-23-power-mode-cycle-0f00-0f5f.csv, row 7 0x0F5C resolved in 2026-09-23-power-mode-cycle-0f00-0f5f.csv
  0 of 15 capture(s) in evidence/ec-watch are out of the reach of every <date>-* glob: none
ec/tools/testdata/README.md: every address claim in the third column agrees with the files it was held to -- 28 with the fixtures their row names, 2 with the captures a bare date in their sentence names
```

**Every figure is byte-identical, and that is the check that the change moved
reporting and not checking.** 54 literals, 30 resolved, 0 missing, 24
unresolved, 30 checked, 15 claiming rows, five shapes at 16/3/2/2/1, and rc 0 —
all unchanged. Three lines of wording changed and nothing else; on the merged
tree the dated line carries a **third** clause, `, 2 with an addr column`, which
is #975's and reports a fact about the *file set* rather than about any claim,
and the block carries a **line beneath it** — `0 of 15 … out of the reach of
every <date>-* glob` — which is #973's and is #973's own finding about the two
premises the `<date>-*` glob rests on, not this issue's. The 28/2 split **sums
to `result.checked`**, which is asserted on the committed tree; it is derived,
not written down, so a dated sentence a later PR adds moves it without breaking
anything.

> *(Corrected on this merge, beside the block rather than in it. The `a dated
> capture that resolves to nothing` this transcript carried is the wording of
> the tree **#975** merged into, and it is left above per `docs/findings.md`
> §4a-4d — the count beside it, `24`, is the same here and the run was green
> there too. **#979** landed on the other side of this merge and added a
> **second** dated refusal — a sentence naming two or more bare dates is passed
> over whole — so the line now reads *the two dated refusals* and the closed
> shape list is **seven** entries rather than six. No figure moves: no committed
> row names two dates, so the new shape has no instance and the `shapes:` line
> is unchanged. The transcript above is re-run on this tree, not carried.)*

## Three decisions, and why they are the hard ones

**Every carrier, not the first match.** `carried_by()` returned a `bool` and
short-circuited on the first path that carried the byte. Keeping that would
print **one** name for a date whose two files both carry it — understating the
very cost the issue asks to make measurable, and doing it silently. It returns
the sorted list of carrying paths and the block prints all of them.
`carried_by_column()`, added by #975 on the other side of this merge, now
returns a list for the same reason and on the same shape, so `Claim.carriers`
means one thing whichever reader answered and the block does not care which ran.
The cost is measured rather than assumed: on the merged committed tree the two
readers together read **40** files with a first-match short-circuit and **97**
reading every set whole — `carried_by` 36 against 93 and `carried_by_column` 4
against 4 — out of a 140 KB `testdata/`, and the difference does not show in the
run's wall time: **32.1ms against 33.0ms** for `check()` alone, best of nine
runs each. `Claim.carriers` is empty for a claim that was never checked and for
a `missing`, which nothing carried.

> *(The **32** and the **78ms/79ms** this paragraph carried are the branch's own
> instrumentation on its own tree and are left visible per `docs/findings.md`
> §4a-4d. The whole-set **97** reproduces byte for byte here; the short-circuit
> figure does not — re-measured it is **40** reads over **20** distinct files,
> against the whole side's 97 over 47, and I cannot say from here which of the
> two readers the branch's `32` was counting, so the reason the number differs
> is not claimed either way. **What the measurement is for does not depend on
> it**: the short-circuit is 57 file reads cheaper against a corpus where the
> whole-set side is the same 97 it was when the figure was written, and that is
> the order the argument needs.)*

**The root on `Result`, and only on `Result`.** One field, appended at the end,
which is safe because every consumer reads attributes by name and `check()` is
the only place that constructs one. The carrier is printed as a **bare
basename**: the root is on the same line and `captures_for()` globs exactly one
directory, so a basename identifies the file within the named set — where
`repo_path()` over the suite's scratch root would put a `../../../..` chain onto
the very line the new case reads.

*Left out on purpose, and the reason is checkable rather than a shrug.*
`main()`'s closing line still labels the index with `repo_path(INDEX)`, which is
the same class of constant. It is not a defect today: `main()` is that line's
only caller and it always calls `check()` with the default root, so **no run
that prints the line ever searched another tree**. Carrying the root for the
index as well would be a change with no wrong output to fix, and the issue does
not ask for it. The asymmetry is written down rather than left for the next
reader to find.

**The agreeing count per set, and why a dated count cannot work.** The obvious
wording — *"…and 2 are held to the captures a date names"* — is the number
that does not move: 2 under both readings, because the row's own after-dump
carries both literals (§ above). So the line has to carry a figure the two
readings disagree about, which is **how many claims agree with each set**.
Measured on this tree, by re-running `check()` with `captures_for()` mocked to
`(UNRESOLVED, [], "")` — the date ignored and every sentence held to its own
row — the two runs are **both green and both 30 checked**, and the split is the
only thing between them:

```
as shipped:  ... agrees with the files it was held to -- 28 with the fixtures their row names, 2 with the captures a bare date in their sentence names
date ignored: ... agrees with the files it was held to -- 30 with the fixtures their row names, 0 with the captures a bare date in their sentence names
```

`missing` is 0 in both. That is the whole of (c) in one line: an implementation
that never resolved a date would print **the sentence §76 printed**, exit 0,
and pass every count the run had. A claim is dated by **membership in the
globs `result.dated` already carries**, so (c) needed **no new field**:
`Claim.files` is what the claim was held against, and a claim's `files` can be a
pattern only when the date resolved — a date that resolves to nothing makes
`reason_for()` return `dated capture not found` and the claim `unresolved`.

*The trap, and it is in the tool's docstring too:* a claim listed in
`result.dated` that was **passed over** under one of the five shapes was never
held to that set at all. The split therefore runs over the *checked* claims, and
the two counts are of claims that **agree**, which is why they sum to
`result.checked` on a green run and fall short of it on a red one — a red run
never prints this line, because `main()` returns before it.

## What the cases now hold, and the mutations run

`test_check_testdata_row_claims.py` was 42 cases and is **58** on the merged
tree: five are new from this branch, five from #975, three from #979, three more
from #973, and one is extended, and the extensions carry more weight than the
additions.

> *(Corrected on this merge, twice over. The **52** this sentence carried is the
> tree #975 merged into and is left per `docs/findings.md` §4a-4d; **#979** added
> three cases of its own on the other side, so the figure is re-derived by
> running the suite rather than by adding the three. **#973 then added three more
> on top of that**, for the **58** here — re-run, not carried. None of the
> eleven additions is one of the cases below, and none of the cases below
> changed.)*

- `test_the_dated_breakdown_names_each_literal_and_its_file_set` is
  **extended, not duplicated**: its scratch tree already had
  `2026-09-23-cycle-a.csv` carrying `0x0F58` and `-cycle-b.csv` carrying
  `0x0F5C`, so the two carrier substrings were added to the case that already
  asserted the glob and the count. The `2026-09-23-* (2 capture(s)` assertion
  is retained **unchanged**, which is the point: it is the one that could not
  see defect (b). Both captures are `.csv` rows, so the case now runs the two
  additions end to end — the names come from the `addr`-column read, and
  `, 2 with an addr column` rides on the same line.
- `test_a_literal_two_of_the_dates_files_carry_names_both` is new, and pins
  the **plural** — two captures carrying one address, both named. It is the
  case that fails if the short-circuit is kept, and on the merged tree it is the
  case that fails if it is kept in **either** reader: its date resolves, so the
  two carriers are named by `carried_by_column()`.
- `test_the_block_names_the_capture_root_the_run_was_given` is new and is the
  case that fails if `repo_path(CAPTURES)` comes back.
- `test_the_closing_line_splits_the_two_file_sets` is new, and the one worth
  the most. Its tree is built as **row 7's is**: the row's own fixture carries
  every address the sentence claims, so **both readings are green** and the
  only thing left to differ is the wording. It asserts `-- 1 with the fixtures
  their row names, 2 with the captures …` and then re-runs the same tree with
  `captures_for` mocked to `(UNRESOLVED, [], "")` — *"the tool ignored the date
  and held the sentence to the row's own files"* — and asserts `-- 3 … 0 …`.
  Both halves assert `report()` returned 0, so the case turns on the wording
  rather than on a red exit code.
- `test_the_closing_line_names_both_file_sets_and_they_add_up` is new and is
  the committed tree's: **the shape only** — that both sets are named, and
  that the two counts sum to `result.checked`. **No count over the committed
  tree**, for the reason `docs/agent-pipeline.md` records and
  `test_the_run_reached_something` already follows; the arithmetic is checked
  because it follows from the run, not from the tree's size.
- `test_the_committed_tree_cannot_tell_the_two_readings_apart` is new, and it
  is the case that makes the measurement in § above reproducible rather than a
  claim only this write-up stands behind: the committed run with the date
  ignored is **still green**, still the same number of claims, and differs from
  the shipped run **only after the `--`** — the sentence is identical and the
  two figures are what moved. Without it, the scratch case above would still
  pass after someone collapsed the split back to one number, and nothing would
  say why the split had been load-bearing. It asserts relations, not figures.
- `test_the_two_door_discriminations_the_issue_names` is the suite's only
  other `carried_by()` call. It is updated to the list return, and it now
  asserts the **exact** carrier and that `0x07C4` is carried by nothing in that
  set — a `bool` would have been satisfied by the first and blind to the second.
  The other four from #975 are the columnar half beside it, unchanged by this
  branch: the `#`-header-is-not-a-row case, its `addr`-row counterpart, the
  `, 0 with an addr column` clause on a `.txt`-only date, the rule held by
  swapping the reader back, and — on the committed tree — every dated claim
  `resolved` with fewer than all of that date's files carrying a column.

**`test_the_run_reached_something` parses `number label` pairs off stdout, and
that was checked rather than assumed.** The new closing wording puts a pair of
its own on the last line — `2 with the captures a bare date in their sentence
names` — and it collides with **none** of the seven labels the case asserts, so
no figure there is shadowed by a later line parsing to the same key. The case
now says so in a comment, because a wording change that *did* collide would
leave a stale figure reading as a real one.

**The mutations, run.** Six wrong implementations were applied to the tool in
place and the suite run over each, so "the fix can fail" is demonstrated rather
than asserted. The first five are this branch's; the last is #975's own rule,
run here so the merged tree's two halves are shown failing separately:

| mutation | cases that go red |
|---|---|
| print `repo_path(CAPTURES)` again | `test_the_block_names_the_capture_root_the_run_was_given` (1) |
| drop the carrier from the block | the two dated-breakdown cases (2) |
| restore the first-match short-circuit in **both** readers | `test_a_literal_two_of_the_dates_files_carry_names_both` (1) |
| `captures_for` returns `(UNRESOLVED, [], "")` — the date ignored, the row's own files used | **16**, including `test_the_closing_line_splits_the_two_file_sets` |
| collapse the split to one total — `-- N with the fixtures their row names` | **3**, both closing-line cases and the date-ignored half of the committed-tree case |
| revert a dated claim to `carried_by()` — #975's rule | `test_a_header_mention_is_not_a_row_and_the_claim_is_missing` (1) |

The **16** is the branch's 9 plus the five cases #975 added, all of which are
about a date that resolved and so go red when no date ever resolves, plus the
**two** of #979's three that read a date at all -- its third asserts the
two-date refusal and stays green when no date resolves, which is correct: a
tool that resolved nothing refuses nothing.

*(The **16** and the decomposition above are left written per
`docs/findings.md` §4a-4d, and both are superseded: they are true of the
#974 × #979 × #985 tree, and this tree reads **19**, for the reason the
re-derivation below gives. The claim about the third of #979's three is the
half that is simply false -- the third does stay green, but not because a tool
that resolved nothing refuses nothing, and both of the other two go red.)*

> *(Re-measured on this tree rather than carried, and **three** of the six rows
> needed it rather than one. The **14** and the **2** this table carried are the
> tree #975 merged into and stay visible per `docs/findings.md` §4a-4d; every
> mutation was re-applied to the tool on this tree and the suite re-run over each,
> and the tool is byte-identical to this tree's afterwards. The `2`/`1`/`1` in the
> three untouched rows reproduce unchanged. The `captures_for` mock is still
> spelled `(UNRESOLVED, [], "")` and still works unchanged even though #979
> widened the third field from one glob to a list of `(glob, files)` pairs: an
> empty string and an empty list both iterate zero times over the per-date loop,
> which is the only thing that reads it.)*
>
> **What the runner reds, measured on this tree** -- the three rows this
> re-derivation says something new about, each the number `python3
> ec/tools/test_check_testdata_row_claims.py` prints over the mutation rather
> than the cases the table names:
>
> - **The date-ignored row is 19, not 16.** `FAILED (failures=19)` over `Ran 58
>   tests`. The **16** was measured on the #974 × #979 × #985 tree and is this
>   branch's **four** plus the **twelve** the same mutation reds on #979's tree
>   alone; the three that moved on since are **#984's**, all of them red because
>   they ask what the run read out of the root -- the denominator and the
>   unreadable root -- and a run that resolves no date reads nothing out of it.
>   **The load-bearing part of the row holds**:
>   `test_the_closing_line_splits_the_two_file_sets` is among the 19, and so is
>   the date-ignored half of
>   `test_the_committed_tree_cannot_tell_the_two_readings_apart`.
> - **Both of #979's two-date cases are among the 19**, and the reason is not
>   that the refusal goes away. A run that resolves no date still refuses:
>   `reason_for()` reads the multi-date refusal off the *sentence*, ahead of
>   every reason that reads a file, so the reported reason is still `two dated
>   captures in one sentence` and
>   `test_a_two_date_sentence_is_refused_with_its_literals_in_neither_day` --
>   which asserts that reason, the verdicts and `result.missing`, and reads no
>   glob -- stays green. The other two fail on their own next assertion: a run
>   carrying no globs prints a refused sentence's stderr line naming **neither**
>   date, and `test_a_two_date_sentence_is_refused_rather_than_read_from_the_first`
>   and `test_two_dates_of_which_one_resolves_to_nothing_are_refused_still` both
>   assert that both of their dates appear on that one line. A tool that resolved
>   nothing still refuses; it just cannot say which dates it declined to choose
>   between.
> - **The split-collapsed row is 2 or 3, and which `N` it means is the whole
>   difference.** Collapsed to `len(own)` alone -- the row's own agreeing count --
>   it reds **2**, the two closing-line cases, and leaves
>   `test_the_committed_tree_cannot_tell_the_two_readings_apart` green, because
>   that case's `assertNotEqual` still holds on 28 against 30. Collapsed to the
>   **combined** total (`len(own) + len(captures)`) it reds **3**, and that is
>   the collapse the table's **3** was measured on, so the **3** stands; the row
>   was ambiguous about which `N` it meant, and this is the note that says so.
> - **The `repo_path(CAPTURES)` row is 2, not 1**: the new
>   `test_the_block_names_the_capture_root_the_run_was_given` and the
>   pre-existing `test_the_block_and_its_denominator_name_the_root_the_run_was_given`
>   beside it, whose `assertNotIn(ctrc.CAPTURES, block)` cannot survive the
>   constant coming back.

**The committed tree is green under both readings, which is the whole of
(c):** it cannot tell them apart by verdict or by exit code, so the case that
reads the disagreement has to be a scratch tree — and the case that keeps the
premise honest has to be the committed one.

## Not claimed here, and what this does not do

- **That the tool now checks more, or that the file set got tighter.** It checks
  exactly what it checked. Naming the carrier narrows nothing — every path in
  the set is still read and the set is still the whole date — and no verdict
  moved. **The `.txt` half of a date is narrower than either side said**: it is
  not read textually any more either, because a dated claim is now answered by
  the `addr` column. That is #975's change and it is stated there; what it does
  not do is narrow the *set*, which is still the whole date, or move a verdict,
  which `1 of 6` and `0 missing` both witness.
- **Which capture of a date the sentence was about.** The carrier named on the
  line is the file that *satisfied* the claim, which is not the capture the
  sentence was about, and the report line is not the place to have quietly
  decided it. Narrowing the set by the prose's "power-mode-cycle" wording is
  declined here exactly as #794 declined it: that would be the parser guessing.
- **That the old closing line was false.** It was accurate for the tree it was
  measured on, and it is **superseded, not retracted**. The two predecessor
  write-ups that quote it verbatim —
  `testdata-row-claims-dated-capture.md:82` and
  `testdata-third-column-claims.md:53` — are **left exactly as written**,
  following the precedent in `testdata-index-suite-count-floor.md` (*"a
  write-up is a record of what its branch measured"*) rather than the §4a
  pattern, which is for a conclusion stated more strongly than its evidence
  supported. This one was not. *(The `:36` this bullet carried on the branch is
  left written; `testdata-third-column-claims.md:53` is where that transcript
  stands on the merged tree, measured by reading the line rather than by
  carrying the pin — the same correction the twenty-seventh note in
  `tools/README.md` records for its own.)*
- **Anything about a live machine.** No capture is *opened*, no EC is read, no
  Windows is involved, and the `evidence/ec-watch/` files are read as text
  exactly as `carried_by()` already read them. No `status:` moved, so
  `ec/annotations/registers.yaml` is not touched. *(Corrected on merge: a dated
  `.csv` is parsed by `read_capture()` rather than searched as text. The file is
  still only read, and nothing about it is opened in any sense that touches
  hardware.)*
- **`ec/tools/testdata/README.md`, row 7's sentence, and any fixture or
  capture.** Nothing is wrong with any of them today; editing prose to make a
  report look better is what this repository forbids.
- **The `0x888D` filter's blind side, the other five shapes, and the `missing`
  wording.** All decided by the predecessor write-up and unchanged here.
- **`tools/README.md`'s suite totals.** The branch's own delta was `1168 →
  1173` on a tree that did not carry #975 — a figure its sibling note in that
  file puts at `1182`, and neither is left to be reconciled here in place of a
  number. It is **renumbered at the merge by the merge**, three times over:
  with other PRs open a branch cannot know the merged number, which is what the
  twenty-first note's own account says, and by the time this branch lands `main`
  has moved repeatedly under it. **The `39`/`1216` this bullet records is the
  #974 × #979 × #985 merge; the tree this write-up now sits in reads `40
  suite(s) run, 1238 tests`**, with #973's suite and its three cases the whole
  of the step and this issue still contributing `+5` and no suite. Both
  figures are left written, and `tools/README.md`'s twenty-ninth and
  thirtieth notes are the records of them — those two numbers, the
  twenty-seventh and twenty-eighth, are the ones their own tree read and stay
  written per [`../findings.md`](../findings.md) §4a-4d. The measured delta on
  each side is here and the per-pin re-registration that the merge forced is
  there — **`tools/README.md:208`** on that tree, the third value that pin has
  held, **`tools/README.md:249`** on the `#780` × `#974` tree, the fifth, and
  **`tools/README.md:279`** on the tree this write-up now sits in, the sixth.
- **This write-up's own place in `docs/findings.md`.** Its summary was written
  as §77, renumbered twice while the branch was open to **§79**, and is
  **§82** on this tree: `main` took §77 for #811, §78 for #979, §79 for #973,
  §80 for #780 and §81 for #978, and the rule is that the summary already on
  `main` does not move. `tools/README.md`'s thirty-first note carries the fourth
  rename and its thirty-second the fifth. **The `§81` this bullet carried is
  left visible and is true of the `#780` × `#974` tree it was measured on.**
- **`docs/ci/agent-gates-testdata-row-claims.patch`.** The CLI is unchanged
  (`--check` is still accepted and is still the whole of it), so the patch
  needs no edit and stays a human's `git apply`. **No gate is wired here.**
- **`.github/workflows/` and `.github/actions/`.** The pipeline's push token has
  no `workflow` scope, so a branch touching them fails at the end rather than
  the start.
- **Anything in another repository.** No `gh` command runs in this work. If a
  follow-up ends at an upstream patch, the deliverable is the prepared patch
  and description committed here for a human to submit.
