# How many edits the testdata index's third column has held (issue #1008)

The write-up for [issue
#1008](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1008), which
asked the question the corpus had been answering with a measurement of a pair.

**The answer, measured over the whole history rather than over a named pair:
`ec/tools/testdata/README.md`'s third column has held **four** edits — in #182,
#502, #720 and #736 — and the one nested index under it has held **one**, in its
**first** column, in #746. The corpus said "twice".**

```
$ python3 ec/tools/census_index_third_column_edits.py --census
...
33 revision(s) of 2 index(es): 5 edited, 14 refused, 12 unchanged, 2 unborn, 0 no-parent, 0 not-read-by-this-method
```

*(Corrected 2026-10-03, issue #1084: the run above no longer reproduces, because
the census now matches rows over their first-column cells rather than by
position. On the tree at `33cca5f9` the same command reads **`47 revision(s) of
5 index(es): 7 edited, 19 one-sided, 0 refused, 16 unchanged, 5 unborn, 0
no-parent, 0 not-read-by-this-method`** — `refused` has become `one-sided`, and
**three more third-column edits have come out of it.** The population has grown
too (three self-indexed directories under `ec/tools/testdata/` are now
committed), so the run above is not comparable to it figure for figure and is
left as the record of the tree it was taken on.
[`testdata-index-keyed-census.md`](testdata-index-keyed-census.md) is the write-up
for that change and carries both measurements side by side. The lead figure above
is superseded in the same way and stays written, true of the tree it was measured
on, per §4a-4d.)*

**The `33` is a per-ref figure and is published with the ref it was taken at:
`0daac768`, the same 33 `origin/main` holds.** The tree this write-up lands in
holds **34**, and the extra record is this PR's own commit editing the paragraph
*below* `testdata/README.md`'s table — a revision of the root index, which the
census classes `unchanged`, so the same run reads `13 unchanged` there. A reader
re-running the command on the merged tree is expected to see that, and
`5 edited` / `14 refused` are the figures that do not move. **The `33` is
re-measured on the `#1008` × `#1032` × `#1033` tree and does not move there
either**: `origin/main` at `48887fa0` reads `33 revision(s) of 2 index(es): 5
edited, 14 refused, 12 unchanged, 2 unborn, 0 no-parent, 0
not-read-by-this-method`, and so does this tree, because `main` committed no
revision of either index in the three windows after the branch forked. The
`0daac768` stays named because it is the ref the figure was taken at, and the
two agree, which is the check a per-ref figure is published with rather than a
coincidence worth nothing.

**The superseded wording is left here rather than only in the corrections,
because the count was in **twenty sites across fifteen files** and a retraction
whose wrong version lives only in a git log is one a reader cannot check.** It
read, in `check_testdata_index.py` and in `docs/findings.md` §41 and §81 among
others:

> The index has needed a hand-repair twice, in #502 and #720.

**This page published that figure wrongly first, and the wrong version is left
here rather than edited out, because the error is the one this page is
about.** It said *"ten files at twelve sites"*, carried over from the issue's
list of eight rather than enumerated. Review re-counted the population over
the base tree, found the figure wrong **on this repository**, and found the
sweep incomplete: **seven of the twenty sites were still uncorrected** — the
paragraph one above the item 10 this page did correct, two prepared patches
under `docs/ci/`, and three `#747` disclaimer blocks propagated across
`docs/findings/`. **The number moves in files nobody enumerated, which is what
a census is for; the first pass was the ninth propagation, not the last.**

**The population is a hand-checked table, and the figure is derived from it**,
which is the only arrangement in which the two cannot drift apart. A
mechanical search cannot do this job and is not offered as if it could: it
cannot tell a population claim from the many unrelated senses of "twice" in
this tree — CSV de-duplication, `len(d)` tested twice, a pin that has moved
twice — and it **misses a site whose claim wraps across a line break**, which
is how three of the seven read. The command that produces the candidate set
the table is checked against, and no more than that:

```
$ git grep -n -iE 'twice|both (of the index.s )?(past )?hand-repairs|both repairs|two hand-repairs|those two repairs' f6480168 -- '*.md' '*.py' '*.patch'
```

A reader who disbelieves a row of the table can re-derive it from that
output. A reader who wants the population should re-read the table rather
than take the number off it.

**Why the count itself was wrong, and it is not that anybody miscounted.**
[`testdata-row-claims-repair-measurement.md`](testdata-row-claims-repair-measurement.md)
measured the two repairs it was asked about, and that measurement was correct.
The error is one of population: `measure_index_repair_visibility.py` takes
`--base`/`--repair`, the two shas came from `git log --format=%s` on the
`(#502)` and `(#720)` subjects, and **the number the merge published was that
pair's size.** Nobody had asked how many third-column edits the history holds at
all, so a measurement of two became a claim about a population and was carried
as settled fact in **twenty sites across fifteen files** — and the merge that
retired the "nobody has looked" disclaimer around it propagated it to three
more, which is why three of the seven uncorrected sites are `#747` blocks this
page had every reason to have read.

**The three findings below are what a census over the population turned up, and
none of them is "there are two more repairs".** They are: a silent zero the
instrument would have printed over the nested index; a **column** the population
is measured in that the issue had named wrongly; and a criterion separating a
repair from a routine edit that the tool deliberately does not apply.

**Nothing here is a live test, and nothing is hardware evidence.** Every number
is read out of committed history and committed prose. No capture is opened, no
EC, no firmware image, no laptop, no Windows, and nothing was read off a
machine.

## The instrument

`ec/tools/census_index_third_column_edits.py`, a new file, beside #978's rather
than as a mode on it — CLAUDE.md's rule, "a new tool is a new file, not another
mode bolted onto an existing one" — and that also keeps a recent tool out of this
diff while several agent PRs are open. `--census` is the entry point and the
only mode; there is no `--check`, because a census renders no verdict.

**It reuses, and reimplements nothing.** `repair_rows`, `git_lines`,
`resolve_revision`, `parent` and `subject` are imported from
`measure_index_repair_visibility`, and `table_cells`, `markdown_tables` and
`HEADER` from `check_testdata_index` — the sibling's own readers, so a change to
what a table is lands in one place. `HISTORY_REQUIREMENT` is reused verbatim so
the two tools cannot disagree about what a clone has to be to answer.

**No extraction.** #978 extracts each revision's `ec/tools` into a scratch tree
because it has to *run* the checkers over the old one. This compares **texts**,
so two `git show <rev>:<path>` per revision is the whole of it — no `git
archive`, no `tarfile`, no scratch tree, none of the `PATHS` decision #978 had
to reason about. That is also why it does not inherit #978's direction limit:
neither tool runs a checker over an old tree, so the "today's rules over
yesterday's prose" caveat does not apply here at all.

**The population is discovered, not listed.** `git log --diff-filter=A
--name-only -- ':(glob)ec/tools/testdata/**/README.md'` finds every index this
repository has ever committed under the testdata root, **including one that has
since been deleted** — a walk of the working tree or of `HEAD` would miss that
one, and a missing index is not a zero, it is a census that looked at half a
tree. The `:(glob)` magic is load-bearing and the plain spelling is not:
`ec/tools/testdata/**/README.md` without it matches `call-graph/README.md` and
**not** the root index itself, which would have published a count over the
nested population as a count over the root.

## Two findings that changed the design

### 1. A third-column census over the nested index prints a clean, wrong zero

`check_testdata_index.table_cells(index, column=3)`
([`check_testdata_index.py`](../../ec/tools/check_testdata_index.py), cited by
name and not by line — a line number here would be one more thing a later edit
moves silently, which is what `test-line-pin-census.md` is about)
returns rows only from a table whose first header cell is `HEADER` — `File`.
The committed nested tables are headed `file / row`, so the reader returns `[]`
for the whole file, and:

| file | tables | `table_cells` col 1 / 2 / 3 |
|---|---|---|
| `testdata/README.md` | 1 (`File`, `Feeds`, `What it constructs`) | 27 / 27 / 27 |
| `testdata/call-graph/README.md` | 3 (`file / row`, `what it pins`) | **0 / 0 / 0** |

`repair_rows()` over a pair of those images compares two empty lists, finds the
lengths equal and reports no third-column difference. That is precisely the
failure its own docstring names — *"a comparison that compared nothing looks
exactly like one that found no difference"* — and it is the committed tree's
own instance of it, not a hypothetical.

So **an image the reader cannot locate is reported as `not read by this
method`, never as "no edits"**, and that is a test case rather than a comment:
`test_a_nested_index_read_as_a_root_one_is_unreadable_not_silent` builds a
nested-shaped file *at the root index's own path*, so the population selects the
third-column reader and the shape check is the only thing between that and a
clean "no edit" over a file carrying tables.

### 2. The #746 repair is a **first-column** repair, and the issue said third

The issue calls it *"a hand-repair of a description cell the new detector is
structurally blind to"*. The cell is in **column 1**:
[`nested_index()`](../../ec/tools/check_testdata_index.py) reads column 1 of
every data row of every table, and its own docstring says why — *"the second
column is prose about the case and the third is a long explanation of it, and a
token lifted out of either would be a pointer the index never made."*

The nested tables are two columns wide, `file / row | what it pins`, and the
repaired cell is a **path**:

```
| `decompiled/common/0EA2.asm` | the issue's worked example: 2 `lcall`s to 0x0EE8, and a 2-byte `ajmp` to 0x5A43 |
```

→ `` `decompiled/bank0/0EA2.asm` `` at `call-graph/README.md:16`, and the
tracked listing is `bank0`. **It is the very cell `check_testdata_index.py`
reports as `nested_missing`** — #978's control found it as the single non-zero
over all four of its runs, and `testdata-row-claims-repair-measurement.md`
records it as already found and fixed.

**This does not weaken the issue; it sharpens what has to be measured.** A
third-column census is the wrong instrument for `call-graph/README.md` *by
construction*, so the tool runs **two differently-shaped measurements** — the
third column of the root index, the pointer column of each nested one — and the
reconciliation is stated **per population**. This is the most likely reason
"twice" survives as a true sentence about the root index while ceasing to be a
true sentence about the tree.

## The measurement

`python3 ec/tools/census_index_third_column_edits.py --census`, on a full clone
at `0daac768`, verbatim and complete:

```
$ python3 ec/tools/census_index_third_column_edits.py --census
population, from `git log --diff-filter=A --name-only -- ':(glob)ec/tools/testdata/**/README.md'`: 2 index(es) ever added under ec/tools/testdata/
  ec/tools/testdata/README.md -- read in its third column, the description
  ec/tools/testdata/call-graph/README.md -- read in its first column, the path a row names

edited, third column, the description -- ec/tools/testdata/README.md
  a393229bcfad558205964bdea123ce80bb208204 -- scope the movement line on a run with a graded window in no block (#736)
    row 23 -- `0751-isolation-run-unplaced-window/*.csv`
      before: The same two-value day as `multi-block/`, with **two `restore` marks
              in no block** — one before the first block and one between the two.
              Nothing else is wrong: every mark is in every capture and spelled
              the same way in all three, and both blocks are intact, so this set
              is not here to be refused. It is the fixture for `--block` selecting
              a block's *own* windows, and unscoped for the closing section's
              fourth case: the only committed run that reaches the `elif
              graded_unplaced:` branch, and so the only one to print
              `UNPLACED_GRADED_NOTE` at `2 of the 8` *with* that branch's sentence
              under it — `unread-window/` below prints the same note and takes the
              withheld branch above it instead. `assign_blocks` leaves a window it
              could not place in the same list, so a `--block` run that took a
              range the length of the blocks ahead of it ran short by whichever of
              these came first — printing one in the block's place, dropping the
              block's own restore, and still calling the block `intact`. The two
              leftovers are one in each position so both blocks are held to the
              same promise the census makes of them (`--block` cannot select a
              window in no block); the stray at the front holds the first
              temperature row, so it is a window with real bytes in it and not a
              quiet one. The two roles are one set of bytes rather than two, and a
              `--block 0xA0` run over it is what shows why: the per-block sentence
              prints, the count line and `UNREAD_MARK_NOTE` do not, exit 0. That
              is structural rather than guarded — a `--block` run's `shown` is
              that block's own windows, and a window in no block cannot be one —
              which is why the branch is placed where a `--block` run cannot reach
              it at all. See `docs/findings/0751-grader-unplaced-window-scope.md`.
              It is *not* a prediction that a restore is ever typed with no block
              open.
      after:  The same two-value day as `multi-block/`, with **two `restore` marks
              in no block** — one before the first block and one between the two.
              Nothing else is wrong: every mark is in every capture and spelled
              the same way in all three, and both blocks are intact, so this set
              is not here to be refused. It is the fixture for `--block` selecting
              a block's *own* windows, and unscoped for the closing section's
              fourth case: the only committed run that reaches the `elif
              graded_unplaced:` branch of the **no-movement** chain, and so the
              only one to print `UNPLACED_GRADED_NOTE` at `2 of the 8` *with* that
              branch's sentence under it — `unread-window/` below prints the same
              note and takes the withheld branch above it instead, and the
              `moved_groups` chain's own `elif graded_unplaced:` arm — see
              `docs/findings/0751-grader-moved-unplaced-scope.md` — is reached
              only over a copy of this set with one `0x0784` row added, not by a
              committed run. `assign_blocks` leaves a window it could not place in
              the same list, so a `--block` run that took a range the length of
              the blocks ahead of it ran short by whichever of these came first —
              printing one in the block's place, dropping the block's own restore,
              and still calling the block `intact`. The two leftovers are one in
              each position so both blocks are held to the same promise the census
              makes of them (`--block` cannot select a window in no block); the
              stray at the front holds the first temperature row, so it is a
              window with real bytes in it and not a quiet one. The two roles are
              one set of bytes rather than two, and a `--block 0xA0` run over it
              is what shows why: the per-block sentence prints, the count line and
              `UNREAD_MARK_NOTE` do not, exit 0. That is structural rather than
              guarded — a `--block` run's `shown` is that block's own windows, and
              a window in no block cannot be one — which is why the branch is
              placed where a `--block` run cannot reach it at all. See
              `docs/findings/0751-grader-unplaced-window-scope.md`. It is *not* a
              prediction that a restore is ever typed with no block open.

edited, third column, the description -- ec/tools/testdata/README.md
  8f4f211f2171e8a1ab2491eb56340f85eea4fbc9 -- name the no-block closing case in the two 0751 testdata entries (#720)
    row 23 -- `0751-isolation-run-unplaced-window/*.csv`
      before: The same two-value day as `multi-block/`, with **two `restore` marks
              in no block** — one before the first block and one between the two.
              Nothing else is wrong: every mark is in every capture and spelled
              the same way in all three, and both blocks are intact, so this set
              is not here to be refused. It is the fixture for `--block` selecting
              a block's *own* windows. `assign_blocks` leaves a window it could
              not place in the same list, so a `--block` run that took a range the
              length of the blocks ahead of it ran short by whichever of these
              came first — printing one in the block's place, dropping the block's
              own restore, and still calling the block `intact`. The two leftovers
              are one in each position so both blocks are held to the same promise
              the census makes of them (`--block` cannot select a window in no
              block); the stray at the front holds the first temperature row, so
              it is a window with real bytes in it and not a quiet one. It is
              *not* a prediction that a restore is ever typed with no block open.
      after:  The same two-value day as `multi-block/`, with **two `restore` marks
              in no block** — one before the first block and one between the two.
              Nothing else is wrong: every mark is in every capture and spelled
              the same way in all three, and both blocks are intact, so this set
              is not here to be refused. It is the fixture for `--block` selecting
              a block's *own* windows, and unscoped for the closing section's
              fourth case: the only committed run that reaches the `elif
              graded_unplaced:` branch, and so the only one to print
              `UNPLACED_GRADED_NOTE` at `2 of the 8` *with* that branch's sentence
              under it — `unread-window/` below prints the same note and takes the
              withheld branch above it instead. `assign_blocks` leaves a window it
              could not place in the same list, so a `--block` run that took a
              range the length of the blocks ahead of it ran short by whichever of
              these came first — printing one in the block's place, dropping the
              block's own restore, and still calling the block `intact`. The two
              leftovers are one in each position so both blocks are held to the
              same promise the census makes of them (`--block` cannot select a
              window in no block); the stray at the front holds the first
              temperature row, so it is a window with real bytes in it and not a
              quiet one. The two roles are one set of bytes rather than two, and a
              `--block 0xA0` run over it is what shows why: the per-block sentence
              prints, the count line and `UNREAD_MARK_NOTE` do not, exit 0. That
              is structural rather than guarded — a `--block` run's `shown` is
              that block's own windows, and a window in no block cannot be one —
              which is why the branch is placed where a `--block` run cannot reach
              it at all. See `docs/findings/0751-grader-unplaced-window-scope.md`.
              It is *not* a prediction that a restore is ever typed with no block
              open.
    row 24 -- `0751-isolation-run-unread-window/*.csv`
      before: `0751-isolation-run-unplaced-window/` **byte for byte, with one mark
              relabelled** — the first of its two block-less restores reads
              `'restored it somehow'` in all three captures, a form §6 does not
              fix. The label is the only variable, and the two windows in no block
              differ in exactly that: the 12:04 restore still parses and is graded
              under `block: unplaced`, the 12:00 one is refused. Both blocks are
              intact, so this withholds 1 window of 8 and grades 7 — the *other*
              reason a run is partly graded, and the one whose withheld window is
              in no block at all. It is here because the closing summary a
              withheld run prints has to hold for both reasons a window is
              withheld, and only the mark-set one was covered: a window refused
              for an unreadable label belongs to no block, which the same run's
              census says in as many words, so a closing sentence about a *block*
              this report refused to read is a §7 fact the output denies. It is
              also the fixture holding **both** kinds of window in no block at
              once, which is the property both ways of scoping an unreadable label
              rest on: `--block` can select neither the refused 12:00 window nor
              the graded 12:04 one, so a `--block 0xA0` run of this set prints
              that block's three windows, `intact`, and exits 1 without having
              printed or withheld either stray — and `unplaced-window/`, the same
              day byte for byte with that one label made readable, exits 0. See
              `docs/findings/0751-grader-block-scoping.md`. It is *not* a
              prediction that a mark is ever mistyped, nor that a re-run of a two-
              value day will hold a window in no block.
      after:  `0751-isolation-run-unplaced-window/` **byte for byte, with one mark
              relabelled** — the first of its two block-less restores reads
              `'restored it somehow'` in all three captures, a form §6 does not
              fix. The label is the only variable, and the two windows in no block
              differ in exactly that: the 12:04 restore still parses and is graded
              under `block: unplaced`, the 12:00 one is refused. Both blocks are
              intact, so this withholds 1 window of 8 and grades 7 — the *other*
              reason a run is partly graded, and the one whose withheld window is
              in no block at all. It is here because the closing summary a
              withheld run prints has to hold for both reasons a window is
              withheld, and only the mark-set one was covered: a window refused
              for an unreadable label belongs to no block, which the same run's
              census says in as many words, so a closing sentence about a *block*
              this report refused to read is a §7 fact the output denies. It is
              also the fixture holding **both** kinds of window in no block at
              once, which is the property both ways of scoping an unreadable label
              rest on: `--block` can select neither the refused 12:00 window nor
              the graded 12:04 one, so a `--block 0xA0` run of this set prints
              that block's three windows, `intact`, and exits 1 without having
              printed or withheld either stray — and `unplaced-window/`, the same
              day byte for byte with that one label made readable, exits 0. See
              `docs/findings/0751-grader-block-scoping.md`. It is also the only
              committed run where a withheld window and a graded window in no
              block hold at once, and the only one whose two counts are taken over
              different denominators — the withheld banner's `1 of the 8` against
              the count line's `1 of the 7` — which is what makes it the run that
              can tell where the count is taken: on `unplaced-window/` above the
              two coincide, so a count taken over `shown` rather than at the print
              point would print the same `2 of the 8` there. See
              `docs/findings/0751-grader-unplaced-window-scope.md`. It is *not* a
              prediction that a mark is ever mistyped, nor that a re-run of a two-
              value day will hold a window in no block.

edited, third column, the description -- ec/tools/testdata/README.md
  565b6f3cc6b7739e0d9b4081327d2c41f05d2a7c -- say in the closing summary why an unreadable mark refuses a --block run (#502)
    row 24 -- `0751-isolation-run-unread-window/*.csv`
      before: `0751-isolation-run-unplaced-window/` **byte for byte, with one mark
              relabelled** — the first of its two block-less restores reads
              `'restored it somehow'` in all three captures, a form §6 does not
              fix. The label is the only variable, and the two windows in no block
              differ in exactly that: the 12:04 restore still parses and is graded
              under `block: unplaced`, the 12:00 one is refused. Both blocks are
              intact, so this withholds 1 window of 8 and grades 7 — the *other*
              reason a run is partly graded, and the one whose withheld window is
              in no block at all. It is here because the closing summary a
              withheld run prints has to hold for both reasons a window is
              withheld, and only the mark-set one was covered: a window refused
              for an unreadable label belongs to no block, which the same run's
              census says in as many words, so a closing sentence about a *block*
              this report refused to read is a §7 fact the output denies. It is
              *not* a prediction that a mark is ever mistyped, nor that a re-run
              of a two-value day will hold a window in no block.
      after:  `0751-isolation-run-unplaced-window/` **byte for byte, with one mark
              relabelled** — the first of its two block-less restores reads
              `'restored it somehow'` in all three captures, a form §6 does not
              fix. The label is the only variable, and the two windows in no block
              differ in exactly that: the 12:04 restore still parses and is graded
              under `block: unplaced`, the 12:00 one is refused. Both blocks are
              intact, so this withholds 1 window of 8 and grades 7 — the *other*
              reason a run is partly graded, and the one whose withheld window is
              in no block at all. It is here because the closing summary a
              withheld run prints has to hold for both reasons a window is
              withheld, and only the mark-set one was covered: a window refused
              for an unreadable label belongs to no block, which the same run's
              census says in as many words, so a closing sentence about a *block*
              this report refused to read is a §7 fact the output denies. It is
              also the fixture holding **both** kinds of window in no block at
              once, which is the property both ways of scoping an unreadable label
              rest on: `--block` can select neither the refused 12:00 window nor
              the graded 12:04 one, so a `--block 0xA0` run of this set prints
              that block's three windows, `intact`, and exits 1 without having
              printed or withheld either stray — and `unplaced-window/`, the same
              day byte for byte with that one label made readable, exits 0. See
              `docs/findings/0751-grader-block-scoping.md`. It is *not* a
              prediction that a mark is ever mistyped, nor that a re-run of a two-
              value day will hold a window in no block.

edited, third column, the description -- ec/tools/testdata/README.md
  944b1ce701415e415a6211f71726759bbc49642e -- report total movement beside the window net, and print every context byte (#182)
    row 4 -- `0751-isolation-example-multi-move-0400-045f.csv`
      before: The temperature half of the same three marks, in a shape the pair
              above does not have: `CPU_TEMP` climbs two steps and then comes back
              down one inside the control window, so its first→last (`+1`)
              understates the three changes behind it and a window summary's
              endpoints and change count say different things. It is read
              alongside `...-fixed-load-0700-07ff.csv` above and was written to
              match that file's marks; the two are fixtures, not a run. It is
              *not* a prediction that a die will wander like that.
      after:  The temperature half of the same three marks, in a shape the pair
              above does not have: `CPU_TEMP` climbs two steps and then comes back
              down one inside the control window, so its net (`+1`) and its total
              movement (`3`) disagree where the write window's (`+3`, `3`) do not.
              It is the fixture §4.4's choice of figure is argued from — the two
              arms moved identically, and only the net makes the write look like
              it moved three times as far. It is read alongside `...-fixed-
              load-0700-07ff.csv` above and was written to match that file's
              marks; the two are fixtures, not a run. It is *not* a prediction
              that a die will wander like that.

edited, first column, the path a row names -- ec/tools/testdata/call-graph/README.md
  1813fe98798fef5b53318822f3ca5c262f4deb9a -- implement issue #746 (#779)
    table 1, row 2 -- `decompiled/common/0EA2.asm`
      before: `decompiled/common/0EA2.asm`
      after:  `decompiled/bank0/0EA2.asm`

33 revision(s) of 2 index(es): 5 edited, 14 refused, 12 unchanged, 2 unborn, 0 no-parent, 0 not-read-by-this-method
  unchanged, third column, the description -- ec/tools/testdata/README.md
    99c0193871243abddc77f52ae2bfe9d73ad96e90 -- the two index hand-repairs are measured, and the third column's checker is green over both pre-repair trees because the repaired rows spell no addresses (#1002)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    c83cf3b368347614e96540eca13be37c39d2f25c -- the fixture CSVs' `evidence` column is a pointer direction nothing read, and the eight cells naming a listing the real tree does not have are emptied (#943)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    abfe76e6759f7acbeec1cf2287d683f2af820b90 -- a two-date sentence is passed over with both dates named, rather than held to the first date's captures (#983)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    26e970d517c17ddc094369741af991d0ebfd1818 -- a bare date in the testdata index's third column now names the capture to check, instead of exempting the sentence (#964)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    8b76c9658df9b9eb40f4754a5512af204db3dd95 -- hold the testdata index's third column to the fixtures each row names (#783)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    1813fe98798fef5b53318822f3ca5c262f4deb9a -- implement issue #746 (#779)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    33870410b6a190ba007367126c74069be333e5f2 -- the prepared gate patches compose, and a test says so (#755)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    677dad9884086f794238f82130bdf305eccab069 -- hold the testdata index to the tree under it, and prepare the gate wiring (#737)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 26 and 27 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    619afcb28ecd69ee8d08b4cb26dbb5e4c63588b5 -- implement issue #472 (#638)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 25 and 26 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    004ad3d7da101ef91ea36b7f5e8da5bcdb6eda8e -- withhold a window in no block when the three consoles do not agree on it (#529) (#537)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 24 and 25 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    4ea4f477df0f438732e9acc7288519605401952f -- carry a refused block's verdict on the dumps and dump pairs read for it (#507)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 22 and 24 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    3ca25719a10a9d062502c2fbc74cb40574df3e83 -- scope the 0751 grader's closing summary to the windows it graded (#486)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 17 and 22 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    c64825b9b73fd632ec9d93f46c38fb0caa7d47aa -- check a block's marks before printing its windows (#169) (#457)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 16 and 17 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    7669537acf800abc70c044d10b1d83598616c904 -- implement issue #167 (#447)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 10 and 16 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    99b9495946a2d97548cd7331a3fb74624c3b6316 -- PR #303 rebuilt on main with the merge conflict resolved (#303)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 8 and 10 table rows, so a row number names a different row
      in each; the third-column edits are not found by this method
    513075b880b06372c43bbcab3807a42ed2d208c0 -- hold prose claims about an ec-watch capture to the capture file they name (#309)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 4 and 8 table rows, so a row number names a different row in
      each; the third-column edits are not found by this method
    41ea3b8d36a8082d5ea6a3eb8144384ca59eb581 -- keep the host-written fan-table trigger out of the grader's §4.2 bucket, and give the moved branch a fixture (#210)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    ac0ec5aaca277b654c7f8d133617fd8102a0588b -- name the 0751 grader's uncovered context bytes, and give §3 a temperature dump pair (#205)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    43d75714adfaa741d792bf4aa71c870ca34216db -- diff the isolation grader's before/after dump pair, so §4.1-§4.3 get a whole-block read too (#177)
  unchanged, third column, the description -- ec/tools/testdata/README.md
    cc9a35222eae1203060caa2e169e0ab1fd7a777a -- match the fan-control probe to the isolation procedure, and run the §6 command against a committed fixture (#154)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 3 and 4 table rows, so a row number names a different row in
      each; the third-column edits are not found by this method
    5c3b88b3930f7b8da41325a1915d488862544e74 -- stage the 0751 fixed-load run so its result can be folded in mechanically (#130)
  refused, third column, the description -- ec/tools/testdata/README.md
      a row was added or removed and the table grew; a cell edit in it is not
      separable from that by this method, and it is counted on neither side. the
      two images have 2 and 3 table rows, so a row number names a different row in
      each; the third-column edits are not found by this method
    a9f9d291ac1695e762aef1d813b403987262b80d -- implement issue #122 (#126)
  unborn, third column, the description -- ec/tools/testdata/README.md
      the file is not at the first parent 30746d27 (fatal: path
      'ec/tools/testdata/README.md' exists on disk, but not in
      '30746d27bfb606116a8f04b44da0910e7c3f1bf2')
    eb495de3c024b45bd3da1e091efab8b889397eb4 -- record 0751-isolation marks in ec_watch's csv and add a grading script for the eventual capture (#120)
  unchanged, first column, the path a row names -- ec/tools/testdata/call-graph/README.md
    c83cf3b368347614e96540eca13be37c39d2f25c -- the fixture CSVs' `evidence` column is a pointer direction nothing read, and the eight cells naming a listing the real tree does not have are emptied (#943)
  refused, first column, the path a row names -- ec/tools/testdata/call-graph/README.md
      the two images carry 2 and 3 table(s), so a table number is not the same
      table on both sides; a table was added or removed, which is not a pointer-
      column edit, and a cell edit in the same file is not separable from it by
      this method -- counted on neither side. the pointer-column edits are not
      found by this method
    0a0c07795a3f9679255103fac871d3191211ee58 -- gate a citation on the citing row's own listing, so the call-graph ranking stops crediting comments that deny their own body (#536)
  refused, first column, the path a row names -- ec/tools/testdata/call-graph/README.md
      table 2 grew from 5 to 7 row(s), so a row number names a different row in
      each; a row was added or removed, which is not a pointer-column edit, and a
      cell edit in the same table is not separable from it by this method --
      counted on neither side
    8443f98b5ccdf417c14185f6c7e22cae7ed45145 -- render the undecided citation pairs, settle all 45 on the listing, and leave the filler budget where the measurement puts it (#534)
  refused, first column, the path a row names -- ec/tools/testdata/call-graph/README.md
      the two images carry 1 and 2 table(s), so a table number is not the same
      table on both sides; a table was added or removed, which is not a pointer-
      column edit, and a cell edit in the same file is not separable from it by
      this method -- counted on neither side. the pointer-column edits are not
      found by this method
    13a0236a62ea39aa0c3dae10639582416a83966b -- gate each citation on a code frame, so the call-graph ranking counts calls and not XDATA bytes (#467)
  unborn, first column, the path a row names -- ec/tools/testdata/call-graph/README.md
      the file is not at the first parent 8e5df167 (fatal: path
      'ec/tools/testdata/call-graph/README.md' exists on disk, but not in
      '8e5df1676fad342e9e852db651d093b9a105bb81')
    37140548cb3f10986517bae6575591b4f06d1d0c -- A named function calls five anonymous ones: 891 unnamed callees (#327)
  an edit is not a repair: whether one was wrong is a reading of the cells above, and it is docs/findings/testdata-index-repair-census.md's, not this run's
  every negative above is 'not found by this method'. A revision that does not resolve is not measurable in this clone, at exit 2.
```

*(Corrected 2026-10-03, issue #1084: the transcript above is the run as it was
before rows were matched over their first-column cells, and it **no longer
reproduces** — the `14 refused` there are now measured, not declined, and
**three of them held a third-column edit this transcript could not see.** The
`#746` record is in `edited` above and is `one-sided` now, because a nested
row's measured cell is its key; **both its cells are still printed**, which is
the evidence. [`testdata-index-keyed-census.md`](testdata-index-keyed-census.md)
carries the new transcript. This one stays byte-for-byte, true of the tree it was
taken on, per §4a-4d.)*

## The criterion, in as many words

**The census counts edits. It does not decide which were repairs, and its own
wording never says the word** — a property of the tool, asserted over its
rendered output in `test_the_tool_never_calls_an_edit_a_repair`, not a
disclaimer in a docstring. Whether one was wrong is a judgement about a
sentence, and it is made here, per revision, from the cells the census prints.

**And there is exactly one exemption, which the issue's framing did not
anticipate and the run found.** The word *does* reach the output, once, on this
tree: `99c01938`'s own commit subject is *"the two index hand-repairs are
measured, and …"*, and the report prints every revision's subject verbatim
because saying what a revision was about is the reason the subject is printed at
all. **A quoted subject is git's sentence about itself, not this tool's**, and
redacting it would make a report unable to show its own evidence — so the
exemption is stated in the tool's docstring and pinned by
`test_a_commit_subject_is_quoted_even_when_it_says_hand_repair`, so it cannot
widen to the tool's own vocabulary without that case going red first. **The
issue's "the tool's output never contains the word" is therefore narrowed rather
than satisfied**, and the narrower claim is the one that is true.

**A hand-repair** is an edit to a description cell **at a revision that changed
no fixture the row names.** The cell is what was wrong; the bytes it describes
were not what it said about them.

**A routine edit** is one at a revision that **did** change the fixture, where
the cell followed the bytes and nobody decided anything.

**A row addition is not an edit at all.** It moves the row count, and
`repair_rows()` **refuses rather than aligns** two images with different counts
— so row additions land in the `refused` class automatically and are counted on
neither side. A revision that both adds a row and edits a cell is stated as **not
separable by this method** rather than guessed at, which is what the refusal
line says and what makes the separation mechanical rather than inferred.

### The criterion applied, per revision

| revision | row | the fixture changed? | what moved in the cell |
|---|---|---|---|
| #182 `944b1ce7` | root 4 | **no** | `first→last (\`+1\`)` → `net (\`+1\`) and its total movement (\`3\`)`, plus a sentence saying the fixture is what §4.4's choice of figure is argued from |
| #502 `565b6f3c` | root 24 | **no** | a whole paragraph added, on `--block` selecting neither stray |
| #720 `8f4f211f` | root 23, 24 | **no** | two paragraphs added, on where the count is taken and on the two roles being one set of bytes |
| #736 `a393229b` | root 23 | **no** | `the \`elif graded_unplaced:\` branch` → `…branch of the **no-movement** chain`, plus where the *other* `elif graded_unplaced:` is reached |
| #746 `1813fe98` | nested t1 r2 | **no** | `decompiled/common/0EA2.asm` → `decompiled/bank0/0EA2.asm` |

**"The fixture changed? no" is one command per revision, and it is the criterion
doing the work:**

```
$ git show --stat --format= 944b1ce7 565b6f3c 8f4f211f a393229b 1813fe98 -- ec/tools/testdata/
 ec/tools/testdata/README.md            |  7 +++++--
 ec/tools/testdata/README.md            |  2 +-
 ec/tools/testdata/README.md            | 16 ++++++++++++----
 ec/tools/testdata/README.md            |  2 +-
 ec/tools/testdata/README.md            | 17 +++++++++++------
 ec/tools/testdata/call-graph/README.md |  2 +-
```

*(That is the run with the five `N file(s) changed, …` summary lines dropped —
one per revision, which `--stat` interleaves after each one's files. Every
per-file line above is byte-identical to the run, column alignment included, so
nothing that bears on the criterion is elided; the census transcript above this
one is byte-identical to its run in full, and this block is not, which is why
the omission is named here rather than left for a reader diffing it to find.)*

Every one of the five touched **only** an index file. Not one fixture byte moved
in any of them, so in all five the cell is what changed and the thing it
describes is not — which is the criterion's first branch in every case.

**What each one was, read from its cell rather than inferred from the number:**

- **#182** is the least obviously a repair of the four, and it is worth saying
  why rather than counting it because it is fourth on the list. The row's cell
  called the `+1` quantity **`first→last`**, which is not what the grader's net
  line is — a net is a sum of signed changes. The commit is *"report total
  movement beside the window net"*, and the cell was corrected to name `net` and
  to carry the second figure beside it. In this fixture the two quantities happen
  to be equal, so the cell carried **the right number under the wrong name**, and
  the edit is the correction of the name plus the sentence explaining why the
  fixture is the argument for §4.4's choice of figure.
- **#736** is a correction of a claim that was **ambiguous to the point of being
  wrong**: the row said the fixture "reaches the `elif graded_unplaced:` branch"
  where there are two of them, and the edit names the no-movement one and says
  that the `moved_groups` chain's own arm is reached "only over a copy of this
  set with one `0x0784` row added, not by a committed run".
- **#502, #720 and #746** are the three the corpus already names as repairs, and
  nothing here disturbs that. #746 is additionally the only one a checker on
  this tree can see: it is a `nested_missing` finding of
  `check_testdata_index.py`, and the fix was the index rather than the rule.

**So the sentence is narrowed to its population and its number is corrected
together**, which is what the issue asked for whichever way the count came out:
*the top-level table's third column has been hand-repaired four times, in #182,
#502, #720 and #736; a nested index's first column once, in #746.*

**And what is not claimed: that four is the right word rather than four being
the right number.** The census counts edits; four is what it found. Calling each
one a hand-repair is the reading above, it is checkable against the table, and a
reader who reads `944b1ce7`'s cell differently should change the word and not
the count.

## The limits, worded from what the tree says today

  * **A full clone is required**, for the reason
    `measure_index_repair_visibility.py`'s `HISTORY_REQUIREMENT` gives, and that
    constant is **reused verbatim** rather than restated here. This
    repository's checkouts differ: `ci.yml`'s `gates` job and every
    `agent-*.yml` stage are
    `fetch-depth: 0`, while `claude.yml:72` is `fetch-depth: 1` — so an
    "@claude" checkout **cannot** answer this. A revision that does not resolve
    is *not measurable in this clone*, at exit 2 and with the command that
    failed. **Never a count of zero**, and the suite's committed class *skips*
    rather than fails in a shallow checkout for the same reason.
  * **The criterion's second branch has no instance in this history.** Every one
    of the five edits is at a revision that changed no fixture, so the committed
    tree **cannot** tell a repair from a routine edit — there is no routine edit
    for it to tell. The branch is stated because the next one may be, and saying
    so is the honest reading of a criterion this history does not exercise.
  * **Fourteen revisions are counted on neither side, and that is a real
    exclusion, not a rounding.** Every one of them changed the row count — the
    table went from 3 rows to 27 over this history. A cell edit made in the same
    revision as a row addition would be invisible to this method, and the tool
    says so per revision rather than reporting the rows it could line up.
    *(Corrected 2026-10-03, issue #1084: this exclusion no longer exists. Rows
    are now matched over their `File` cells rather than by position, so a row
    addition stops making the table unmeasurable: each moved key is now printed
    in a new `one-sided` class, and **three of those revisions turn out to have
    edited a shared row as well** — which is exactly what this exclusion hid.
    [`testdata-index-keyed-census.md`](testdata-index-keyed-census.md) carries
    the measurement, the criterion applied per edited cell, and what the
    alignment still cannot see. The paragraph above stays written, true of the
    tree it was measured on, per §4a-4d.)*
  * **One revision is two records.** `1813fe98` appears twice — `unchanged` for
    the root index and `edited` for the nested one. Reading it as one is how a
    count across the two populations could come out one too high or one too low,
    which is why the suite's lookup takes the population as well as the sha.
  * **The population is the history's, not the tree's.** A nested index added and
    deleted entirely *between* two releases is in the census and not in
    `check_testdata_index.py`'s, which walks the working tree. On this history
    the two agree, and a reader who wants the tree's population should say so
    rather than take this one.
  * **The direction is unchanged, and it does not inherit #978's limit.** Both
    tools compare texts. Neither runs today's checker over an old tree, so
    "a checker that is red on an old tree may be red for a reason its author
    would have called correct" does not apply to this measurement at all.

## What the corpus changes

**Twenty sites carried the count, in fifteen files, and all twenty are corrected
with the superseded wording left visible**, per
[`../findings.md`](../findings.md) §4a-4d. The superseded text is quoted at the
top of this page rather than at each site, for the reason #978's own
"What the corpus changes" section gives: a retracted claim must not survive
unchallenged, and quoting it once here satisfies that at every site without
twenty copies of a sentence that is now false.

**This table is the enumeration, and the figure above is what its rows add up
to** — twenty rows, fifteen files — rather than a number stated beside a list
that does not match it, which is what the first pass of this page did. The
`corrected` column records *when*, because the seven marked **after review**
are the ones the first pass missed and leaving them unmarked is what let the
figure be wrong twice over.

| site | corrected | handling |
|---|---|---|
| `ec/tools/check_testdata_index.py`, docstring | first pass | replaced in place, with the population split and the pointer to here |
| `ec/tools/check_testdata_row_claims.py`, opening docstring | first pass | replaced in place, now naming the four and pointing here |
| `ec/tools/check_testdata_row_claims.py`, the `#978` block | first pass | its heading says "the two hand-repairs it was pointed at" and the four are given below it, which is the pair scoped rather than the population claim |
| `ec/tools/measure_index_repair_visibility.py`, docstring | first pass | replaced in place, and it now says in its own words that it measures a pair and the count is a different measurement |
| `ec/tools/test_check_testdata_index.py`, docstring | first pass | replaced in place |
| `ec/tools/test_check_testdata_row_claims.py`, docstring | first pass | replaced in place |
| `ec/tools/testdata/README.md` | first pass | **below the table, never in a description cell** |
| `docs/findings.md` §41 | first pass | correction in an inline italic note, §41's "the error class, and not a repair history" preserved |
| `docs/findings.md` §47 | first pass | correction in an inline italic note |
| `docs/findings.md` §81 | first pass | correction in an inline italic note; its "twice" is a record of what §41/§47/§76/§79 said and is left standing as that |
| `docs/agent-pipeline.md` item 10 | first pass | replaced in place |
| [`testdata-third-column-claims.md`](testdata-third-column-claims.md) | first pass, extended after review | the `> **Superseded, 2026-09-26, by issue #1008:**` blockquote beside the #978 one, **and** the "both repairs were to a row's third column" the blockquote leaves standing corrected in place — it was counted in this table on the strength of the blockquote, which retires the disclaimer but does not change a number in the sentence below it |
| [`testdata-row-claims-repair-measurement.md`](testdata-row-claims-repair-measurement.md) | first pass, extended after review | the same blockquote at the top, its "What the corpus changes" section extended to name the sites corrected here, and its own site list's arithmetic closed |
| `docs/agent-pipeline.md` item 9 | **after review** | replaced in place. It sits **one paragraph above the item 10 the first pass corrected**, which is why a reader following the corrected item lands on the stale count — the single worst placement of the seven |
| [`agent-gates-capture-claims.patch`](../../docs/ci/agent-gates-capture-claims.patch), header | **after review** | replaced in place. A prepared patch, so this is prose a human reads *before* landing it |
| [`agent-gates-testdata-row-claims.patch`](../../docs/ci/agent-gates-testdata-row-claims.patch), header | **after review** | replaced in place, and the "green through both" claim is left scoped to the two that were measured rather than widened to four |
| [`agent-gates-testdata-row-claims.patch`](../../docs/ci/agent-gates-testdata-row-claims.patch), the `+` line | **after review** | replaced in place, **inside the hunk**. This one is not prose a human reads: it is the text `git apply` puts into `.github/scripts/agent-gates.sh`, so leaving it would put a false count into the gate permanently. Editing a `+` line's content leaves the hunk's line counts untouched, and `tools/test_agent_gates_patches.py` applies the set and composes it in every ordered pair, so the patch is still a patch a human can land |
| [`capture-filename-date-prefix.md`](capture-filename-date-prefix.md) | **after review** | replaced in place: "both repairs" → all four, with the pointer |
| [`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md) | **after review** | the same `#747` disclaimer block, the same edit |
| [`testdata-row-claims-report-naming.md`](testdata-row-claims-report-naming.md) | **after review** | the same `#747` disclaimer block, the same edit |

**One site was considered and excluded, and naming it is what makes the
enumeration checkable rather than a number.** `ec/tools/
test_measure_index_repair_visibility.py`'s comment reads *"The two hand-repairs
the corpus's disclaimer is about"*, and its own next sentence scopes it: *"this
only says which pair of revisions the committed answer is about."* It counts
the subject of a **superseded disclaimer**, not the index's repair history, and
a test naming its own `--base`/`--repair` input is not a claim about the
population. Had the four been substituted there it would have been false; left
at two it is true, and the count it carries is a different one.

**`ec/tools/testdata/README.md` is edited below its table, never in a
description cell**, for the reason #978 gives and the checkers bear out: both
read table rows only, so a paragraph edit cannot move either tool's result, and
the replacement is kept free of backticked `0xNNNN` so it stays inert if the
paragraph is ever reflowed into the table. §4's rule — editing prose to make a
tool green is forbidden — is why the edit is a paragraph and not a cell.

**The two handles are deliberately different, and which is which is named rather
than left to be found.** The two `docs/findings/` summaries and §81 keep the old
wording as the body of the paragraph with a dated correction beside it, because
in all three the sentence is a *historical* record of what other sections said —
§81's is explicitly "§41, §47, §76 and §79 each carried the same disclaimer" —
and deleting it would remove the record. The rest are replaced in place with the
corrected claim and a pointer here, which is what #978 did at ten of its
fourteen.

**Nothing else moves.** No `status:` in `ec/annotations/registers.yaml`, no
annotation CSV, no checker rule, threshold or refusal, no fixture, no row, no
capture, no `.asm`, no `.c`. **No line is added to
`.github/scripts/agent-gates.sh`** — census tools are deliberately ungated
(`census_test_line_pins.py` appears nowhere in that file), a census renders no
verdict, and `.github/workflows/` is out of scope for an agent branch because the
plan stage's push token has no `workflow` scope. **No `gh pr create` or `gh issue
create` against any repository**, this one or another.

## The test

`ec/tools/test_census_index_third_column_edits.py`, discovered by
`bash tools/run-tests.sh` by `find` the moment it is committed, with no wiring
beyond its row in `tools/README.md`'s suite table. Thirty-seven cases, and what
they are for is not the number — the repository's standing rule is that an
expected count turns every added fixture into a failure — but the four ways the
number could be wrong quietly:

  * **the reader comparing nothing.** The inline case pins that
    `table_cells(text, column=3)` returns `[]` over a nested-shaped image while
    `markdown_tables` still finds its table, that a `File`-headed table with no
    rows is *located* rather than refused, and that `repair_rows()` over two
    nested images answers `([], None)` — a result a report could print as "no
    third-column difference", which is why the caller has to ask
    `located()` first. The scratch case is the same guard through
    `classify()`: a nested-shaped file at the root index's own path lands in
    `not-read-by-this-method` and **not** in silence, and its creating commit
    lands in `unborn` rather than `unreadable`, because one image of that pair
    does not exist and saying anything about what a reader could have read in it
    is a claim about nothing.
  * **a refusal being read as an edit.** A commit that adds a row lands in
    `refused` with `grew` and *counted on neither side* and no rows; a
    first-column-only commit lands in `unchanged`; a table that grew refuses
    that table and **leaves the others readable**; a growth that also edited a
    cell says *not separable*.
  * **a failure being read as a zero.** A commit before the file existed is
    `unborn`; a root commit is `no-parent` and the class says *not a count of
    zero*; a repository that cannot answer is exit 2; a census that located no
    index exits non-zero; no `git` on `PATH` is exit 2 before anything is
    measured.
  * **a count being read as a judgement.** The rendered output is asserted
    never to say "hand-repair" **in the tool's own wording**, to say *an edit is
    not a repair*, to count **every** class whether or not it found anything, and
    to name the column each population is read in — beside the case that pins
    the one exemption, a commit subject carrying the word and quoted anyway.

**The last class reads this repository's own history and skips when the clone is
too shallow**, on the `tools/test_agent_gates_patches.py` precedent and not
`test_walk_budget_census.py`'s assert-and-fail — the count is a number about
prose, and hardcoding it would fail the day a fifth edit is made. It asserts
that both named repairs and the nested one are among the revisions reported, that
each is in `edited` with a row, that the population holds the root index and
every nested one, that a revision whose row count moved is a refusal rather than
an edit, and that no committed revision falls in the unreadable class. **Never
how many.**

**All three load-bearing guards were checked by mutation rather than by reading
the suite green**: dropping the `located()` check, dropping the nested row-count
refusal, and collapsing `reader_for()` to one population each turn it red, and
restoring it turns it green again.

## Left open, for the follow-up pass

  * **A checker that reads what a fixture demonstrates, not the addresses in
    it.** `check_testdata_row_claims.py` is blind to all four third-column
    repairs for one reason — the cells spell zero backticked `0xNNNN` literals,
    so there is nothing to hold to a fixture. The *other* reason is now measured
    and is not about literals: `944b1ce7` was a cell naming a **quantity**
    (`first→last` where the grader prints a **net**) and `a393229b` was a cell
    naming a **branch** without saying which of two. Neither is decidable by any
    rule reading the cell, and both were caught by a person running the grader
    and reading the row. That question has a different owner and
    `test_grade_0751_isolation.py` already holds part of it.
  * **The fourteen refused revisions are not counted on either side, and one of
    them may hold an edit.** A revision that adds a fixture row *and* fixes a
    description cell is invisible here by construction. 14 revisions are in that
    state on this history; the census says so rather than guessing, and no
    method that compares positions can do better without an alignment rule that
    would itself be a judgement.
    *(Done, 2026-10-03, issue #1084: the alignment this bullet asked for exists —
    `index_keyed_rows.py`, keyed on the first-column cell, matched over the
    intersection. **It found that three of those revisions did also edit a shared
    row**, so the guess above was right that one of them might and wrong about
    how many. See [`testdata-index-keyed-census.md`](testdata-index-keyed-census.md).
    The bullet stays written, true of the tree it was measured on, per §4a-4d.)*
  * **Whether the two populations should ever be one number.** They are different
    columns in different tables, and this write-up states the reconciliation per
    population rather than summing. A future single figure would need a stated
    rule for combining them, and there is not one.
  * **`verify_reassembly.py:1313-1319` still says** *"both of ci.yml's checkouts
    are default-depth"*. #978's write-up assigned that to its own issue and it
    is not restated as a fix here; the `HISTORY_REQUIREMENT` above is reused
    from #978's own constant rather than carried over from that sentence, for
    the reason §"The four limits" of
    [`testdata-row-claims-repair-measurement.md`](testdata-row-claims-repair-measurement.md)
    gives.
