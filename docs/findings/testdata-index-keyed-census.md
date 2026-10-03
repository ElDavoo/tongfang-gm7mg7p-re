# The row-count refusal is gone: the census keys on the `File` cell, and three more edits come back (issue #1084)

The write-up for [issue
#1084](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1084), which asked
for a key so that a row addition would stop making the whole table unmeasurable.

**The answer: rows are matched over their first-column cells. Every revision a
positional comparison refused is now measured — three of them turn out to hold a
third-column edit that the refusal could not see, and the corpus's corrected
count of four hand-repairs is a subset of what is now measured rather than the
whole of it.** The nested population's one known edit moves out of `edited` and
is now a key that left beside a key that arrived, with **both cells printed** —
so the finding survives and the class no longer claims it was an edit.

```
$ python3 ec/tools/census_index_third_column_edits.py --census
...
47 revision(s) of 5 index(es): 7 edited, 19 one-sided, 0 refused, 16 unchanged, 5 unborn, 0 no-parent, 0 not-read-by-this-method
```

The same run on the same tree at `33cca5f9`, with the tool as it was before this
change, reads:

```
47 revision(s) of 5 index(es): 5 edited, 21 refused, 16 unchanged, 5 unborn, 0 no-parent, 0 not-read-by-this-method
```

**No revision changes class for any reason other than the row comparison.** Both
figures are per-ref and are published with the ref they were taken at, `33cca5f9`,
the tree this branch forks from; the population has itself grown since the census
write-up was written (three self-indexed directories under `ec/tools/testdata/`
are now committed, and they bring their own histories), so **the number to
compare against is the second line above, not any figure in the older
write-up.** The command is the same in both cases; only the tool's row
comparison changed. Read revision by revision:

  * the **`21 refused` become three `edited` records and eighteen `one-sided`
    ones** — the three are `4ceca374`, `17b7e332` and `c64825b9`, and each is a
    revision that grew the table *and* reworded a row both images carry;
  * the **`5 edited` become four**, #746 having moved out of the class for the
    reason below;
  * `16 unchanged` and `5 unborn` do not move at all.

**Nothing here is a live test and nothing is hardware evidence.** Every number is
read out of committed history and committed prose. No capture is opened, no EC,
no firmware image, no laptop, no Windows, and nothing was read off a machine.

## The key, in the tool's own words

The comparison lives in [`index_keyed_rows.py`](../../ec/tools/index_keyed_rows.py),
a new file beside the census rather than a fourth function inside it — CLAUDE.md's
rule, and the census is already long enough that a reader has to hold two things
to follow it. **A row's identity is its first cell**: `File` for the root index,
which is the cell `check_testdata_index.py` resolves every path a row names from,
and the backticked listing for a nested one. Rows are matched over the
**intersection** of the two key sets, and what is left over is reported as a row
present on one side only.

Three consequences are worth stating here rather than leaving a reader of a
transcript to work out:

  * **A revision that both edits a shared row and adds one is no longer
    unmeasurable.** The edit is found over the keys both images carry and the
    addition is reported beside it. That pair used to be one line saying the two
    were *not separable by this method*, which is what the refusal was for.
  * **A row present on one side only is not a refusal.** It is an answer: the
    tool knows which key moved, in which direction, and what the cell that exists
    says. Folding it into `unchanged` would claim the two images agree; folding it
    into `refused` would claim the method did not answer when it did. It is its
    own class, `one-sided`, counted like every other.
  * **No rename rule.** A removed key and an added key are **two rows**, each
    with the cell that exists. Pairing them is a judgement about which row became
    which, and a key is precisely what cannot make it — so a reader who wants the
    pairing makes it, from both cells printed.

**`refused` did not go away; it changed what it refuses.** It is now the class for
the cases a key cannot settle at all: a key repeated inside one image (a dict
would keep one row and drop the other, and the comparison would then be over a
row that was never there), an empty key cell (a blank key matches nothing on the
other side and every blank key matches every other one), and a row with no cell
in the column being read. Each is named and each says which of the three it is.
**None of the committed revisions falls in it**, and
`test_no_committed_revision_carries_a_key_the_reader_cannot_settle` holds that as
a property of the tree rather than as a count of it.

**Two refusals are delegated rather than reimplemented**, so there is one of each
and not two that could drift: an image the reader cannot locate is the census's
own `located()` guard, asked before the comparison runs, and a revision this
clone cannot resolve is the census's exit-2 branch, which reuses
`HISTORY_REQUIREMENT` verbatim. The silent zero this arrangement exists to
prevent is real and named — an image the reader cannot read yields an empty key
set, and two empty key sets compare equal — and
`test_the_reader_comparing_nothing_returns_an_empty_set_and_no_refusal` shows it
being produced rather than merely asserted against.

**A reorder is not an edit.** Two images carrying the same keys reading the same
are `unchanged` even if the column read in order is not byte-identical, because
the reader asks what each row says rather than where it sits. That is why the
`unchanged` reason now says **every row it shares with its first parent reads the
same**, and no longer claims byte-identity it does not check.

## The instrument

`ec/tools/index_keyed_rows.py` reads tables through `check_testdata_index`'s own
`table_cells()` and `markdown_tables()` — imported, not copied, for the reason the
census's own import comment gives: a second reader of the same table could come to
disagree with the tool it is measuring. `table_cells()` owns the rule for *which*
table is the root index's, so the root branch asks it rather than re-spelling that
test; only the nested branch, which has no such rule because it reads every table
in the file, reaches for `markdown_tables()` directly.

**No table key is needed for the nested population, and the reason is a check in
the tool rather than an assertion in a docstring.** A nested first-column cell is
unique across the whole file, which is what lets one file-level keyed comparison
stand in for both of the refusals the nested arm used to have — the whole-file
table-count change and the per-table row-count change — with no table identity at
all. **The duplicate-key guard is what makes that safe per image rather than
assumed**, and `test_every_committed_index_keys_are_unique_and_never_empty`
asserts it over every self-indexed index in the tree, so a new one needs no edit
here — the same argument `check_testdata_index.py`'s self-indexed clause makes.

**`measure_index_repair_visibility.repair_rows()` does not move, and neither does
its suite.** The issue says leave it and this leaves it. It measures a *named
pair* and refuses rather than aligns on purpose, because a row number there is a
position in both images; the census reads a *population*, so it keys instead.
Both refusals now stand side by side in the census's suite,
`test_images_with_different_row_counts_are_refused_not_aligned` beside
`test_the_keyed_comparison_reads_the_same_pair_instead_of_refusing_it`, over the
same two images. `test_measure_index_repair_visibility.py` is unchanged, and its
pinning of that refusal is the check that the alignment did not leak into the
shared reader.

## The three edits that were in the refusal

Of the root table's third-column edits, `944b1ce7`, `565b6f3c`, `8f4f211f` and
`a393229b` were already found. **Three more were inside revisions the positional
comparison refused**, and each was a revision that grew the table *and* reworded a
row both images carry — the exact case the old alignment could only decline:

| revision | row | the clause that moved |
|---|---|---|
| #457 `c64825b9` | root 17 | *"It is **the only** fixture with a void block in it, and so the one …"* → *"It is the three-value day §3's per-block integrity check and the grader's `--block` are **first read against**; `0751-isolation-run-void-block/` below is that same void condition in a one-block set"* |
| #1699 `17b7e332` | root 11 | *"the committed file opens with **three** [comment lines]"* → *"the committed file opens with **a `#` block**"* |
| #1732 `4ceca374` | root 23 | *"byte for byte in the `0x0700` **and `0x0400`** captures"* → *"byte for byte in the `0x0700` capture"* |

**`c64825b9` is the one that is interesting, and it is interesting because the
revision caused the staleness itself.** The row it edited, `3blocks/`, was not
touched by it; what the revision did was **add** `0751-isolation-run-void-block/`,
a second fixture with a void block in it — which made "it is the only fixture
with a void block in it" false, and the edit is the correction. This is a shape
no positional or keyed comparison can be *told* about; it is only visible by
reading the cell beside what the revision did, and it is here because the census
reached the revision at all.

## The criterion applied, per revision

[`testdata-index-repair-census.md`](testdata-index-repair-census.md)'s criterion,
in its own words and unchanged: **a hand-repair is an edit to a description cell
at a revision that changed no fixture the row names**; a routine edit is one at a
revision that did, where the cell followed the bytes. It is applied **per edited
cell**, and the evidence is one command per revision:

```
$ git show --stat --format= c64825b9 17b7e332 4ceca374 -- ec/tools/testdata/
```

**All three are hand-repairs, and the reason is not the same for each — which is
why the evidence has to be read rather than assumed.**

  * **#457 `c64825b9`, root 17, `0751-isolation-run-3blocks/*.csv`.** The
    revision did not touch that fixture at all; it added a *different* one.
  * **#1699 `17b7e332`, root 11, `capture-claims-example-ac-plugin-sweep-summary.csv`.**
    The revision did touch that fixture, and the cell edit follows from it
    exactly: the fixture's own `#` block said "the committed file opens with
    three of them", and at this revision the **evidence** file it describes went
    from three leading comment lines to thirteen, so the cell's "three" became
    false and was corrected to "a `#` block". The fixture's comment moved in
    lockstep with the cell — `git show 17b7e332 -- ec/tools/testdata/capture-claims-example-ac-plugin-sweep-summary.csv`
    shows the same sentence changing in both. **On the criterion as stated this is
    a hand-repair**, because what was wrong was the sentence and the cell was
    corrected by hand alongside the fixture rather than generated from it.
  * **#1732 `4ceca374`, root 23, `0751-isolation-run-missing-mark/*.csv`.** This
    one is **not** this revision's doing at all, which is the most interesting
    thing in this section. The cell claimed the fixture was "byte for byte in the
    `0x0700` and `0x0400` captures". That was true when `c64825b9` wrote it and
    **stopped being true at `5ad88d8d`**, which changed
    `0751-isolation-run/2026-01-01-0751-isolation-0400-045f.csv`'s
    `0x0402` context row into a `0x0438` battery row — a change to *the other*
    fixture the sentence compares against, which made the two stop matching. The
    cell was then wrong for **159 commits** before `4ceca374` corrected it
    (`git rev-list --count 5ad88d8d..4ceca374^`), and at that revision the row's
    own fixture changed nothing but its comment header.
    So the criterion's fixture test says the revision changed the row's fixture,
    and the *reason* the cell was wrong was a different revision entirely. **A
    reader who applies the criterion mechanically gets "routine" here and is
    wrong about the mechanism**, which is the reason this section states the
    mechanism rather than the verdict alone.

**So every one of the seven root third-column edits this alignment finds lands
on the criterion's hand-repair branch** — #182, #502, #720, #736 and the three
above — and **the corpus's corrected count of four is a subset of what is now
measured rather than a contradiction of it.** On two of the three, applying the
criterion's fixture test mechanically gives the wrong mechanism: on #1699 the
revision *did* change the row's own fixture, so the test answers "routine", and
on #1732 it did too — while the cell was not wrong because of that revision at
all. **What the three share is that the sentence was what had to be corrected**,
which is the criterion's stated reason rather than its shortcut, and it is why
each is argued above rather than tabulated.

**What is not claimed: that this is now the whole population.** Two limits, both
inherent to the method rather than to this tree:

  * **A keyed comparison can still miss a cell that changed in the same revision
    as a row addition *and* a reword of the added row**, because the added row's
    own cell is on neither side of the intersection as a shared key. That is a
    narrower miss than the one it replaces — the old method missed *every* shared
    row at such a revision — but it is not a zero. The honest phrasing of the
    result is **no edit found under this alignment**, not *no edit*.
  * **The nested population's edits are no longer reported as edits at all.** A
    nested row's measured cell *is* its key, so a repointed pointer is by
    construction a key that left and a key that arrived. #746 is still in the
    report with **both cells printed**, which is the evidence, but a reader
    looking for `edited` records in the nested population will find none and
    should read the `one-sided` ones instead. **This is a real loss of
    convenience and not of information**, and it is the price of keying this
    population on its only identifying column.

## What the corpus changes

**`docs/findings.md` §92 and `testdata-index-repair-census.md` are corrected in
place**, per §4a-4d, with the superseded wording left visible beside each: the
census write-up's lead figure, its committed transcript, its "fourteen revisions
are counted on neither side" limit, and its "Left open" bullet that named this
issue.

**The sites that carry the sentence "twice" or "four" are not restated** —
[`testdata-index-repair-census.md`](testdata-index-repair-census.md)'s "What the
corpus changes" table is the enumeration of them. On this result the count they
already hold is a **subset** of what is now measured rather than a contradiction
of it, and editing that many files to restate an unchanged figure is the
correction-chain shape `ec/tools/check_no_append_logs.py` exists to stop. **What
moves is stated in one place — here — and both older documents point at it.**

## The test

`ec/tools/test_index_keyed_rows.py`, new, discovered by `bash tools/run-tests.sh`
by `find` the moment it is committed, with no wiring: a suite describes itself in
its own docstring and there is no shared table to add a row to. What it pins is
the four ways a keyed comparison can be wrong quietly — the reader comparing
nothing, a refusal read as an answer, a key read as a rename, and a guard that is
not one — plus the properties of the committed images the file-level nested
comparison rests on. **Never how many**: a count over a population moves on the
day a row is added, and a case that pinned one would fail then and say the reader
broke.

`ec/tools/test_census_index_third_column_edits.py` is **revised rather than
deleted**, per the issue's own instruction and the repository's: the refusal
cases are rewritten for the classes that replaced them, `repair_rows()`'s own
refusal stays (it is about that tool, and this is not its change), and new
scratch-repository cases cover a row addition landing in `one-sided` with the
other rows still read, a growth that also edited a shared row, a first-column-only
and a `Feeds`-only commit, and a nested pointer change printing both cells. Its
committed-history class now asserts that a **named** formerly-refused revision is
read over its shared keys rather than refused, and that no committed revision
carries a key the reader cannot settle — again a property, never a census.

**The load-bearing guards were checked by mutation rather than by reading the
suites green.** In `index_keyed_rows.py`: dropping the duplicate-key guard,
dropping the empty-key guard, dropping the root short-row length check, and
treating a key missing from one image as an unchanged row each turned the new
suite red. In the census: folding `one-sided` into `unchanged`, folding it into
`refused`, dropping the one-sided rows from an `edited` record, and dropping the
`located()` guard each turned the census suite red. Restoring each turned it green.

## Left open, for the follow-up pass

  * **The corpus's "hand-repaired four times" is now a subset of what is
    measured, and the sites carrying it are left as they are.** The decision
    taken here is that the extra findings live in this write-up and the existing
    sentences stay, on the grounds that restating an unchanged figure across the
    enumeration is the correction-chain shape the repository has been bitten by
    twice. **A reader who disagrees has a concrete disagreement to have**: the
    sentence is no longer the whole truth, and whether it should name the three
    edits above is a question about those sentences rather than about the census.
  * **A cell that changed in the same revision as a row addition *and* a reword
    of the added row** is still not found by this method. Narrower than what it
    replaces, and named above rather than left to a reader to assume away.
  * **Whether the nested population should have its own key.** Its first column is
    its identity, so keying on it means pointer changes cannot be reported as
    edits. A table key would restore that at the cost of the file-level
    comparison the duplicate-key guard currently makes safe; nothing here says
    which trade is right.
  * **A fixture a cell names changing without the cell's revision being where the
    sentence goes stale** — #1732's shape, where a *different* fixture's bytes
    moved and this cell's claim quietly became false 160 commits before anyone
    corrected it. `check_testdata_row_claims.py` holds claims to the files a row
    names, but nothing holds a cell that compares two fixtures to both of them.