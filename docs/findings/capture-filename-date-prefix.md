# The capture root's date prefix and its flatness are measured, and a name breaking either is refused (issue #973)

`captures_for()` in `ec/tools/check_testdata_row_claims.py` builds
`f"{date}-*"` and globs it under `CAPTURES`. **That glob is a glob rather than
a guess only because of two properties of `evidence/ec-watch/` that nothing on
the tree read**: every file in the root is dated in its own filename, and the
root is flat. `docs/findings/testdata-row-claims-dated-capture.md` states both
as premises (at its `:45`-`:46`), and `captures_for()`'s own docstring gives
them as the *reasons* its glob is one. Both are true on this tree today. This
branch is **a census of both, a denominator the run prints, and a refusal for a
name that breaks either.**

**Nothing here is a live test, and no capture is opened.** A directory listing
is read and a name is matched against a shape. No EC, no firmware image, no
laptop, no Windows, and no byte of any capture is involved — the same class of
claim as
[`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md),
one level further from the data.

**Not claimed: that this would have caught #502 or #720.** Carried forward from
#747 verbatim, because both repairs were to this column and neither has been
read back as a diff this tool could have been run over. What it holds is the
tree as it stands.

> **Superseded, 2026-09-26, by issue #978,** which is about
> `check_testdata_row_claims.py` and not about a capture's name: the pre-repair
> trees were extracted and the checker run over each, and the answer is 0
> `missing` at every row either repair touched. The paragraph above is kept as
> it stood rather than edited out, per `docs/findings.md` §4a; see
> [`testdata-row-claims-repair-measurement.md`](testdata-row-claims-repair-measurement.md).

## The census, measured on this tree, 2026-09-26

The four commands, run from the repository root, and their output verbatim:

```
$ ls evidence/ec-watch/ | wc -l
15

$ ls evidence/ec-watch/ | grep -cE '^20[0-9]{2}-[0-9]{2}-[0-9]{2}-'
15

$ ls evidence/ec-watch/ | grep -vE '^20[0-9]{2}-[0-9]{2}-[0-9]{2}-'
(empty)

$ find evidence/ec-watch -mindepth 1 -type d
(empty)
```

**15 files, 15 conforming, 0 non-conforming, and no subdirectory.** Every capture
in the root complies, and the root is flat — which is precisely why the
`#794` merge could size its rule at two literals by hand. The four commands
say nothing about whether that still holds tomorrow, and until this branch
nothing held it at all.

Three dates are on disk:

```
$ ls evidence/ec-watch/ | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort | uniq -c
      3 2026-09-18
      6 2026-09-23
      6 2026-09-24
```

And the index carries four date tokens, of which two are bare — the two
`DATED_CAPTURE` can match:

```
$ grep -noE '`?20[0-9]{2}-[0-9]{2}-[0-9]{2}`?' ec/tools/testdata/README.md
7:`2026-01-01`
13:2026-09-23
17:2026-09-23
19:`2026-09-23`
```

The two bare dates are both `2026-09-23`, and they resolve to six files:

```
$ ls evidence/ec-watch/2026-09-23-*
evidence/ec-watch/2026-09-23-0751-isolation.txt
evidence/ec-watch/2026-09-23-ctgp-live.txt
evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv
evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-0f5f.csv
evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt
evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt
```

The other two tokens are backticked, so `DATED_CAPTURE`'s lookarounds cannot
match them, and line 7 is above the table and never read at all. **So the
census sizes the rule's users at one dated sentence and two literals, and that
is the entire population at risk.**

## The two questions, and why conflating them would be a false alarm

This is the part the issue's own figures blur, so it is worth stating
plainly, because a `9 of 15` line in this run's output would be read as an
alarm about nine files when nothing whatsoever is wrong.

**How many captures the run reached** is **6 of the 15**. The run globs the
dates the *index* names, and the index is a description of the testdata
fixtures — **not a manifest of `evidence/ec-watch/`**. The other 9 are
conforming captures (three of `2026-09-18`, six of `2026-09-24`) that no dated
sentence mentions. That is normal, it is not a finding, and it is not a
property of the naming convention.

**How many files in the root are reachable at all** is **0 of 15** — and
*that* is the property the convention is about. A file whose name does not
begin `20\d\d-\d\d-\d\d-` is out of the reach of **every** `<date>-*` glob,
including the one its own contents would belong to. It is not a capture the
run reads less of; it is one the run never reads, whatever the index says.

The second is the number that makes the premise checkable and the first is the
number that would be wrong to print. `dated_report()` therefore prints the
second, and `ec/tools/check_capture_names.py` refuses on the second.

## The run, before and after

`ec/tools/check_capture_names.py` did not exist before this branch. Its
`--check` over the committed root:

```
$ python3 ec/tools/check_capture_names.py --check
15 capture(s) under evidence/ec-watch/, 0 without a date prefix, 0 subdirector(ies)
every capture in the root is dated in its own filename and the root is flat, so `captures_for()`'s `<date>-*` is a glob rather than a guess
```

`check_testdata_row_claims.py` before, dated block only — the tallies are
unchanged by this branch and are left where `#794` put them:

```
$ python3 ec/tools/check_testdata_row_claims.py --check
  ...
  2026-09-23-* (6 capture(s) under evidence/ec-watch): row 7 0x0F58 resolved, row 7 0x0F5C resolved
```

and after, with the denominator line and with the block naming the root the run
was actually handed rather than the module-level `CAPTURES`:

```
  2026-09-23-* (6 capture(s) under evidence/ec-watch, 2 with an addr column): row 7 0x0F58 resolved, row 7 0x0F5C resolved
  0 of 15 capture(s) in evidence/ec-watch are out of the reach of every <date>-* glob: none
```

*(Merged-tree note, 2026-09-26, re-run on the second merge's tree as well as the
first: the "after" block above is **the merged tree's, not this page's**, and the
`after` line is the one the merged tool prints today. Two other clauses are on
it, and neither is this issue's — #975 (issue #982) put the `, 2 with an addr
column` on the file-count line before this page was written, and #979 (issue
#983) landed beside it and changed `captures_for()`'s *shape* without changing
what the one dated sentence in the committed index resolves to, so the block is
the same two literals keyed by the same glob. **Nothing this page is about
moved:** the two figures are the tallies and the `0 of 15`, and both are
unchanged at `30 resolved, 0 missing, 24 unresolved` and `15 capture(s) … 0
without a date prefix, 0 subdirector(ies)`, measured by running both tools on
the merged tree. The "before" block above is left as written because it is
`#794`'s dated record, which is what the line above it already says — and it is
not what either merge-base prints either, for the same reason the `2 with an
addr column` clause is there. Three clauses on one line is a readability cost
this page does not get to weigh, and none of them is a second denominator: one
counts the date's `.csv` members, one names the tree the run was handed, and the
line beneath them — the only denominator this page is about — counts the files
no glob can reach. Those are the two questions this page has kept apart
throughout.)*

**The tallies are byte-identical: `30 resolved, 0 missing, 24 unresolved`.**
That is the check that this branch moved reporting and not verdicts, which is
the whole of what was intended. The line costs nothing when the answer is
`0 of 15`; what it buys is that a capture arriving without its date shows up
as `1 of 15` rather than as a run quietly checking less.

## The decision: a refusal, not a wider glob

`captures_for()` could also be taught to try a date *embedded* in a filename,
which would catch a trailing-date capture without anyone's permission. **It is
declined, and the census says why.** The rule's population is one dated
sentence and two literals. Widening the glob changes *what a claim is held
to* on a rule with almost no users: a filename carrying two dates is ambiguous,
and a widened resolution can turn a calibrated `unresolved` — "not checked by
this method, not absent" — into a red `missing` or a green `resolved` with
nobody having edited a file. **That is a coverage change wearing a naming
guard's clothes, and it belongs in its own issue with its own census.**

A refusal, by contrast, is decidable from one directory listing, has a
denominator, and leaves every verdict exactly as it is.

## What each refusal holds, and what each costs

The tool reads one listing and reports **two refusals in two vocabularies**,
because they are different mistakes with different fixes and a merged count
would leave a reader guessing which premise had stopped holding.

**A name carrying no `^20\d\d-\d\d-\d\d-` prefix.** The cost is the silent
direction, and the suite demonstrates it against `captures_for()` itself rather
than asserting it in prose: with the date's only capture unprefixed, the glob
comes back empty, `captures_for()` reports `missing`, and this tool's own
vocabulary makes that `unresolved` — *"not checked by this method, not absent"*
— **so the run stays green while covering strictly less than it did.** That is
the state the denominator line exists to make visible.

**A subdirectory in the root.** The second premise, and until this branch it
was checked nowhere at all. It is a real blind spot rather than a hypothetical
one: `glob.glob()` returns directories, so `<date>-*` would match one, and
`carried_by()` skips anything that is not `os.path.isfile`. The date resolves
to a file set the tool then reads nothing from, and the sentence's literal
comes back **`missing`** — a red verdict whose message sends a reader to fix
the index's prose, when the thing to fix is a directory. The suite pins that
too, with the address present on disk in a file the glob cannot reach, so the
`False` is decidable as the glob having resolved to the wrong kind of thing.

## How each was checked

`ec/tools/test_check_capture_names.py` is new, 19 cases, collected by
`tools/run-tests.sh` by `find` with no wiring. Both refusals fire on a **scratch
root**, because nothing in the committed tree is non-conforming today and a
case over a conformant tree proves only that the tool runs.

- The two refusals are reported in **separate vocabularies**, asserted by
  checking that neither message contains the other's noun.
- The **declined alternative is pinned as a refusal** rather than left in
  prose: `power-mode-…-2026-09-23.csv` is out of reach, because the glob is
  `<date>-*`. A date in any position would be a different rule.
- A **lookalike year conforms** (`2026-99-99-`), because the prefix is a shape
  and not a calendar; a checker that went on to decide whether a named day
  exists would be answering a different question.
- `PREFIX` and `captures_for()`'s glob are asserted to **agree in both
  directions**, so the two readers of one rule cannot drift — the same argument
  `test_check_testdata_row_claims.py` makes about `files_for()` and
  `resolve()`.
- A root that **cannot be listed** is a broken census and exits non-zero,
  never three empty lists: "0 undated, 0 subdirectories" over a directory
  nobody read is a checker that passed by checking nothing, which is the
  `docs/findings.md` §14b defect `run-tests.sh` guards at the suite level.
- **The two costs, shown by running the code** rather than described: the
  cases above, against `captures_for()` and `carried_by()` themselves.

`ec/tools/test_check_testdata_row_claims.py` was 47 cases at the first merge's
base and is **53** on the merged tree.

- `test_the_block_and_its_denominator_name_the_root_the_run_was_given` is a
  **scratch** root holding one conforming and one unprefixed capture: the block
  names the scratch root, the denominator reads `1 of 2`, and the unprefixed
  file is **named on the line**. The root is asserted by its own unique
  directory rather than by `ec-watch`, because both roots end in that name and
  anything weaker would pass against a block still printing the committed one —
  which is the bug the `Result` field exists to fix.
- `test_the_dated_block_denominates_itself_in_the_capture_root` asserts the
  committed numerator is **0** and the denominator **non-zero, never `== 15`**.
  The numerator is the refusal: a capture that arrives without its date turns
  it red, which is what a refusal is for, and the cost is written down here
  rather than designed away. The denominator is deliberately not a figure —
  pinning `15` would turn every capture added afterwards into a failure, the
  same trade `docs/agent-pipeline.md` records against a floor.
- `test_a_capture_root_that_cannot_be_listed_is_reported_not_crashed_on` is the
  vacuity guard on the new line. `glob.glob()` answers an unreadable root with
  an empty list rather than an error, so a run pointed at a root that has moved
  reaches the denominator with a dated sentence that resolved to nothing; the
  line is then unreadable too, and it says so on stderr instead of printing a
  `0 of 0` that reads like a conformant root.

> **Correction: the plan stage's `was 42 cases and is 45` was true of the tree
> it measured and is true of neither figure on this one, so it is recorded here
> rather than edited out, per §4a-4d.** The plan took its count before the
> commit that took the suite to 47 landed beside this branch: `42` is the count
> on `26e970d5`, and `3e020cf4` — the first merge's `origin/main` tip and this
> branch's merge-base — carries 47 (its parent `368e9e52` is #982's
> addr-column change), which is the merge
> [`testdata-addr-column-claim.md`](testdata-addr-column-claim.md) (issue #975)
> reports as its own `42` → `47` at its `:194`. The two pages therefore agree on
> what each figure was: `42` is the count before #975 on both, and the three
> cases above are this branch's.
>
> **The pair is now `50` → `53` rather than `47` → `50`, because #979 landed
> beside this issue and added three of its own between the two merges** — the
> two-date-sentence cases, none of which is this issue's and none of which this
> page's three cases touch. Measured on the tree this lands on rather than
> carried: `git show origin/main:ec/tools/test_check_testdata_row_claims.py | grep -c 'def test_'`
> is **50** and `grep -c 'def test_' ec/tools/test_check_testdata_row_claims.py`
> is **53**, the same `53` `python3 test_check_testdata_row_claims.py` reports
> (`Ran 53 tests ... OK`). So three steps are now on record, each true of the
> tree it was measured on: `42` → `47` (#975), `47` → `50` (#979, on the other
> side of the merge from this issue's three), and `50` → `53` (this issue's
> three, on the merged tree). No case was rewritten, dropped or weakened to reach
> any figure — `git diff origin/main -- ec/tools/test_check_testdata_row_claims.py`
> removes no `def test_` line — and the count is the only thing here that was
> ever wrong. **The `47` → `50` this page carried through the first merge is
> true of neither tree and is superseded by the pair above**, per §4a-4d.
>
> **One case of those three needed an edit to survive the second merge, and it
> is named rather than left to be found.** This issue's
> `test_a_capture_no_date_can_reach_is_one_the_run_never_checks` unpacks
> `captures_for()`'s third return field as a single glob, which was its shape
> when this page was written. #979 changed that field to one `(glob, files)`
> pair per bare date a sentence carries, so a two-date sentence is refused with
> every glob named; the case now unpacks the pair and says so. **The case's
> claim is unchanged and the fix is to the unpacking, not to the assertion** —
> a sentence naming one date is still keyed by its own glob, which is the
> premise being demonstrated. It is the only edit this issue's suite needed, and
> `test_check_capture_names.py`'s 19 needed none: it reads the tool's two
> refusal vocabularies and the committed root's two tripwires, and #979 changed
> neither.

**The mutations, run.** Four wrong implementations were applied to
`check_capture_names.py` and four to `check_testdata_row_claims.py`, and the
suites were run over each, so the "can fail" claim is demonstrated rather than
asserted: a `PREFIX` that matches everything, a dropped directory refusal, a
`--check` that never fails, an unlistable root read as an empty one; and a
`dated_report()` printing the module-level `CAPTURES` again, the denominator
line dropped, the numerator reporting the count the run *reached* rather than
the count no glob can reach, and the unlistable-root guard removed. The third
of the second list is the one worth naming: it is the conflation this whole
section is about, and it is red.

## Not claimed here, and what this does not do

- **That any current capture is misnamed.** All 15 comply, and the two
  premises measured clean on the day this was written. The refusals describe
  what may be added, not a defect in the corpus.
- **That the glob has ever silently missed a file.** It has not, on this tree,
  and nothing here is evidence about a corpus that was not measured. A
  misnamed capture in an earlier commit would be a claim about history this
  branch has not walked.
- **That this would have caught #502 or #720.** Carried forward verbatim
  above; it belongs to `#747`/`#794` and not to this issue. Retired as a
  measurement by #978, which ran the checker over both pre-repair trees: 0
  `missing`, because the rows either repair touched carry no address claim to
  be wrong about.
- **That a date in a filename is a real day.** `20\d\d-\d\d-\d\d-` is a shape.
- **That a conforming file is a capture.** This reads a directory listing. It
  never opens a file, never reads a byte, and never runs a
  capture-producing tool. What one of these files *contains* is
  `check_capture_claims.py`'s and `check_capture_encoding.py`'s.
- **That every capture in the root is named by the index.** It is not, and
  requiring it would be wrong: the index describes the testdata fixtures, not
  the capture corpus. See the two questions above.
- **`captures_for()`'s resolution semantics.** Union over a date, no narrowing by
  a word in the prose — **unchanged by this issue, and re-stated here as
  unchanged by it.** The qualifier is the second merge's: #979 (issue #983)
  landed beside this one and changed the *shape* of what a sentence naming two
  or more bare dates is read against — refused whole rather than read from the
  first, with every glob named. **That is a different rule about a different
  question, and it is not this page's**: this page's is whether a *name* in the
  capture root is reachable by a `<date>-*` glob at all, and no sentence-shaped
  question can move it. The write-up is
  [`testdata-row-claims-multi-date-sentence.md`](testdata-row-claims-multi-date-sentence.md)
  and the summary is
  [`../findings.md`](../findings.md) §78. **A first-date-only reading is the
  thing #979 removed, so the phrasing "first bare date" that stood here is
  dropped rather than carried** — a sentence naming two dates is no longer read
  from either.
- **Editing the prose to match the rule.** `ec/tools/testdata/README.md:5-6`
  ("Real captures live in `../../../evidence/` and are dated with the day they
  were taken") and `evidence/README.md:65` (which spells the convention for a
  capture not yet taken) are **not touched**. They are the convention being
  held, not a defect to be corrected to match a tool; rewriting prose to make
  a checker green is the thing this repository forbids.
- **Renaming or moving any capture**, and `evidence/ec-watch/` growing or
  shrinking. The census describes the tree as it stands; the refusal describes
  what may be added.
- **The gate wiring.** `docs/ci/agent-gates-testdata-row-claims.patch` is
  unchanged — the tool's CLI is unchanged — and it remains a human's
  `git apply`. No new patch is written under `docs/ci/`, and no gate or
  workflow is wired by this branch.
- **`ec/README.md` and `tools/README.md`'s totals paragraph.** `ec/README.md`
  lists neither `check_testdata_index.py` nor `check_testdata_row_claims.py`,
  so the newest tools are not entered there; one row in a 27-entry shared list
  buys a merge conflict. The README's suite table gains its mandatory row, and
  **the totals paragraph is re-derived, because this time it had to be**: a new
  `test_*.py` moves the suite count, which is what that sentence says it is, so
  `tools/README.md` now reads **forty and 1233** where the merge's base read
  **thirty-nine and 1211**, and both figures are from
  `bash tools/run-tests.sh` on the merged tree rather than from adding two
  sides' numbers up. The superseded `1211` is left visible in the sentence's own
  parenthetical per §4a-4d, and the re-derivation is recorded as the file's
  twenty-third merged-tree note. **`docs/findings/tools-readme-totals.md` (issue
  #817) is what the paragraph means; the branch's own `thirty-eight … 1168` is
  not this tree's and never was after #982 landed in the base** — the first
  merge left that bullet alone for exactly the reason it gives, and the second
  merge has to correct it because the sentence it declines to touch had moved
  under it. `test_check_pin_table_by_cited_file.py`'s own indexed/unpinned pin
  is re-set to the measured **40 / 11 / 29** for the same reason and with the
  same "run the thing, do not add up" rule.
- **Live hardware, Windows, and the EC/BIOS/Windows stack.** Nothing here
  reads a register, opens a capture, or touches a firmware image. No `status:`
  moved, so `ec/annotations/registers.yaml` is not touched at all.
- **Anything in another repository.** No PR or issue is opened anywhere; the
  upstream work the mission eventually means is unaffected by this change.
