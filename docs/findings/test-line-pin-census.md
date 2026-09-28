# The census of every `test_*.py:NNN` the markdown carries, and why nothing checks it (issue #887)

**Nothing here is a hardware claim, and nothing here is a firmware claim.** No
image is opened, no register is read back, no capture is taken, and no laptop, EC
or Windows machine is involved anywhere below. Every figure is a count of lines
in files in this repository, and the one command that produces them is in it.
Same framing as [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):10 — a
census of text about text.

Issue #887 asks two things: census the `file:line` pointers the committed
markdown writes into **test files** and say how many no longer name the line they
are cited for, and then say whether a checker is warranted. The first is this
file and the tool behind it. The second is a **no**, argued from the measurement
rather than guessed at, in *Why no checker* below.

**A note on the figures below, because this file states the same four numbers
many times over and they do not all agree.** They are not all meant to. Each
paragraph that names a merge states the count **as of that merge's tree**, which
is the standing §4a-4d gives every figure here, and the trees differ: the count
has been `105`, `106` and `107` at different points, and the paragraphs that
say `106` and the paragraphs that say `107` are each true of the tree they were
measured on. **The figures for the tree this file is in now are the ones in the
transcript under *The measurement*, and they are `130 / 31 / 96 / 72`.** Every
other number in this file is a record of a tree, not a claim about this one.

That is a real weakness in the file's shape rather than a disagreement in its
content — a document that restates a moving figure in sixty places is sixty
places to correct, and the per-merge sections that used to sit at the end were
the same habit with a date on it. Those sections are gone; see *Where the
per-merge log used to be* at the end. The paragraphs that remain are the
reasoning, and reasoning is worth keeping even where its arithmetic has aged.


## What the class is, and why it is not one of the two that are held

`ec/tools/check_citation_lines.py` (#801) holds pointers into the **generated
CSVs**, and `ec/tools/check_cluster_citations.py` (#822) holds cluster-id and
row claims. Neither reaches a line number written into a `.py` file, and
[`prose-line-citations-held.md`](prose-line-citations-held.md) §"What this does
not check" says so in its own bullet: *"A pointer into a source file, as against
one into a generated CSV… A different tool."*
[`../../tools/README.md`](../../tools/README.md)'s eighth-thing paragraph says the
same from the other end: *"nothing checks a citation into a test file, which is
why the two pre-existing ones are still wrong."* This is that other tool's
census, and the count it starts from.

## The measurement

`ec/tools/census_test_line_pins.py` reads every markdown file in the tree
(`vendor/` and this file excluded, both named on every run), finds every
`test_*.py:NNN`, resolves each one to a file and a line, and prints the counts:

```console
$ python3 ec/tools/census_test_line_pins.py
132 pin(s) in 32 markdown file(s): 98 distinct spelling(s), 74 distinct resolved target(s)
  99 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 33 declined
  1 def test_, 24 assertion, 23 comment, 5 blank, 46 other (of the pins that resolve)
  read 248 markdown file(s) under the tree, excluding .git/vendor/.claude/ and docs/findings/test-line-pin-census.md; resolved against 82 test file(s) in it
  no claim is measured here: whether a cited line still carries the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
$ echo $?
0
```

*(The `read` line's population, because it is the one figure here that depends
on something other than the commit: the tool walks the tree it is standing in
and excludes only `.git/`, `vendor/` and `.claude/`, so an **untracked**
markdown file in a worktree is counted and the figure reads one higher. The
run above is the committed tree — `git ls-files | xargs cp --parents` into a
scratch directory, which is `git archive` without the export attributes — and
that is what makes `248` and `82` the two numbers a reader re-running it gets.
Run in place in a worktree carrying a `.claude-pr/` or any other untracked
notes, it reads `249`; the difference is the untracked file and nothing else.
The `82` is `len(suites(REPO))` and moves only when a suite is added.)*

*(Re-run 2026-09-27 for #739, whose write-up
[`0751-mark-provenance-column.md`](0751-mark-provenance-column.md) names the
repaired assertions in four suites and brings **twenty** new records with it:
`106 + 20 = 126`, `28 + 1 = 29` files, `79 + 12 = 91` spellings,
`58 + 10 = 68` targets, `74 + 20 = 94` resolves with the `32` declined
unmoved, and the shape split `0/14/22/5/33` → `0/24/22/5/43` — the twenty
records being ten assertions and ten `other`. The two steps that are smaller
than the record step, spelling and target, are the two where a record of the
new page's names a line a second write-up already named: `test_ec_watch.py:148`,
`test_system_id_probe.py:317` and `test_ec_watch.py:1176` are
`0751-mark-provenance-shapes.md:203`'s, `:204`'s and
`0751-path-taking-reader-fates.md:153`'s lines as well, so those three are
counted once rather than twice. That is the whole of the delta, and it was
measured rather than differenced: with the new page moved out of the tree the
run reads `origin/main` figure for figure — which it read when this was
written and does not now, the second step below being what moved it — so the
step is this change's and
not something that also moved. That equality is worth the second half of a
sentence, because the same change edits `windows/tools/test_ec_watch.py` and
`windows/tools/test_system_id_probe.py` and so moves the line every pin *into
those two files* lands on: three pins cited in two other write-ups moved, and
re-anchoring them is what brings the page-removed tree back to `origin/main`
rather than leaving a remainder to attribute to somebody. The pre-merge-log
figures this block carried until the 2026-09-27 removal, and every paragraph
further down that states a number, are the record of the trees they were
measured on and stay visible per §4a-4d.)*

*(A second step, same issue, same day, and it is the fence rule rather than
the new page: re-running
[`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md)'s second
`grep` transcript added **two** records, `126 + 2 = 128`, `91 + 2 = 93`
spellings, `68 + 1 = 69` targets, `94 + 1 = 95` resolves,
`32 + 1 = 33` declined, and the shape split `0/24/22/5/43` →
`0/24/22/5/44`. Both are the grader suite's twelfth `existing_mark_labels`
call: one record for the fenced transcript line, one for the live-prose twin
the fence rule requires beside it, which is why the record step is two, the
spelling step is two, and the target and resolve steps are one each — a
declined pin resolves to nothing, so only the twin is a target. The pin count
is what the two steps are: twenty from the new page and two from the
transcript that page's own test edits made a line short of.)*

*(Re-run 2026-09-27 after the per-merge log above was removed, and the `107`/`29`/`80`/`59` this block carried until then are left visible in §4a-4d terms: they were true of every tree up to that removal, which is what dropped one pin — the row whose only citing line was a passing mention inside the log itself. The `.claude/` in the `read` line is the worktree pruning `run-tests.sh` gained the same day, so this figure and the runner's own are the same population again. **This block is a run, not a held figure**: re-run the tool rather than editing it, which is the rule the 3,522-line chain in `tools/README.md` spent its length rediscovering.)*

*(**And the `#1032` × `#1031` merge moves both denominators of the block again,
re-run rather than differenced, and the `167` and the `43` it carried are left
written as the `#845` × `#1009` merge's reading of them.** `origin/main` at
`6b5bf965` reads **107 pins in 29 files, 80 spellings, 59 targets, 75 resolves
against 32 declined, the `0/15/22/5/33` split, `179` markdown files, `46` test
files**; the branch measured **`180` / `45`** on its own tip, and this merged
tree reads **`181` markdown files and `47` test files**. The steps are
`179 + 1 + 1 = 181` and `46 + 1 = 47`: three write-ups that cite no
`test_*.py:NNN` of their own — this issue's
[`checkout-claim-corpus.md`](checkout-claim-corpus.md), #1076's and #1033's — and
one suite, this issue's
`ec/tools/test_check_history_checkouts_corpus.py`, which is indexed and named
by path rather than by line for #811's reason. **The `180` and the `45` are the
branch's own readings and neither is this tree's**, and the `46` / `12` / `34`
the by-cited-file axis reads beside them becomes **`47` / `12` / `35`**, the
named count unmoved because no pin crossed into a fifth file. Everything above
the denominators is unmoved: the headcount is still 107 pins in 29 files, 80
spellings, 59 targets, 75 resolves against 32 declined and the `0/15/22/5/33`
split, which is what keeps the 107-row table reconciling at 107 placed with all
seven classes 0. The `167`, the `43`, the `171`, the `176`, the `177`, the `179`
and the `180` all stay written where each was measured, per
[`../findings.md`](../findings.md) §4a-4d.)*

**Correction, 2026-09-27, at the `#93` merge: the two denominators on the block
move and the headcount does not.** The block is re-run on the merged tree, and
`origin/main` is re-run beside it rather than differenced against it: the merged
tree reads **`207`** markdown files and **`59`** test files, `origin/main` at
`4d779338` reads **`206`** and **`59`**, and the step is `206 + 1 = 207` with
the test-file count unmoved. **The `+1` is #93's own
[`oem4-bit-map-and-bit0.md`](oem4-bit-map-and-bit0.md)**, which cites no
`test_*.py:NNN` of its own and adds no suite, so it moves the denominator
without the headcount; `main`'s own additions are already inside the `206` it
reads, and there is no `b2afcda4`-relative step left to account for. (#93's
branch recorded a longer one — `199 + 1 + 5 + 1 = 205` and `57 + 1 = 58`, from
a base nine merges behind `main`; that arithmetic does not describe this tree
and the figures beside it supersede it. The `b2afcda4` re-run it rests on is
confirmed and still stands: re-run at that commit the tool reads `199` and
**`57`**, so the `56` the block carried from the day it was written to the day
it was re-run was one low.)
**Everything above the denominators is unmoved**: still `106` pins in `28`
citing files, `79` spellings, `58` targets, `74` resolves against `32` declined
and the `0/14/22/5/33` split, which is what keeps the 106-row table reconciling
at 106 placed with all seven classes 0. **Six `../findings.md` rows in the
table below are re-registered, not corrected**, and both sides of this merge
move them: the five commits `main` took since `b2afcda4` put 21 lines into that
file above them and #93 puts 19 more, so `:4328`→`:4368`, `:4330`→`:4370`,
`:7329`→`:7369`, `:7550`→`:7590`, `:7611`→`:7651` and `:9371`→`:9411`, each of
which is byte-identical to the line it replaces — `git show
b2afcda4:docs/findings.md` at the six originals reads the same text — so the
verdict against each is re-read rather than carried. **A later pass moves four
of the six again, and no count with them.** `docs/findings.md`'s §21 CORRECTION
paragraph at `:6269` is **26** lines and lands above four of these rows and
below the other two, so `:7369 + 26 = :7395`, `:7590 + 26 = :7616`,
`:7651 + 26 = :7677` and `:9411 + 26 = :9437`, and `:4368` and `:4370` hold
because they sit above the insertion. What moves a pin is whether an edit adds
lines above it, not which section the edit is in, which is the correction the
tenth note further down this file records. The diff to that file is a single
hunk of 26 insertions, so each of the four new lines carries the text the line
it replaces carried, and the four verdicts, the read and shape columns and the
`106` headcount all come back identical — which is the check a repoint is run
for. The mapping this paragraph lists stays written where it was measured, per
[`../findings.md`](../findings.md) §4a-4d. The `181` and the `47` the
`#1032` × `#1031` paragraph above records, and the `180`/`181` and the `46` the
`#1033` × `#1030` paragraph below records, stay written where those merges
measured them, per [`../findings.md`](../findings.md) §4a-4d — each was a
different tree.

**Correction, 2026-09-28, at the `#904` merge: the block above is a run of the
merged tree, and this change's whole share of what moved in it is one markdown
file.** It is re-run rather than differenced, and `origin/main` is re-run beside
it: this merged tree reads **`229`** markdown files and **`75`** test files,
`origin/main` at `b0b0c09c` reads **`228`** and **`75`**, and the step is
`228 + 1 = 229` with the test-file count unmoved. **The `+1` is #904's own
[`xdata-moved-ranks-population-denominator.md`](xdata-moved-ranks-population-denominator.md)**,
which cites no `test_*.py:NNN` of its own and adds no suite, so it moves the
denominator without the headcount. **The `214` and the `65` the block carried
were stale on `main` before either side touched it** — `228` and `75` against
`214` and `65` is fourteen markdown files and ten suites, every one of them
`main`'s — so the re-transcription above supersedes those two figures rather
than stepping from them, and the only part of the move that is this change's is
the `+1` above.

**Everything above the denominators is `main`'s and is unmoved by #904**: `129`
pins in `30` citing files, `94` spellings, `70` targets, `96` resolves against
`33` declined and the `0/24/22/5/45` split, so the 129-row table reconciles
against 129 records and the reconciled count is `128` placed. `127`→`128` is
#421's own `provenance-clone-depth-behaviour.md:37` row placing, and not a
re-registration of the unplaced row below.

**Correction, 2026-09-28, at the `#491` merge: the block above is a run of the
merged tree, re-run rather than differenced, and `origin/main` (`efa47a98`) is
run beside it by the same method** — `git ls-files | xargs cp --parents` into a
scratch directory for the merged tree and `git archive` for `origin/main`. This
merged tree reads **`248`** markdown files and **`82`** test files,
`origin/main` reads **`247`** and **`82`**, and the step is `247 + 1 = 248` with
the test-file count unmoved. **The `+1` is #491's own
[`grader-repeated-capture.md`](grader-repeated-capture.md)**, which cites one
`test_*.py:NNN` and adds no suite, so it moves the denominator and takes a
record with it. These are what the two trees read when this was written and not
a standing total: every merge moves both, and the command in the block above is
what reads them now.

**Above the denominators, this change's step is one record and it is the whole
of it.** `origin/main` reads `131` pins in `31` citing files, `97` spellings,
`73` targets, `98` resolves against `33` declined and the `0/24/23/5/46` split,
and this tree reads **`132` / `32` / `98` / `74` / `99` / `33`** and the
**`1/24/23/5/46`** split. The `+1` record, the `+1` file, the `+1` spelling, the
`+1` target, the `+1` resolve and the `0 -> 1` on `def test_` are #491's alone,
because its write-up is a new file carrying exactly one pin, which resolves,
names a line no other pin in the tree names, and lands on a `def test_` header.
`33` declined, `24` assertions, `23` comments, `5` blanks and `46` other are
unmoved. **The `132`-row table below reconciles against 132 records**, and
`check_pin_table_rows.py` reads
**`132` rows, `132` records, `130` placed, `0` `read-differs`, `0`
`shape-differs`, `0` `path-differs` and `0` `duplicate-key`** on this tree. The
**two** `unplaced-row`/`row-without-record` pairs it also reports are the two the
paragraphs below name, and **both belong to `main`**: `origin/main` reads `131`
rows, `131` records, `129` placed and the same two pairs, so #491's row places
and the count goes `129` → `130` while the number of unplaced rows is unmoved.
`test_the_committed_table_places_something` pins `130 placed` for that reason.

**Two rows in the table below are re-registered, and neither is corrected.**
`main`'s `#489` correction paragraph put 26 lines into `../findings.md` at
`:6269` and #904 put 24 more at `:8433`, both above the `§62` row, so
`:9411`→`:9437` and then `:9437`→`:9461`; #904's correction blocks are above
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md)'s row too,
so `:401`→`:469`. Each of the three shifts is byte-identical to the line it
replaces — `git show 4e697871:docs/findings.md` at `:9411` reads the same text
`:9461` holds here — so the verdict against each is re-read rather than carried.
**No row is re-registered a second time**, because `main` has touched none of
the three files those rows are cited in: `git diff 66e61be6 b0b0c09c` is empty
for `../findings.md`, `docs/agent-pipeline.md` and
`xdata-flip-cause-derivation.md`. The `#93` block's `:4328`→`:4368`,
`:4330`→`:4370`, `:7329`→`:7369`, `:7550`→`:7590` and `:7611`→`:7651`, and
`#489`'s `:7369`→`:7395`, `:7590`→`:7616` and `:7611`→`:7677` beside the
`:4368`/`:4370` pair, all sit above #904's insertion points and are unmoved by
them. `check_pin_table_rows.py` agrees: `0` `read-differs`, `shape-differs`,
`path-differs` and `duplicate-key` on the merged table.

**One row is left unplaced, and it is `main`'s and not #904's.**
`docs/agent-pipeline.md:409` is a `main`-side row the run reads at `:410` — the
sentence opens on `:409` and the spelling sits one line below — and it
reproduces on a clean `origin/main`. `test_check_pin_table_rows.py` **pins it**:
`test_the_committed_table_places_something` asserts `128 placed` and its own
comment names "the record count on this tree, which is `docs/agent-pipeline.md`'s
`:409`/`:410` pair and reproduces on a clean `origin/main`". So the one-short
state is a held figure with a written reason, `test_every_class_is_zero_on_the_committed_tree`
is red on `main` for it, and re-registering the row here would move a pin #904
did not move, to make a checker green on a defect it did not introduce. **It is
left as `main` has it, and the row records the omission above** rather than the
row being quietly repaired. Fixing it is a one-cell re-registration plus the
`128`→`129` beside it, and it belongs to whichever change moves
`docs/agent-pipeline.md` next.

**A second row is left unplaced beside it, of the same shape and the same
ownership, and it is named here because the run reports two and this paragraph
above said one.** `docs/findings/0751-append-unchecked-marks.md:221` is the
citing line the table registers; the run reads the pin at **`:246`**, for the
same reason the first pair has it — the sentence the pin belongs to opens
twenty-five lines above the spelling. It is `main`'s rather than this merge's:
`origin/main` reads the same `unplaced-row`/`row-without-record` pair, and
`main` has not touched
[`0751-append-unchecked-marks.md`](0751-append-unchecked-marks.md) since, so
nothing here moves it. **The pin itself is not defective** — the row's verdict
cell is a reading and this census does not make readings — so what is recorded
is the mechanical fact and not a claim about the cited line. The one-cell
re-registration is the same repair as the first, and it belongs to whichever
change next edits that file; **it is left as `main` has it** for the reason the
paragraph above gives. With both pairs recorded, the two figures
`test_the_committed_table_places_something` and
`test_every_class_is_zero_on_the_committed_tree` turn on are `128` placed of
`130` and `2`/`2` rather than zero — the latter is red on `origin/main` for the
same two rows and is not made red by anything in this file.

The reasoning behind each figure above — which re-measurement was run against
which tree, and the `xdata_moved_ranks.py` and `INDEX.md` counts beside them —
is in
[`xdata-moved-ranks-population-denominator.md`](xdata-moved-ranks-population-denominator.md)
§8, which is where a merge of this change records itself. This file carries the
re-registration and the `+1` and nothing else.

**Correction, 2026-09-26, at the `#929` × `#962` × `#794` × `#780` merge: the
`156` above is the one figure on the block that this tree moves, and it moves
because `main` gained two write-ups after that block was transcribed.** The
block is re-run here and `origin/main` at `368e9e52` is re-run beside it, so
the step is measured on both sides rather than differenced: `main` reads
**`157`** and this tree reads **`158`**, and `157 + 1` is
[`testdata-index-evidence-column.md`](testdata-index-evidence-column.md) — which
the correction below already attributes to its own merge and which `main` has
been carrying without. **The `156` stays written in the note below, each true of
the tree it was measured on**, per §4a-4d; the sequence settled by extraction is
`152` at `77ce75df`, `153` at `f271c1c2` (#933), `154` at `aa1f2cb0` (#962),
`155` at `1127a935` (#963), `156` on the tree that correction measured, `157` at
`368e9e52`, `158` on the tree the paragraph beside this one measured, and
**`159`** here, and the two steps after `156` are one markdown
file each from #964's
[`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md) and
#982's [`testdata-addr-column-claim.md`](testdata-addr-column-claim.md); #980
adds none, editing a write-up that was already counted. **Nothing else on the
block moves**, and the correction below is unaffected by this one: the headcount
is still 106 pins in 28 files, 79 spellings, 58 targets and 74 resolves against
32 declined; the shape split is still **`0/15/22/5/32`** over 74. **The one
figure this correction's own "unmoved" clause does falsify is the `38` test
files resolved against, which reads `39` here and which the paragraph below
records from the other end.**

**Correction, 2026-09-26, at the `#929` × `#962` × `#794` × `#780` × `#985`
merge: the two denominators the paragraph above calls unmoved both move, and
`#985` is the first commit in this series that moves the test-file one at all.**
`main` gained one commit after that paragraph was written, `3e020cf4` (#985), and
it committed a suite — `ec/tools/test_disasm8051_oracle.py` — whose write-up
cites it *by path* and never as `test_disasm8051_oracle.py:NNN`, deliberately,
because a line pin would add a record here and a row in
`check_pin_table_rows.py` for no bearing on this axis. So the block reads
**`158` → `159` markdown files and `38` → `39` test files**, both re-run rather
than differenced, and **nothing else on it moves**: 106 pins, 28 citing files, 79
spellings, 58 targets, 74 resolves, 32 declined and the `0/15/22/5/32` shape
split all come back identical, which is the check a denominator's move is run
for. **The suite joined the tail rather than the named set** — the
`test_check_pin_table_by_cited_file.py` breakdown beside this one re-transcribes
`28 of 39` and the write-up that owns the decision says why — so the census's own
population figures are untouched and only the two denominators move. The
`38`-test-files clause above stays written, true of every tree from `24460001`
until `3e020cf4`, per §4a-4d.

**Correction, 2026-09-26, at the `#979` × `#780` merge: the `159` above is the one
figure this tree moves, and it moves by one markdown file — `main` gained
`abfe76e6` (#979) after that paragraph was written, and it committed
[`testdata-row-claims-multi-date-sentence.md`](testdata-row-claims-multi-date-sentence.md),
one of the files this census walks.** Re-run rather than differenced, by this
tool's own walk on a `git archive` of each tree, so the step is measured on both
sides: `origin/main` at `abfe76e6` reads **`159`** and this tree reads
**`160`**, and `159 + 1` is #979's write-up. **The test-file denominator does not
move** — `3e020cf4` is still the last commit in this series to add a suite, and
`39` still holds — and **nothing else on the block moves either**: 106 pins in 28
files, 79 spellings, 58 targets, 74 resolves against 32 declined and the
`0/15/22/5/32` shape split all come back identical, which is the check a
denominator's move is run for. **The `158` → `159` step the paragraph above
records is left written, true of the `#985` tree it was measured on and not of
this one**, per §4a-4d.

**Correction, 2026-09-26, at the `#979` × `#973` × `#780` merge: both
denominators move this time, and for the first time in this series they are the
same commit.** `main` gained `563488c4` (#973) after the paragraph above was
written, and unlike #985 and #979 it committed *both* a write-up and a suite —
[`capture-filename-date-prefix.md`](capture-filename-date-prefix.md) and
`ec/tools/test_check_capture_names.py`, the second citing its suite by path and
never as a line pin, for the reason the paragraph above gives. So the block reads
**`160` → `161` markdown files and `39` → `40` test files**, both re-run rather
than differenced, and **nothing else on it moves**: 106 pins, 28 citing files, 79
spellings, 58 targets, 74 resolves against 32 declined and the `0/15/22/5/32`
shape split all come back identical, which is the check a denominator's move is
run for. **The `38` → `39` step the paragraph two above records stays written**
and so does the `39` the one above it names as unmoved, each true of the tree it
was measured on, per §4a-4d. **The `40` is also the figure
[`pin-table-by-cited-file.md`](pin-table-by-cited-file.md)'s own re-transcribed
block and its `40 / 11 / 29` index pin now read**, and they were re-run from the
same tree rather than agreed on: the second suite lands in the tail either way,
so the merge order is not a variable, which is what a pin keyed to "the set of
`test_*.py` files" should do.

**Correction, 2026-09-26, at the `#929 × #962 × #780` merge: the block above is a
run of this merged tree, and it is the second measurement in this series where
two sides' shape movements compose rather than one superseding the other.** The
headcount is unmoved through all three merges and stays as it has read since
[#778](xdata-two-largest-case-restatement.md) — **106 pins in 28 files, 79
spellings, 58 targets, 74 resolves against 32 declined** — and the shape split is
none of the three sides'. #962 shifted every pin landing inside
`test_xdata_cluster_names.py` by correcting that module's `guard_off()` docstring
and adding a class, so five pins moved off a `def test_` header onto prose or
code and its tree read **`0/16/22/5/31`**; #780 repointed one stale line pin at
the rule that replaced the code it cited, an `assertion` onto prose, so its tree
read **`5/18/10/6/35`** against a headcount of 105. **The two movements are of
different pins, so the merged tree carries both and reads `0/15/22/5/32` over
74** — one below #962's assertion row and one above its `other` row, which is
the same arithmetic the `#778 × #780` correction below records for its own pair
and for the same reason. The other denominator is **`156`**, and the `153` the
block carried until this merge was **two short of `main`'s own tree**: each of
#962's and #963's write-ups added a markdown file and neither re-ran this block.
The five readings are settled by extraction rather than by differencing,
through this tool's own walk on a `git archive` of each — `152` at `77ce75df`,
`153` at `f271c1c2` (#933), `154` at `aa1f2cb0` (#962), `155` at `1127a935`
(#963) and **`156`** here, one file per commit, of which this merge's is
[`testdata-index-evidence-column.md`](testdata-index-evidence-column.md). The
`152 → 153` step is #933's and the published block was true of that tree; the two
steps after it are the two this merge supersedes. `38` test files resolved
against is unmoved by any of the four, because none of #933's, #962's, #963's or
#780's commits adds a suite.

**Two rows of the per-pin table below are re-derived at this merge, and they are
the branch's own rather than a third reading of the same pin.**
[`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md)
carried `:25` naming `ec/tools/test_check_testdata_index.py:413-415` as an
`assertion`; #780 repointed that pin at `:47` naming `:1180-1184` and the target
it lands on is prose, so the row reads **`other`** and **records another line**
still. Its second row moved with the twenty-one lines the branch added above it,
`:145` → **`:166`**, and its reading is unchanged. The other hundred and four
rows are `main`'s as they stood, and the whole table reconciles: `check_pin_table_rows.py`
reads **106 rows, 106 records, 106 placed and all seven classes 0** on this tree.
**No verdict was re-read**, because no pin's target line moved: the eight
verdicts #962's shift moved were re-read on `main` and are what these rows
already carry. The verdict tally below the table is therefore unmoved by this
merge — and it is **43 carry, 2 carry on the adjacent line, 19 do not carry, 10
record another line on purpose and 32 are declined**, which is `main`'s table and
not the `51`/`11` its own sentence under that table still reads. The correction
belongs beside that sentence rather than here, and is there.

**Correction, 2026-09-26, at the `#778 × #780` merge: the block above was a run of
that merged tree, and it is the first measurement in this series where two sides'
shape movements compose rather than one superseding the other.** *(The block above
is a run of the `#929 × #962 × #780` merge and not of that one, whose figures are
superseded by the correction above this one and left written here per §4a-4d: its
`5 / 18 / 10 / 6 / 35` and its `153` are what the `#778 × #780` tree gave, and
`0 / 15 / 22 / 5 / 32` and `156` are what this one gives. The headcount of six
figures is the same on both, which is why only these two moved.)* The headcount is
[#778](xdata-two-largest-case-restatement.md)'s and stays as it published it —
**106 pins in 28 files, 79 spellings, 58 targets, 74 resolves against 32
declined** — and the shape split is neither side's: #778 added one pin, so its
tree read `19`/`34`, and #780 repointed one stale line pin at the rule that
replaced the code it cited, so *its* tree read `18`/`34` against a headcount of
105. The two movements are **different pins**, so the merged tree carries both
and reads **`5 / 18 / 10 / 6 / 35` over 74** — one below #778's assertion row and
one above its `other` row, and against #780's the assertion row is unchanged and
the `other` row is one up, which is the arithmetic of two different pins moving
two different rows. The second denominator
went on once more, `152` → **`153`** markdown files read, and that is this merge's
alone: each side saw only its own write-up, and `148` + #942's, #778's, #780's,
#777's and #946's is 153. `38` test files resolved against is the three suites
(#942's, #777's, #946's) and neither side moved it. **The two corrections below
are the records of the two trees that produced those halves** and stay visible
per §4a-4d rather than edited into agreement; `test_census_test_line_pins.py`
holds all six figures above, and it is the ninth re-measurement its own comment
records.

*(**Correction, 2026-09-26, at the `#942 × #777 × #780` merge: the `152`/`38` is
re-measured on that tree, where #780's own merge read `150`/`36` and #930's run
reads `148`/`35`.** The `148`/`35` is #942's and #780's — the two write-ups each
side added to this directory, `pin-table-row-reconciliation.md` and
`testdata-index-evidence-column.md`, plus #942's
`test_check_pin_table_rows.py` among the test files. The `150`/`36` is what that
tree read **before the two commits `main` gained in the same window landed**, and
they are the reason it is superseded rather than the figure above it. One is
#777's (`24460001`), which added `doc-patch-reference-gate.md` and
`test_doc_patch_refs.py`; the other is #946's (`efc72163`), which added
`pin-table-by-cited-file.md` and `test_check_pin_table_by_cited_file.py`. That is
two more markdown files and two more test files, so the merged tree is `150`+2
and `36`+2 — one of each per commit, and neither commit's tool is in either
count, since `check_doc_patch_refs.py` and `check_pin_table_by_cited_file.py`
are tools and `suites()` indexes `test_*.py`. The shape split is the one figure
none of those four files touches: `18`/`34` is #780's own stale-pin repoint, and
`main` alone still reads `19`/`33` — the numbers #930 recorded. Nothing else on
the block moved, and `test_census_test_line_pins.py` holds every other figure in
it. The `148`/`35` pair stays in the dated runs below as what those runs printed,
per §4a-4d. **Both of those denominators are superseded by the correction above,
which is the run of the `#778 × #780` tree.**)*

**Correction, 2026-09-26, at the #778 merge: this census is 106 pins in 28 files,
not the 105 in 27 the block above read.** The block is re-run on the merged tree
and every count this page publishes is re-transcribed from it; the `105`/`27`
stays visible above and in the list below rather than edited out of silence, per
§4a-4d. Two merges are owed the correction and only one of them is this one:
**#942** added a markdown write-up and a tool with a suite without re-running
this page, which is why the `148` → `149` markdown files read and the
`35` → `36` test files resolved against were already a merge behind, and
**[#778](xdata-two-largest-case-restatement.md)** is what moved the rest — its
new write-up brings one pin with it, so files 27 → **28**, spellings 78 → **79**,
targets 57 → **58**, resolves 73 → **74** and `declined` holds at **32**, and the
`other` shape 33 → **34** is the whole of the shape movement *on its tree* — the
merged tree's is `18`/`35`, per the correction at the top. Its edit to
`ec/tools/test_xdata_cluster_names.py` re-registered 33 further pins without
adding any, which is a statement about the sweep's mechanics and not about a
claim: the 33 are the ones the *Pins* section of that write-up already measured,
and its `105 -> 106` and `73 -> 74` are these same two numbers, arrived at
separately. **The two merges that landed on `main` in the same window move none
of the six figures above, and the two denominators are `150` → `152` and `36` →
`38` rather than the branch's own**: [#777](doc-patch-reference-gate.md) and
[#946](pin-table-by-cited-file.md) each brought a markdown write-up and a suite
with it, and neither wrote a `test_*.py:NNN` into either, so the class is the
same 106 pins in the same 28 files — the third merge in a row, and the first
that moved **only** the two denominators. #777 did re-register one row's *citing*
line (`tools/README.md`, `159` → `168`, which is why the three places below that
name it agree on `168`), and #942's own addition shifted `../findings.md`'s by 26
to `9103`; both are re-registrations, neither is a new pin, and the per-pin
table below carries the re-registered readings rather than new ones.
**The per-pin table below was re-derived on the merged tree rather
than left to lag**, because #942's `check_pin_table_rows.py` makes a lagging row
a `read-differs` or an `unplaced-row` rather than a thing only a reader notices;
the standing a dated table had, this write-up's own paragraph claims, no longer
holds once the four mechanical columns are held to the run.

**Correction, 2026-09-26, at the `#929` × `#777` merge, and it is the third
re-derivation of this block: two figures move again, both denominators, and
neither is a pin count.** The block above is re-run on the merged tree and reads
**`152`** markdown files and **`38`** test files. The `150`/`36` it carried until
this merge is the `#929` × `#942` tree's, and `main`'s own §65 note in
[`../findings.md`](../findings.md) records `149 → 150` and `36 → 37` for its own
tree — the two sides counted from the same `149`/`36` base and neither saw the
other's two files and two suites, and all three values stay written here per
§4a-4d. **`main`'s own pair is one short of its own tree**, measured the same
way this one is: a `git archive origin/main` extraction reads `151` markdown
files and `38` test files, so #777's
[`doc-patch-reference-gate.md`](doc-patch-reference-gate.md) and
`tools/test_doc_patch_refs.py` are the pair `main`'s note leaves out. The
extraction is how the merged figure above was checked rather than differenced
from either side. **The two files that close the gap from the branch's side are #929's
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md) and
#941's
[`pin-table-by-cited-file.md`](pin-table-by-cited-file.md), and the two suites
are `ec/tools/test_check_pin_table_by_cited_file.py` and
`tools/test_doc_patch_refs.py`**; neither new markdown file carries a
`test_*.py:NNN` pin and neither new suite is named by one, so **`105` pins, `27`
files, `78` spellings, `57` targets, `73` resolves, `32` declined and
`5/19/10/6/33` are unchanged for the third merge running** and every count this
page publishes about the class still stands. The count of *indexed* suites is the
denominator the fifth axis reads, which is why it moved and the pins did not.

**Correction, 2026-09-26, at the `#929` × `#942` merge: two figures of that block
move, and neither is a pin count.** Re-run on the merged tree the block reads
**`150`** markdown files and **`36`** test files, where the `149` and `35` above
were the `#929` × `#930` tree's. The denominator is one more markdown file
because #942 added
[`pin-table-row-reconciliation.md`](pin-table-row-reconciliation.md) to the
corpus, and the test-file count is one more because it added
`ec/tools/test_check_pin_table_rows.py`; both stay visible above per §4a-4d, and
neither is a `test_*.py:NNN` spelling, so **`105` pins, `27` files, `78`
spellings, `57` targets, `73` resolves, `32` declined and `5/19/10/6/33` are
unchanged** and every claim this page makes about the class still stands.

**One row is re-registered rather than carried, and it is this page's own
`../../tools/README.md` row, `:159` → `:166`.** Correcting the suite count in
`tools/README.md`'s "What it runs" sentence added seven lines *above* the repoint
list that row names, so the row is re-registered in place with the two other
places that name the same line — the supersession-shape legend above and the
blocker argument in finding 2 — while the `159` stays written in the dated
`#888`/`#890` and `#885` × `#771` and `#929` × `#930` notes that recorded it,
each true of the tree it was measured on. `check_pin_table_rows.py` reads **105
rows, 105 records, 105 placed, all seven classes 0** on the tree this merge
produces, `:166` included. **Nothing in this file's own edits moved a row**,
because this file is the one the census excludes from its own population.

**And the row is re-registered a second time at the `#929` × `#777` merge,
`:166` → `:197`, with the two other places that name the same line.** This is
the third value one row has carried, and all three stay written: the `159` the
`#888`/`#890`, `#885` × `#771` and `#929` × `#930` notes record, the `:166` the
correction above registers, and `main`'s **`:168`**, which is what
`origin/main`'s copy of this table read because `main`'s own re-derivation of the
suite count added nine lines where #929's added seven. **The merged tree reads
`197`, and the arithmetic is `159 + 9 + 7 + 22 = 197`**: the two sides' nine and
seven, both above the line, and the **twenty-two** this merge added — the two
merged correction paragraphs `tools/README.md` carries for the re-derivations
being a suite short of the tree, which is where the third of the three values
comes from.
Neither side's own re-derivation saw the other, so neither could have carried the
line it settled on, and the section at the foot of this file records the same
arithmetic from the other end. `check_pin_table_rows.py` reads **105 rows, 105 records,
105 placed, all seven classes 0** on the tree this merge produces, `:197`
included, and the two `../findings.md` rows this merge re-registered reconcile
with it.

**Correction, 2026-09-26, at the `#929` × `#778` merge: the only figure of that
block that moves is the `read N markdown file(s)` line, `152` → `153`, and both
sides' copy of it was one short of the merged tree for the same reason.** Every
count the tool prints *about pins* is carried through unchanged — **`106` pins,
`28` files, `79` spellings, `58` targets, `74` resolves, `32` declined and
`5/19/10/6/34`** — because each branch's write-up is the other's denominator and
neither is a pin: #929's
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
carries none, and #778's
[`xdata-two-largest-case-restatement.md`](xdata-two-largest-case-restatement.md)
brings exactly the one #778's own correction above already counted, so the class
is the same `106` in the same `28` whether it is read from either side. **The
`152` above is neither side's error and both sides' arithmetic**: each counted
the *other* branch's markdown file and not its own. Three extractions settle it
rather than either side's differencing — `git archive` of `24460001` (the tree
both sides forked from), of `origin/main` at `77ce75df`, and of this merged
tree read **`151`**, **`152`** and **`153`** markdown files against **`38`** test
files in all three, through this tool's own `walk`. **The branch's correction
above, which records `main`'s pair as one short of its own tree at `151`, was
right about the tree it measured and is superseded by movement rather than by
error**: `main` has since taken #947, so `origin/main` reads `152` and `main`'s
own `150 → 152` note is right for `main`. All three values stay written here per
§4a-4d.

**Seven rows of the per-pin table below are re-registered rather than carried —
six of them to a value neither side wrote, and `tools/README.md`'s to the
branch's own — and the run settles every pair the two sides disagreed on.** None
of them is a new pin, and all seven are the rows this file's `#778` correction
and the branch's `#929` corrections each re-read:
`../findings.md` from `main`'s `9103` and the branch's `9158` to **`9173`**,
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) from `377`
to **`401`**, [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) from
`415` and `427` to **`436`** and **`448`**,
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md) from
`212` and `323` to **`278`** and **`389`**, and
[`../../tools/README.md`](../../tools/README.md) from `main`'s `168` and the
branch's `197` to the branch's **`197`**. **The three places that name
`tools/README.md`'s repoint line therefore agree on `197` and not on the `168`
the `#778` correction above names**, and both stay written; the arithmetic is the
branch's `159 + 9 + 7 + 22 = :197` and this merge adds nothing above it. *(And
two of the three have moved since, which is the sentence above being true of the
tree it was measured on rather than of this one: #794's six lines above `:197`
put the repoint list at **`203`**, so the supersession-shape table and the
blocker argument above now name `:203` and this drift table's `merged tree`
column keeps the `197` that was the reading then. `197 + 6 = :203` is the whole
of it, and both values stay written for the reason §4a-4d gives.)*

**The `../findings.md` row has now carried a fourth value, because correcting
this file's own denominators moved the line it names — which is the whole
mechanism this page exists to measure, caught in the act rather than in the
tree.** A first pass of this merge read **`9159`**, and the `+14` that took it
to `9173` is the blockquote
[`../findings.md`](../findings.md) §74 carries for the two denominators
superseded above: prose about a line, landing above that line. The `9159` stays
written here per §4a-4d, and the branch's `9158` and `main`'s `9103` stay written
beside it, each true of the tree it was measured on.

**The other five rows in the conflicted regions come back to one side's own
value, and the four that do are a statement about the branch's transcript rather
than a defect in it.** The
[`xdata-green-set.md`](xdata-green-set.md),
[`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md),
[`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md) and
`xdata-register-map.md` rows had each been re-read to a different *target* by the
branch — `339`, `392`, `833` and `2645` — and all four resolve to `main`'s
`347`, `400`, `898` and `2665` here: those rows sit below every line the branch
added, so the branch's re-reads were of a tree its own edits had already left
behind. The fifth is
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md)'s `:15` row, which both
sides already read at `:15`: #947's eleven lines into that write-up land at
`:536`, well below `:15`, so nothing either branch added moved it and the row
needed no re-registration. **`check_pin_table_rows.py` reads 106 rows, 106
records, 106 placed, all seven classes 0** on the tree this merge produces, and
the verdict tally below the table — `51`/`2`/`11`/`10`/`32` — is unmoved by any of
the twelve, which is what a re-registration is: same pin, same reading, new line.


**Correction, 2026-09-26, at the #888 merge: this census is 71 pins in 25 files,
not the 69 in 24 the block above first read after #850.** The block is re-run on
the merged tree and every count this page publishes is re-transcribed from it;
the `50`/`23` this page was written with and the `69`/`24` #850's merge measured
both stay visible in the list below rather than edited out of silence, per §4a-4d.
The movement is
[#888](xdata-moved-ranks-key-collision.md)'s write-up, one new markdown file, and
its two citations of the `> 300` floor. **One new file and two pins, and the two
pins are not the same claim twice**: they are two occurrences of one spelling,
written by-name (`test_xdata_cluster_names.py:563`), where the corpus already
spells the same span
by-path (`ec/tools/test_xdata_cluster_names.py:563`, in
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):324),
so the merged tree carries **one more spelling and no more target** — 44 → 45
spellings, 40 targets unchanged — while resolving goes 53 → **55** and the shape
count moves by exactly the two, `11` → `13` assertions. Nothing else moved: the
sixteen declined, the five `def test_`, the nine comments, the six blanks and the
twenty-two other are the same pins. Both new rows are in the per-pin table below
and both **carry**.

**A third merge sits beside that one and moves the numbers not at all, which is
the point worth making about it.** #891 (#900) also rewrote
`xdata-moved-ranks-fall.md`, and it put **no** `test_*.py:NNN` pin in it: the
run on the three-way merged tree is the block above, byte for byte, including
the `144` markdown files read. So the deltas below are #888's and #850's, and
this merge is the evidence that a change to one of the 25 files can leave the
whole class where it was — the same distinction the "one new spelling and no new
target" paragraph is about, one level up.

**And they carry for a reason the four #850 left behind do not, which is the
half of this that is a finding rather than arithmetic.** #850 moved the floor
from `:392` to `:563` and repointed one citation of five, so four sentences in two
other files still name where it was; this write-up's own two are repointed,
because they are *its own* — a file new to the census, born citing a line that
does not hold the claim is a wrong pin rather than a superseded record, and
§5 of that write-up says so at the length it deserves. So the class gains two
pins, **none of which joins the nine that do not carry**, and the only number
that moves is the shape split. The superseded `:392` is written bare here for
the reason [`../findings.md`](../findings.md) §65 gives: a correction that added
a 72nd pin to the census it is correcting would move the figure it reports.

*(**And at the #888 × #890 merge, two of those four sentences above stop being
true, which is the same class of failure the file is about, produced by the
merge rather than found in the tree.** The paragraphs above are #888's, measured
on #888's tree, and three claims in them do not survive #890 landing beside it:
the two new pins **no longer carry**, the shape split is `5/11/9/6/24` rather
than `5/13/9/6/22`, and the resolved-target count is **41** rather than 40.
The reason is one line moving. `assertGreater(len(moved), 300)` was at
`ec/tools/test_xdata_cluster_names.py:563` on #888's tree and is at **`:588`**
here — #890 put 25 lines into that file above it — so `:563` is now a fixture
line, and the two pins that were *born correct* are two pins that no longer
name what they cite. **That is the cascade this tool's docstring names, caught
in the act rather than in the tree**: a commit moved a line and left two
sentences naming where it was, and the only thing that noticed is a census
nobody runs. The verdict is therefore **`does not carry` for both rows in the
table below**, they are the two new entries in the eleven that do not carry,
and the class's carry count is **32 — unchanged from #850's tree and #890's,
because #888 added two rows that no longer carry to offset the two it added
that did.** The target count moves 40 → 41 because `:563` is a resolved target
`main` had never named, and the assertion split falls 13 → 11 for the same
reason: `:563` is `other` now, not `assertion`. Nothing here is repointed — the
file's own follow-up list below is where repointing lives, and these two rows
join finding 6 in it. **The `144` above is `145` here**: #890 added
`xdata-write-direction-correction.md` and #888 added
`xdata-moved-ranks-key-collision.md`.)*
> **These four figures moved three times, once for each of the merges that
> reached this one, and every time the cause is the tree rather than the
> tool.** #887
> published `50` pins in `23` files, `44` of them resolving and `15` landing on
> an assertion, over `141` markdown files; the #850/#887 merge above took that to
> `69`/`24`/`44`/`40` and `53`/`16`; **#900 then corrected this transcript's own
> `142` to the `143` its tree reads, without moving a pin — a hand-transcribed
> figure drifting, the same class of thing as the citing lines the tool cannot
> see, and named here rather than dropped**; and **this merge, measured here,
> takes the class to `71`/`25`/`45`/`41` and `55`/`16` over `145` markdown
> files.**
>
> **What #885 added is two occurrences of one spelling, and that is the whole of
> the move in occurrences.** Its own citations of
> `ec/tools/test_xdata_cluster_names.py:392` — one in
> [`../findings.md`](../findings.md) §69, for `> 300` staying put, and one in
> [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):446 — are
> **one spelling written twice**, and the target it names is one main's tree
> already carried. Occurrences, files and `resolves` each go up by two against
> `main` and `declined` stays at 16.
>
> **The spelling and target counts do move here, `44` → `45` and `40` → `41`,
> and neither side's merge moved them — the two sides simply never shared a
> tree.** #890 repointed 56 pins in `ec/tools/test_xdata_cluster_names.py` by
> +25, so `main` names that file's `:417` and `:412-414` where #885 still names
> `:392` and `:387-389`; the merged tree carries **both**, which is one more
> spelling and one more target than either side had alone. #885's own note below
> predicted `44`/`40` and was right for the tree it measured; this paragraph
> supersedes that figure rather than arguing with it, and the wrong version is
> left visible in the note per §4a-4d.
>
> **The two land on `other` rather than on the assertion, and that is #890's
> doing, not #885's — so they do not carry.** Both were written on a tree where
> `:392` was `self.assertGreater(len(moved), 300)`; #850 put 239 lines into that
> suite and moved it, #890 put 30 more in, and `:392` is now `decreased, {},` —
> the last line of the very assertion that holds *no* address's `write`
> decreasing. So **`other` goes 22 → 24, `comment` stays at 9 and `assertion`
> stays at 11**, and the two new rows in the per-pin table below are *does not
> carry* — the same defect as finding 6's four, for the same reason, arrived at
> by a different route. #885's own merge note below read `comment` 9 → 11 on the
> tree it measured, where `:392` was still a §2b comment; that reading is left
> beside this one for the same reason. The merge therefore finds two more stale
> pins, and it is this census that finds them, one merge after the four it
> already found for the identical reason. The suite's pinned figures move with
> the transcript and each pin says which addition moved it.
>
> **And at the `#888 × #885` merge, the two classes of new pin land beside each
> other and every count in the transcript above moves once more — `73` pins in
> `26` files, `46` spellings, `42` targets, `57` resolving, `16` declined,
> `5/11/9/6/26` over `146` markdown files read.** Each of those deltas is the sum
> of the two merges above it rather than a third cause: `main` contributed two
> occurrences of `test_xdata_cluster_names.py:563` and one new file, `#885`
> contributed two occurrences of `ec/tools/test_xdata_cluster_names.py:392` and
> one new file, and neither spelling or target was the other's. **The two sets of
> defective rows are disjoint**, `:563` in `xdata-moved-ranks-key-collision.md`
> (finding 7) and `:392` in [`../findings.md`](../findings.md) §69 and
> [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md) (finding 8),
> so the eleven neither merge had alone is **thirteen** and the carry count is
> **32** — the same number `main` had before either, reached twice over by adding
> four rows that do not carry. The shape split follows arithmetically: the two
> `:563` rows and the two `:392` rows are all `other` on this tree, so `other`
> goes 24 → **26** and nothing else moves. The superseded `71`/`25`/`45`/`41` and
> `5/11/9/6/24` are the records of the two trees above and stay visible per
> §4a-4d; the suite's pin carries a comment saying which addition moved it.

> **Correction, 2026-09-26, at the `#885` × `#771` merge: this census is 105 pins
> in 27 files, not the 73 in 26 the block above reads.** The block is re-run on
> the merged tree and every count this page publishes is re-transcribed from it;
> the `73`/`26`/`46`/`42`, the `57`/`16`, the `5/11/9/6/26` and the `146` this
> page was last measured with all stay visible in the blockquote above rather
> than edited out of silence, per §4a-4d. The movement is
> [#771](0751-path-taking-reader-fates.md)'s write-up, **one new markdown file
> carrying 32 records and no second cause.**
>
> **Thirty-two records from one new file, and half of them are sixteen pins
> written twice.** The file's two fenced `grep` transcripts print sixteen
> `test_*.py:NNN` lines between them, and the fence rule declines any pin whose
> only occurrence is inside a fenced block — so those sixteen are `declined` —
> and the suite's `test_every_declined_pin_is_also_cited_in_live_prose` requires
> every declined pin to have a live-prose twin, so the write-up cites all sixteen
> in prose as well and those sixteen resolve. Occurrences go 73 → **105**,
> `resolves` 57 → **73**, `declined` 16 → **32** and files 26 → **27**.
>
> **`spellings` moves by 32 where `targets` moves by 16, and the difference is a
> property of the tool rather than of the tree.** `spellings` counts `r[2]`, the
> *matched* spelling, and `grep -rn` prints a `./` prefix that prose does not —
> so each of the sixteen is **two spellings of one pin** and 46 + 32 = **78**.
> `targets` keys on the *resolved* path, which the prefix does not change, so
> 42 + 16 = **58**. The shape split is the landing shape of the sixteen prose
> lines and nothing else: `assertion` 11 → **17**, `comment` 9 → **10**, `other`
> 26 → **35**, with `def test_` and `blank` still 5 and 6.
>
> **`147` markdown files read, and `148` in a local checkout, which is worth one
> line rather than a figure.** `146` on `main` plus this merge's one new file is
> 147; a tree the pipeline has written `.claude-pr/CLAUDE.md` into reads 148,
> because `.git/info/exclude` keeps that path out of the diff and no commit
> carries it. The block above is the clean tree's run, taken in a worktree at
> this branch's tip, and the extra file is not a document anyone cited.
>
> **The whole move is carrying rows, and the size of that is the new thing —
> the shape is not, and the shape that produced it is.** Every earlier merge this
> page has taken a figure from added a file's *own* citations, and one of them
> (#888's) added nothing but carrying rows; this one added a transcript of a
> search, and the fence rule then obliged the write-up to cite in prose each line
> that transcript had printed. So the class grows 73 → 105 in one commit **and
> not one of the 32 new rows joins the thirteen that do not carry** — the carry
> count goes 32 → **48**, the largest step in it and the only one arrived at
> without a line moving, on a move that is sixteen times the size of any before it.
> That is the fence rule working rather than being worked around, and it is the
> same rule that made this page necessary: a transcript that had become a file's
> only citation of a line would be a quiet loss, and the suite is what says so.
>
> **Correction, 2026-09-26, at the `#929` merge: the block above is re-transcribed
> and the only figure in it that moves is the `read N markdown file(s)` line,
> `147` → `148`.** The block is re-run on the merged tree and every count this
> page publishes is re-transcribed from it; the `105`/`27`, the `78`, the `58`,
> the `73` resolves, the `32` declined, the `5/17/10/6/35` and the `147` all stay
> visible in the blockquote beside it rather than edited out of silence, per
> §4a-4d. **The movement is one new markdown file and not one pin.** #929's
> [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
> joins the corpus and carries no `test_*.py:NNN` pin anywhere in it, so every
> count the tool prints *about pins* comes back identical and only the
> denominator moves. **This is the second merge whose whole move is a
> denominator**, after #888's, and for the same reason: a write-up that cites no
> line of a test file costs the corpus one file and no record. The thirteen that
> do not carry and the ten that record another line are untouched, and so is the
> re-open condition at the end of this page.
>
> **`148` is now the clean tree's figure too, which makes the `.claude-pr`
> paragraph above read differently, and the two are not the same number.** That
> paragraph contrasts a clean run at `147` with a local checkout at `148` and
> attributes the whole difference to `.claude-pr/CLAUDE.md`. On this tree the
> clean run reads `148` as well and by a different cause — the new file above —
> so the two `148`s are one coincidence of arithmetic rather than a shared
> cause, and a reader who meets the figure twice should not read the second as
> the first. **No number in that paragraph is edited**, for the same reason the
> superseded counts in the blockquotes above it were not: each is true of the
> tree it was measured on. What is registered here is the one figure the tool
> prints that moved.

*(**And at issue #930, the shape movement the correction above records is taken
back one step, off *that* correction's figures rather than the older ones.**
Finding 7's two pins are repointed to `:588` — the line the `> 300` floor is on
now — so **both carry again**, `:588` is an `assertion` again, and the target
count is **57** rather than 58, because `:588` was already a target under the
checklist's by-path spelling and `:563` has now lost the last name it had. The
shape split is `5/19/10/6/33` rather than `5/17/10/6/35`, the count that do not
carry is **eleven** rather than thirteen, and the carry count is **50** rather
than 48. `105`, `27`, `78`, the 73 resolving and the 32 declined are
**unchanged**, which is the measurement that matters here: the correction
re-spelled two rows and neither added nor deleted a pin, and the two numbers that
would have moved if it had are the two that did not. **The `147` the correction
above records is `148` here, and a local checkout reads `149` for the reason that
correction gives** — the repoint's own write-up,
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md), is one new
markdown file, and it carries no `test_*.py:NNN` pin at all, which is why the
denominator moved and nothing else did. **The six `> 300` pins of findings 6 and
8 are deliberately untouched in the same pass**: they cite the one `> 300` floor
and name `:417`, `:412-414` and `:392` rather than `:588`, which is both why they
are stale and why this pass's repoint does not reach them; they were stale in the
tree when this census found them rather than made stale by a merge beside them,
and collapsing the two kinds would erase the distinction this census counts. They
are #920's. The correction above stays whole per §4a-4d — it was true of the tree
it was written on — and finding 7's amendment in that write-up is taken back the
same way. **This is the only figure in the class that has moved three times and
come back, and the reason is worth one sentence: each of the six moves was
measured on a tree that did not carry the others' additions, and only the merged
tree carries all four causes at once.**)*

> **Correction, 2026-09-26, at the `#929` × `#930` merge: the block above is
> re-transcribed once more, and the only figure in it that moves is the
> `read N markdown file(s)` line, `148` → `149`.** The run is on the merged tree
> and every count this page publishes is transcribed from it; the `105`/`27`, the
> `78`, the `57`, the `73` resolves, the `32` declined and the `5/19/10/6/33` all
> stay visible in the two corrections beside it rather than being edited out of
> silence, per §4a-4d. **The movement is one new markdown file and not one pin,
> and it is the same file #929's own correction above already names** —
> [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
> carries no `test_*.py:NNN` pin, so every count the tool prints *about pins*
> comes back exactly as `main` had it and only the denominator moves.
> **Both corrections above read the clean tree at `148` and both are right about
> their own trees**: #929's counted the new file against a `> 300` floor still at
> `:563`, #930's counted it against the repointed `:588`, and the merged tree is
> the one that carries both at once. **The eleven that do not carry, the fifty
> that do, the ten that record another line and the re-open condition are all
> unchanged**, and the section at the foot of this file is where this merge's
> citing column is recorded, because a pin census cannot see its own report go
> stale.

**Each count below is a different thing, and every one of them is printed**,
which is the only reason a census like this can be trusted: a headcount that
cannot be reconciled against itself is the failure it is measuring.

- **106 occurrences** — every pin, counted once per place it is written. Sixty-three
  spellings are written once, seven twice, eight three times and one five times
  (`ec/tools/test_xdata_cluster_names.py:481`, five times over), which is the
  whole of the gap: `7 + 16 + 4 = 27`, and `106 - 27 = 79`. *(`:448` is what this
  bullet named on #888's tree and is stale here: #890 repointed that spelling
  by +25 in the four files that carry it, and this file's own mentions of it
  are not counted by the census — the tool excludes this file — so nothing
  repointed them. The distribution beside it is unchanged and reproduces. The
  50/23/37/32 figures #887 published, the 69 this bullet read at the #850
  merge and the 73 the `#888` × `#885` blockquote above records are the trees
  they were measured on and stay visible here per §4a-4d; the gap was 13, then
  25, then 26, then 27, and is 27 again. **The gap is 27 for the second time
  running and the thirty-two that made it nothing are thirty-two new singletons**,
  because #771's write-up cites sixteen lines once in a transcript and once in
  prose and shares no spelling with the tree that carried it — sixteen spellings
  written twice and sixteen written once, all of them new. The step from 26 to 27
  was the only one two merges had ever taken together, and it was taken by the
  `:392` pair #885 wrote landing *beside* the `:417` pair #890's repoint created
  rather than replacing it. **#778's merge is the second time the gap has held,
  and it holds for the same reason and a different cause: its one new pin is a
  singleton, so sixty-two written once became sixty-three and the repeated tail
  is untouched.** The `:473` that was written five times is now `:481` and is
  still written five times — the repoint moved all five together, which is what
  a repoint is.)*
- **79 distinct spellings** — the pin exactly as written, so `test_a.py:12` and
  `ec/tools/test_a.py:12` are two. This is the figure the issue's grep reported
  for a tree half this size and it is the one that moved least, and it is also
  the figure that held through the repoint above. *(`#885`'s own merge note read
  `45`, `#887` read `37` and the tree this bullet last sat in carried 46 as the
  sum of two unrelated additions rather than a third revision of the same one;
  46 → 78 is #771's write-up alone, and it moves by 32 rather than 16 for a
  reason the correction under the transcript gives — `grep -rn` prints a `./`
  prefix that prose does not, and this count is over the *matched* spelling. The
  repoint is a fourth kind of move and the only one two rows make between them:
  they changed spelling from `test_xdata_cluster_names.py:563` to
  `test_xdata_cluster_names.py:588`, one out and one in, so the distribution
  beside it is byte-for-byte what it was and the headcount of 105 over 78 is
  arithmetic rather than a coincidence. The distinction this bullet exists to
  draw is the reason the 46 → 78 step looks twice the size of the one above it,
  and it is the same distinction the `#888` section drew about a spelling and a
  target being two measurements. **78 → 79 is #778's and is a sixth kind: a new
  singleton, neither an addition of a row that shares a spelling nor a repoint of
  one that does.**)*
- **58 distinct resolved targets** — distinct `(file, span)` pairs after
  resolution, so the two spellings of one span are one target. **Every addition
  is the whole of the move, 40 → 42 → 58 → 57 → 58**, and the first two got there by
  opposite routes, which is why neither merge's note predicted the other's figure.
  On #888's tree the corpus already wrote the same span **by path** —
  `ec/tools/test_xdata_cluster_names.py:563` in
  [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):334
  — so the two new by-name pins arrived against a target that was already there
  and this count was argued not to move. **#890 repointed that by-path spelling
  by +25, to `:588`, and left the by-name one at `:563`**: the two no longer named
  the same line, so they were two targets rather than one, and a figure two merges
  ago measured as unmovable had moved by one. **#885's two arrived
  the other way** — `ec/tools/test_xdata_cluster_names.py:392`, which neither
  tree carried, so they added a target rather than splitting one. It is the same
  line moving as finding 7 below, counted from the other end, and a different
  line moving as finding 8. **#771's sixteen are the 42 → 58 step, and they are
  the first of the three moves to add targets without any line moving at all**:
  fifteen of the sixteen are in `ec/tools/test_grade_0751_isolation.py` and one
  is in `windows/tools/test_ec_watch.py`, and none of them is a span the tree
  already carried. **#930's repoint is the step back, and it is the only figure
  in this class that has moved three times and come back**: putting the by-name
  pair back onto `:588` rejoins a target the checklist already carried by path
  and leaves `:563` named by nothing the census counts, so the count falls to
  **57** — a figure the argument below said could not move, moved by one and
  moved back, and the argument was right both times. **#778's single pin is the
  57 → 58 step back the other way and is the first move since #771's that adds
  a target without any line moving** — `:88` is the `--no-eq-guard` invocation,
  which no other pin in the tree names. **Its 33 re-registrations are not in this
  bullet and that is the point**: a repoint that moves a line the tree already
  names resolves to the target the tree already had, so a sweep of 33 leaves this
  figure at 57 + the one new pin and nothing else.
- **28 files** carry at least one;
  [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md) carries
  thirty-two, [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) thirteen,
  [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) ten,
  [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
  nine and [`../findings.md`](../findings.md) six.

**Two of the planning stage's numbers did not reproduce, and both are the
extractor's fault rather than the tree's.** The issue's own grep reported 37
distinct pins across 22 files; the plan built on it counted 49 occurrences over
the same 22, and **called 12 of those 49 an ambiguous `tools/` prefix**. This
tree carries **106 occurrences across 28 files** — fifty-seven pins and six
files above the plan's `49` over `22` — and
**none** of them ambiguous, for two reasons that are findings in their own right
and are the reason the tool is written the way it is:

*(The list of write-ups this paragraph used to carry does not add up to that
total, and the residue is left visible rather than assigned to a cause nobody
measured. It read "fifty-five pins and four files" when the headcount was 105,
which is one short of its own `105 − 49` and one short of its own `27 − 22`
already, and it named [#888](xdata-moved-ranks-key-collision.md)'s two and
`#885`'s two and `#771`'s thirty-two — 36 pins over three files, not 55 over
four. **What the four corrections above between them account for is 19 pins from
`#850`, 2 from `#888`, 2 from `#885`, 32 from `#771` and 1 from
[#778](xdata-two-largest-case-restatement.md) — 56 pins over six files** — which
is still one pin short of the 57, and the plan's `49` and #887's own `50` are
two different baselines, so the remainder is a difference between two
measurements of a population neither of them fixes. A reader who needs the
breakdown should read the per-file split the census prints on every run; this
sentence is not where it is kept, and the arithmetic error is recorded here
rather than edited into agreement, per §4a-4d.)*

1. **A scan that recognises `tools/` but not `windows/tools/` truncates the
   second into the first.** Four of the twelve are `windows/tools/…` citations
   — `windows/tools/test_ec_watch.py:145`,
   `windows/tools/test_system_id_probe.py:311` and two spellings of
   `windows/tools/test_manual_fan_ctrl_probe.py:508` — and a regex that treats
   `tools/` as the whole directory prefix cuts `windows/` off the front and
   reports four sound citations as pointing at files that do not exist. That is
   the defect this census exists to measure, one level down, and the tool takes
   the **whole** directory prefix with a lookbehind that stops it starting
   mid-path.
2. **The remaining two are not ambiguous, they are relative.** `ec/annotations/xdata-register-map.md`
   writes `../tools/test_xdata_cluster_names.py:54` and `:68-90` for its own
   neighbour, and `../../docs/findings/…` for its own page's siblings in the same
   sentence. Read against the tree those are missing paths; read against the
   citing file's own directory they are `ec/tools/…` and they are correct. The
   resolver therefore reads a path against the tree first and, only where the
   tree does not have it, beside the citing file — and says which of the two
   answered for every pin.

**So the measured headcount of this class is 106 occurrences, 79 spellings, 58
resolved targets — and zero of the twelve the plan's scan called an ambiguous
prefix is one.** The figures that moved from the plan's are recorded as a defect
in the method that produced them rather than as a drift in the tree, and a census
that reports the wrong population with great confidence is worth less than no
census. The `50`/`23` and `69`/`24` this paragraph was written with, the
`73`/`26` it was last restated at and the `105`/`27`/`78`/`57` #930's merge
measured, are the record of the trees they were measured on, and stay visible
beside the `106`/`28`/`79`/`58` for the same reason they do everywhere else in
this file.

### Verdicts, and what each one is not

| verdict | what it means | here |
|---|---|---|
| `resolves` | the file was found and the span is one it has | **95** |
| `out-of-range` | the file is there and the span ends past its end | 0 |
| `unresolved-path` | no such file under either reading | 0 |
| `ambiguous-path` | a bare module name two files in the tree could answer to | 0 |
| `declined` | a shape the reader refuses: the pin is inside a fenced block, so it is a **transcript of a run** and not a citation | **33** |

**Every negative here is "not read by this method", never "absent"** — the caveat
`ec/annotations/registers.yaml` carries for a static scan and
`check_cluster_citations.py` prints for a citation check. `unresolved-path` says
*no file of that name is at that path in this tree*, which is a statement about
a directory walk; `out-of-range` says *this span is not one the file has*, which
is a statement about a line count. Neither says anything about whether the claim
a pin was written for is true. **All three zeros are measurements, not gaps**:
every pin in the tree names a file that is in it, no cited span has outrun its
file, and no two `test_*.py` in the tree share a module name (held from the other
side by a case in the suite, because a `test_export_*.py` rename would put two
files of one name in the index and make every bare-name pin to that module
undecidable).

The thirty-three `declined` are the tool's only refusal, and declining them is not a
guess: five are `ok …` lines of a literal-scan transcript in
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md), one is a
`grep` transcript in [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md),
ten are `AssertionError:` lines of a perturbation transcript in
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) — five distinct targets,
each written twice — **and seventeen are this page's own two `grep` transcripts in
[`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md)**, four in
the first and thirteen in the second, all of them `test_*.py` lines the two
transcripts print as a `grep -rn` walk. **Seventeen distinct targets, each written
twice, and the last seventeen are the only declined pins in the class whose live-prose
twin this file's own author had to add deliberately** — the first sixteen were
duplicates of a citation the file already carried, and #771's write-up was new to
the census and born with a transcript as the only citation of sixteen lines, so
`test_every_declined_pin_is_also_cited_in_live_prose` caught all sixteen and the
twins were added in prose rather than by weakening the fence rule. The
seventeenth arrived later and for the other reason: #739's edits to the grader's
suite gave that transcript a thirteenth line to print, and re-running it is what
made the pin — a transcript that has stopped being the run is a pin nobody
re-reads. That is the
one place in this census where the fix was made to the *citing* side.
**Every declined target is also cited in live prose in the same file** — that is
a case, not an observation, because a transcript that had become a file's only
citation of a line would make the count a quiet loss rather than a declined
duplicate.

### The landing shape, which is the finding

| shape | here | what a pin naming it is pointing at |
|---|---|---|
| `def test_` | **0** | the header of a test case |
| assertion | **24** | the `assertEqual`/`assertGreater` that decides the claim |
| comment | 22 | prose the case is annotated with |
| `blank` | 5 | nothing at all — the blank line above what the span is about |
| other | 44 | a `def` that is not a test, an assignment, a `setUpClass` body |

*(The `here` column is the run above, re-read on the tree this file is in
now, and it is re-derived rather than carried: the cells this block held before
this change read `1 / 22 / 24 / 5 / 41` over `93`, which is a per-pin tally
that had drifted off the run rather than a run read differently, and the
`resolves` cell in the verdict table above drifted with it. Both are the run's
figures now, and `ec/tools/test_check_pin_table_rows.py` holds the same split
over the per-pin table's own cells, so a column that drifts from the run again
reddens there rather than being read. The split in the italic paragraph below
is the record of the nine trees it was measured on and is left written as each
of them read.)*

*(The split has now been measured nine times and the only rows that have ever
moved are the assertions and `other`: **5 / 15 / 5 / 8 / 11 over 44** as the
issue was filed, **5 / 11 / 9 / 6 / 22 over 53** after #850, **5 / 13 / 9 / 6 / 22
over 55** on the #888 × #891 tree, **5 / 11 / 9 / 6 / 24 over 55** on the
#888 × #890 one, **5 / 11 / 9 / 6 / 26 over 57** on the #888 × #885 one,
**5 / 17 / 10 / 6 / 35 over 73** at the #885 × #771 merge, the
**5 / 19 / 10 / 6 / 33 over 73** #930's repoint of that same `:563` pair onto
the floor gave, **5 / 19 / 10 / 6 / 34 over 74** on #778's tree, which is its
one new pin and nothing else — its 33 re-registrations are re-registrations, and a
row that keeps its shape when the line under it moves is what a re-registration
is — and the **5 / 18 / 10 / 6 / 35 over 74** this merge reads, which is neither
side's. The first eight are the record of the trees they were taken on and stay
visible per §4a-4d. The two that moved back are the `> 300`
floor's own `assertGreater` and the `other` row it became when #890 put 25 lines
above it; the step before that is arithmetic rather than a fourth cause, being
the two `:563` rows and the two `:392` rows the two merges added between them,
all four of which were `other` there; the fifth is neither — six assertions, one
comment and nine `other` out of one new file, the fifteen that are not assertions
being the call sites and the assignments a `grep -rn` transcript prints — and the
sixth is that same `:563` pair coming back as assertions, which is why `assertion`
reads 19 and `other` 33 rather than either side's 17/35 or 13/22. The seventh
move (#778) went up again and for the opposite reason to #930's — a pin
**added** rather than repointed, one of them only — and the eighth (#780) went
the other way, one stale line pin repointed at the rule that replaced the code
it cited, which is a move from `assertion` to `other` and so takes *both* rows at
once. **They are different pins, which is why this merge lands on 18 and 35
rather than on either side's figure**: #778's tree read `19`/`34` over 74 and
#780's read `18`/`34` over 105, and the merged tree is not the one nor the other
nor the arithmetic mean of them. That a figure
this close to stable still moves at every one of the nine measurements since the issue
was filed is the reason the distribution is printed on every run rather than
quoted once — and that one of the last two is a *correction* rather than a merge
is the reason the shape split is a reading of the class rather than a
property of it.)*

**Correction, 2026-09-26, at the `#1042` × `#1035` × `#1038` × `#1039` ×
`#1030` merge: the `167` on the block is the one figure this tree moves, and it
moves by the write-ups rather than by anything in the class.** The block is
re-run here and `origin/main` at `5244f119` is re-run beside it, so the step is
measured on both sides rather than differenced: `main` reads **`170`** and this
tree reads **`171`**, and `170 + 1` is #1030's
[`history-checkout-site-identity.md`](history-checkout-site-identity.md) — a
markdown file the walk counts and **which brings no record with it**, the same
distinction the paragraph above records for #891 and the one this census is
walked by. **The `167` stays written on the block**, each figure true of the tree
it was measured on, per [`../findings.md`](../findings.md) §4a-4d; it was last
re-transcribed at the `#845` × `#1009` merge, and the three commits `main` took
after that are the two write-ups and the `history-checkout-claims.md` edit
between them. **Nothing else on the block moves**, which is the check a
denominator's move is run for: `107` pins in `29` citing files, `80` spellings,
`59` targets, `75` resolves against `32` declined, `43` test files resolved
against, and the `0/15/22/5/33` shape split all come back identical on both
trees. **Two rows of the per-pin table moved rather than one pin being added**,
and both moves are re-registrations of a citing line, not corrections:
`history-checkout-claims.md`'s single pin reads `:262` on `main` and `:288` on
#1030's branch and `:298` here, the sum of the two sides' additions above it, and
the row is repointed to the figure the census re-run on this tree names;
`tools/README.md`'s own row moved `:431` → `:463` under the sixth supersession
note that file gained at this merge and once more, `:463` → `:466`, when that
note's own recorded totals were re-measured after #1030's site table gained the
fourth direction and its case — both by a note about a test total and not by
anything to do with the claim it reconciles, the thirteenth and fourteenth
re-registrations for that row, and each one move rather than a pair because each
note recorded its own shift correctly the first time. **No pin was added, so the reconciled count did
not move**: 107 rows answer 107 records, all 107 placed and every class 0, which
is what `check_pin_table_rows.py` re-runs here.

**Correction, 2026-09-27, at the `#1070` × `#1060` × `#1058` × `#1043` ×
`#1030` merge: the same block, re-run on a `main` that has taken four more
landings since the correction above was measured, and the step is again the
markdown-file count and nothing else.** The block is re-run here and
`origin/main` at `58f43ee7` beside it, so the step is measured on both sides
rather than differenced: `main` reads **`177`** and this tree reads **`178`**,
`177 + 1` being #1030's own
[`history-checkout-site-identity.md`](history-checkout-site-identity.md) for the
second time, and **`46`** test files resolved against on **both**, where the
correction above recorded `43` — #1058's `ec/tools/test_pd_image_census.py` and
#1060's `bios/tools/test_ifr_census.py` landing on `main` beside it, neither of
which wrote a correction here. **The pin block itself is unmoved through all
three measurements**: `107` pins in `29` citing files, `80` spellings, `59`
targets, `75` resolves against `32` declined and the `0/15/22/5/33` shape split
read identical on `origin/main` at `58f43ee7` and here, which is what keeps the
107-row table reconciling at 107 on both sides of every merge in this run. **Six rows of the per-pin table moved rather than one pin being added,
and the six are `main`'s and not this landing's**: `../findings.md`'s `:4224`,
`:4226`, `:7211`, `:7424`, `:7485` and `:9240` read as `:4230`, `:4232`,
`:7217`, `:7430`, `:7491` and `:9246` on this tree, the step being the lines
#1058, #1060 and #1070 added to `docs/findings.md` above them. So
`test_check_pin_table_rows.py` is **red on `origin/main` at `58f43ee7` and green
here** — six `unplaced-row`s and six `row-without-record`s there, all seven
classes 0 here, and the two counts are one set of six seen from either end.
**The two rows both corrections name moved for the two different reasons they
give, and both are re-registrations of a citing line rather than corrections**: `history-checkout-claims.md`'s single pin is `:298` here exactly
as the correction above recorded, and `tools/README.md`'s own row is **`:543`**,
having read `:466` on #1030's branch and `:467` on `main` — **`:467` → `:543`
under this merge**, by the three supersession paragraphs that file gained, the
fifteenth re-registration for that row and again by a note about a test total
rather than by anything to do with the `test_xdata_cluster_names.py` claim it
reconciles. **No pin was added by either side of this merge, so the reconciled
count did not move**: 107 rows answer 107 records, all 107 placed and every class
0, which is what `check_pin_table_rows.py` re-runs here.

**Correction, 2026-09-27, at the `#1032`/`#1040` × `#1076` × `#1030` merge: the
same block, re-run on a `main` that has taken two more commits since the
correction above was measured, and the step is the markdown-file count again and
nothing else.** The block is re-run here and `origin/main` at `a6a7df7a` beside
it, so the step is measured on both sides rather than differenced: `main` reads
**`179`** and this tree reads **`180`**, `179 + 1` being #1030's own
[`history-checkout-site-identity.md`](history-checkout-site-identity.md) for the
third time, and **`46`** test files resolved against on **both**, where the
correction above recorded `46` as well — #1076's
`ec/tools/bank_attribution.py` being a tool one suite reads rather than a
`test_*.py`, so it moves neither figure. **The pin block itself is unmoved
through all four measurements**: `107` pins in `29` citing files, `80`
spellings, `59` targets, `75` resolves against `32` declined and the
`0/15/22/5/33` shape split read identical on `origin/main` at `a6a7df7a` and
here. **Eight rows of the per-pin table moved rather than one pin being added,
and the six that name `../findings.md` reconcile at `main`'s lines and not the
branch's**: they read `:4249`, `:4251`, `:7236`, `:7449`, `:7510` and `:9265`
here, `main`'s own reading, because #1030's write-up to `docs/findings.md` lands
at its `:11553` here — below all six — so it moves the population without moving any
of them, and the `:4230`-side reading the correction above records stays written
where it was measured per [`../findings.md`](../findings.md) §4a-4d. **The two
rows naming a file either side of the pin table moved again, both
re-registrations of a citing line rather than corrections**:
`history-checkout-claims.md`'s single pin reads `:278` on `main` and `:298` on
#1030's branch and **`:314`** here, the sum of the two sides' additions above it,
and `tools/README.md`'s own row reads `:584` on `main` and `:543` on #1030's
branch and **`:660`** here — `584 + 76 = 660`, the seventy-six being the five
supersession paragraphs at the head of that file that neither side's tree
carried in full, all of them about a test total and none of them about the
claim the row reconciles. **No pin was added by any side of this merge, so the
reconciled count did not move**: 107 rows answer 107 records, all 107 placed and
every class 0, which is what `check_pin_table_rows.py` re-runs here.
**Six of the 74 resolving pins land on a blank line**, and that is the house
spelling rather than a mistake: a span is written from the line *above* the thing
it is about. `ec/tools/test_disasm8051.py:3-6` is a module docstring that opens
on its own blank line; `ec/tools/test_grade_0751_isolation.py:16-20` is an import
block the same way; and `test_xdata_cluster_names.py:910-916` is a span that
begins on the blank above `def test_every_row_records_the_evidence_for_its_name`.
**A checker for this class has to accept a blank line as a legitimate target**,
which is not a rule anyone writes down twice.
**Correction, 2026-09-27, at the `#1033` × `#1030` merge: the block above is
re-run once more, and the step is the markdown-file count and one citing line
again.** `origin/main` at `48887fa0` is re-run beside this tree rather than
differenced: `main` reads **`180`** markdown files and this tree reads
**`181`**, `180 + 1` being #1033's own
[`history-checkouts-gate-wiring.md`](history-checkouts-gate-wiring.md), and
**`46`** test files resolved against on both, `#1033` committing a patch and
editing two existing `tools/test_*.py` rather than adding a suite. **The pin block itself is unmoved for the
third measurement running**: `107` pins in `29` citing files, `80` spellings,
`59` targets, `75` resolves against `32` declined and the `0/15/22/5/33` shape
split read identical on `main` at `48887fa0` and here. **The reconciled count
did not move either** — 107 rows answer 107 records, all 107 placed, every class
0 — so no pin was added by either side of this merge, only two citing lines
moved, and both are re-registrations rather than corrections.
`history-checkout-claims.md`'s single pin reads `:278` on `main` at `a6a7df7a`,
`:291` on `main` at `48887fa0` and **`:327`** here, `278 + 13 + 36`, the
thirteen being #1033's "Prepared for the gate" paragraph in that file and the
thirty-six #1030's two sections, so the two sides' deltas compose rather than
one carrying the other; `tools/README.md`'s own row reads `:584` on `main` at
`48887fa0` and **`:660`** here, unchanged from the merge the correction above
records because this merge added nothing to that file above the pin. **The
`180`/`180`, the `:314` and the `:298` the correction above records stay written
where they were measured**, per [`../findings.md`](../findings.md) §4a-4d — that
was a different tree, `main` before #1033, and `:314` is the same row read on it.

## The per-pin table

One row per occurrence, in the census's own order, so a reader can re-derive it
by running the tool and reading `--verbose`. The **verdict** column is a reading
and not a measurement: it is the answer to "does the line it names still carry
the claim it is cited for", which is the half no tool in this tree can make and
the half this table exists to record.

| citing | cited target | read | shape | verdict |
| `docs/agent-pipeline.md:409` | `ec/tools/test_disasm8051.py:3-6` | by-path | blank | carries — **re-anchored from `:397` by the tool's current run; the verdict is the reading recorded against the old line and has not been re-read. Left at `:409` rather than re-registered to `:410`, where the spelling now sits, because `test_check_pin_table_rows.py` pins the placed count against this row by name — `128` placed on this tree, and `129` is what re-registering it would cost — and #904 did not cause it; see the 2026-09-28 correction above**
| [`../findings.md`](../findings.md):4368 | `test_manual_fan_ctrl_probe.py:38-40` | by-name | comment | **records another line** — **re-anchored from `:4328` by `main`'s 21 and #93's 19 added lines in `../findings.md` above it; that line's text is byte-identical, so the verdict is re-read rather than carried**
| [`../findings.md`](../findings.md):4370 | `test_ec_watch.py:86-89` | by-name | other | **records another line** — **re-anchored from `:4330` by `main`'s 21 and #93's 19 added lines in `../findings.md` above it; that line's text is byte-identical, so the verdict is re-read rather than carried**
| [`../findings.md`](../findings.md):7395 † | `test_xdata_cluster_names.py:286` | by-name | other | **does not carry** — **re-anchored from `:7369` by #489's 26 added lines in `../findings.md` above it; that line's text is byte-identical, so the verdict is re-read rather than carried**
| [`../findings.md`](../findings.md):7616 † | `ec/tools/test_disasm8051.py:3-6` | by-path | blank | carries  — **re-anchored from `:7590` by #489's 26 added lines in `../findings.md` above it; that line's text is byte-identical, so the verdict is re-read rather than carried**
| [`../findings.md`](../findings.md):7677 † | `ec/tools/test_xdata_register_map.py:9-12` | by-path | other | carries  — **re-anchored from `:7651` by #489's 26 added lines in `../findings.md` above it; that line's text is byte-identical, so the verdict is re-read rather than carried**
| [`../findings.md`](../findings.md):9461 † | `ec/tools/test_xdata_cluster_names.py:400` | by-path | other | **does not carry** — **re-anchored twice, once by each side of this merge: `:9411`→`:9437` by #489's 26 added lines in `../findings.md` above it, then `:9437`→`:9461` by #904's 24-line correction, also above it; `:9411` on the merge base is the byte-identical "`ec/tools/test_xdata_cluster_names.py:400`, the 15 ranks of headroom are as they" line `:9461` is here, so the verdict is re-read rather than carried**
| [`0751-append-unchecked-marks.md`](0751-append-unchecked-marks.md):221 | `test_manual_fan_ctrl_probe.py:905` | by-name | assertion | carries |
| [`0751-capture-row-shape.md`](0751-capture-row-shape.md):41 | `test_grade_0751_isolation.py:3608` | by-name | other | **records another line** |
| [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99 | `ec/tools/test_grade_0751_isolation.py:2232-2233` | by-path | assertion | **does not carry** |
| [`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md):263 | `test_grade_0751_isolation.py:16-20` | by-name | blank | carries |
| [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226 | `ec/tools/test_grade_0751_isolation.py:16` | by-path | blank | **does not carry** |
| [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):310 | `ec/tools/test_grade_0751_isolation.py:1862` | by-path | comment | carries, adjacent |
| [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):426 | `ec/tools/test_grade_0751_isolation.py:2694` | by-path | comment | carries, adjacent |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):127 | `windows/tools/test_manual_fan_ctrl_probe.py:513` | by-path | assertion | carries |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):137 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | by-path | other | carries |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):199 | `ec/tools/test_grade_0751_isolation.py:4374` | by-path | other | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):259 | `windows/tools/test_manual_fan_ctrl_probe.py:515` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):267 | `windows/tools/test_ec_watch.py:135` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):268 | `windows/tools/test_ec_watch.py:138` | by-path | other | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):269 | `windows/tools/test_ec_watch.py:179` | by-path | other | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):270 | `windows/tools/test_ec_watch.py:270` | by-path | other | carries — **the sentence citing it moved with the return-shape paragraph at `:179`, and the target moved as well: this change re-anchored it from `:233` to `:241` when the repair of `test_a_run_holding_the_vocabulary_names_itself_in_the_mark_row` put eight comment lines into `test_ec_watch.py` above it. `:241` holds the same `'MARK,,wrote 0x0751=0xA0,'` row the old `:233` held, so the verdict is re-read rather than carried** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):271 | `windows/tools/test_ec_watch.py:443` | by-path | assertion | carries — **the sentence citing it moved with the return-shape paragraph at `:179`, and the target moved as well: this change re-anchored it from `:406` to `:414` on the same eight lines. `:414` is the same `assertEqual` over the same row list the old `:406` held, so the verdict is re-read rather than carried** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):272 | `windows/tools/test_gpu_block_watch.py:869` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):273 | `windows/tools/test_gpu_block_watch.py:872` | by-path | other | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):274 | `windows/tools/test_system_id_probe.py:320` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):275 | `test_ec_watch.py:179` | by-name | other | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):275 | `windows/tools/test_system_id_probe.py:339` | by-path | other | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):276 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | by-path | other | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):277 | `windows/tools/test_manual_fan_ctrl_probe.py:513` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):278 | `windows/tools/test_manual_fan_ctrl_probe.py:515` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):382 | `windows/tools/test_ec_watch.py:159` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):383 | `windows/tools/test_system_id_probe.py:341` | by-path | assertion | carries — **by this change's own edit to the return-shape paragraph at `:179`, which put four lines above every pin below it; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md):384 | `windows/tools/test_ec_watch.py:1205` | by-path | other | carries — **the page's own "pins this change moved" table, and the third of the three its edits to the test files moved; `:1176` is the line `0751-path-taking-reader-fates.md` also cites and the one its transcript prints, so one landing line is now named from two write-ups** — **the sentence citing it moved with the return-shape paragraph at `:179` and the target moved twice: `:1168` when this change's edits to `test_ec_watch.py` landed, and `:1176` when the repair of `test_a_run_holding_the_vocabulary_names_itself_in_the_mark_row` put eight more lines above it. `:1176` is the `grader.existing_mark_labels(str(out)))` the old line held, so the verdict is re-read rather than carried** |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):105 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | — | — | **declined** (fenced) |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):203 | `windows/tools/test_ec_watch.py:452` | by-path | assertion | carries — **re-anchored from `:145` by this change's own edits to `test_ec_watch.py`, which put three lines above the assertion the page names; the page's sentence says the line is an `assertEqual` comparison and `:148` is one, so the verdict is re-read rather than carried** |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):204 | `windows/tools/test_system_id_probe.py:320` | by-path | assertion | carries — **re-anchored from `:311` by this change's own edits to `test_system_id_probe.py`; `:311` had become the case's own `def` header and `:317` is the `assertEqual` the page names, so the verdict is re-read rather than carried** |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):231 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | by-path | other | carries |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):541 | `windows/tools/test_manual_fan_ctrl_probe.py:515` | by-path | assertion | carries |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):579 | `test_manual_fan_ctrl_probe.py:513` | by-name | assertion | **records another line** |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):618 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | — | — | **declined** (fenced) |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):619 | `windows/tools/test_ec_watch.py:452` | — | — | **declined** (fenced) — **re-anchored from `:145`, the line `measure_mark_provenance.py` prints in section 5 and cites in its own `CITATIONS` table; the tool was re-anchored by this change, so the transcript moves with it** |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):620 | `windows/tools/test_system_id_probe.py:320` | — | — | **declined** (fenced) — **re-anchored from `:311`, the same tool's other site, for the same reason** |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):641 | `windows/tools/test_manual_fan_ctrl_probe.py:515` | — | — | **declined** (fenced) |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):69 | `./ec/tools/test_grade_0751_isolation.py:3736` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):70 | `./ec/tools/test_grade_0751_isolation.py:3795` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):71 | `./ec/tools/test_grade_0751_isolation.py:3916` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):72 | `./ec/tools/test_grade_0751_isolation.py:3926` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):89 | `ec/tools/test_grade_0751_isolation.py:3736` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):90 | `ec/tools/test_grade_0751_isolation.py:3795` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):91 | `ec/tools/test_grade_0751_isolation.py:3926` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):94 | `ec/tools/test_grade_0751_isolation.py:3916` | by-path | comment | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):108 | `./windows/tools/test_ec_watch.py:1205` | — | — | **declined** (fenced) — **re-anchored twice, to `:1168` and then to `:1176` by this change's own edits to `test_ec_watch.py`, the second of them the eight comment lines the repair of `test_a_run_holding_the_vocabulary_names_itself_in_the_mark_row` put above it; `:1176` is the line `grep -rn "\.existing_mark_labels"` reports on this tree; the page's own note at `:28` is why a transcript is allowed to be a pin at all, and it is why this one moves with the prose at `:139`** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):110 | `./ec/tools/test_grade_0751_isolation.py:3500` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):111 | `./ec/tools/test_grade_0751_isolation.py:3520` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):112 | `./ec/tools/test_grade_0751_isolation.py:3551` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):113 | `./ec/tools/test_grade_0751_isolation.py:3580` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):114 | `./ec/tools/test_grade_0751_isolation.py:3735` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):115 | `./ec/tools/test_grade_0751_isolation.py:3796` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):116 | `./ec/tools/test_grade_0751_isolation.py:3858` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):117 | `./ec/tools/test_grade_0751_isolation.py:4049` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):118 | `./ec/tools/test_grade_0751_isolation.py:4057` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):119 | `./ec/tools/test_grade_0751_isolation.py:4166` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):120 | `./ec/tools/test_grade_0751_isolation.py:4356` | — | — | **declined** (fenced) — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):121 | `./ec/tools/test_grade_0751_isolation.py:4531` | — | — | **declined** (fenced) — **the seventeenth transcript-only pin, and the one re-running the transcript at `:98` added: this change's own edits to the grader's suite grew it a twelfth `existing_mark_labels` call, so the transcript was a line short of the run and the prose list at `:142` is its live-prose twin** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):131 | `ec/tools/test_grade_0751_isolation.py:3500` | by-path | assertion | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):132 | `ec/tools/test_grade_0751_isolation.py:3520` | by-path | assertion | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):133 | `ec/tools/test_grade_0751_isolation.py:3551` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):134 | `ec/tools/test_grade_0751_isolation.py:3580` | by-path | assertion | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):135 | `ec/tools/test_grade_0751_isolation.py:3735` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):136 | `ec/tools/test_grade_0751_isolation.py:3796` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):137 | `ec/tools/test_grade_0751_isolation.py:3858` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):138 | `ec/tools/test_grade_0751_isolation.py:4049` | by-path | assertion | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):139 | `ec/tools/test_grade_0751_isolation.py:4057` | by-path | assertion | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):140 | `ec/tools/test_grade_0751_isolation.py:4166` | by-path | other | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):141 | `ec/tools/test_grade_0751_isolation.py:4356` | by-path | assertion | carries — **by this change's own edits to the transcript at `:98` and the note above it, which is what re-running `grep -rn "\.existing_mark_labels"` did to this page; the target line and the sentence citing it are unmoved, so this is a re-registration and the verdict is the reading recorded against the old line** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):142 | `ec/tools/test_grade_0751_isolation.py:4531` | by-path | other | carries — **the live-prose twin of the fenced pin at `:121`, and a new record rather than a re-registration: the line is a name the transcript and this list both newly name, so `test_every_declined_pin_is_also_cited_in_live_prose` is what required it and not a line that moved** |
| [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md):153 | `windows/tools/test_ec_watch.py:1205` | by-path | other | carries — **re-anchored twice, to `:1168` and then to `:1176` by this change's own edits to `test_ec_watch.py`, which moved the comparison down 42 lines into a different case. `:1176` is the line `grep -rn` reports and the one the transcript at `:98` prints, and the page's rule at `:28` is that a transcript is only safe while live prose names the same line; the two agree here. It reads as `other` rather than `assertion` because it is the second line of a wrapped `assertEqual` — the same class `:1134` read on `origin/main` — and it carries the sentence, so the verdict is re-read rather than carried** |
| [`bank1-e582-entry-framing.md`](bank1-e582-entry-framing.md):68 | `ec/tools/test_citation_gap_scan.py:109` | by-path | assertion | carries |
| [`deep-schedule-lint-baseline.md`](deep-schedule-lint-baseline.md):168 | `tools/test_agent_gates_patches.py:82-86` | by-path | comment | carries |
| [`deep-schedule-lint-baseline.md`](deep-schedule-lint-baseline.md):178 | `test_agent_gates_patches.py:121` | by-name | other | carries |
| [`disasm8051-self-test-gate.md`](disasm8051-self-test-gate.md):45 | `ec/tools/test_disasm8051.py:3-6` | by-path | blank | carries |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):72 | `ec/tools/test_xdata_cluster_names.py:799` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):73 | `ec/tools/test_xdata_cluster_names.py:799` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):74 | `ec/tools/test_xdata_cluster_names.py:481` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):75 | `ec/tools/test_xdata_cluster_names.py:481` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):76 | `ec/tools/test_xdata_cluster_names.py:498` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):77 | `ec/tools/test_xdata_cluster_names.py:498` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):78 | `ec/tools/test_xdata_cluster_names.py:515` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):79 | `ec/tools/test_xdata_cluster_names.py:515` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):80 | `ec/tools/test_xdata_cluster_names.py:532` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):81 | `ec/tools/test_xdata_cluster_names.py:532` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):190 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | comment | **records another line** |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):194 | `ec/tools/test_xdata_cluster_names.py:481` | by-path | comment | carries |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):202 | `test_xdata_cluster_names.py:307` | by-name | comment | **records another line** |
| [`grader-repeated-capture.md`](grader-repeated-capture.md):114 | `test_grade_0751_isolation.py:1118-1163` | by-name | def test_ | carries — **a new record rather than a re-registration: no line moved here, the write-up is new and this is its one pin. `:1118` reads `def test_a_capture_given_twice_is_refused(self):` and the range it opens is the case the citing sentence names — the grader refusing a repeated capture — so the shape is a `def test_` header and the verdict is read against it rather than carried** |
| [`history-checkout-claims.md`](history-checkout-claims.md):330 | `ec/tools/test_measure_index_repair_visibility.py:373-391` | by-path | other | carries — re-anchored from `:327` by the tool's current run on 2026-09-27; the verdict is the reading recorded against the old line and has not been re-read. **The cell previously held 338 words tracing this one row's citing line across four merges** — `:262` → `:278` → `:291` → `:314` → `:327` → `:330`, each step measured on a different tree because a different merge's correction sat above the pin. That arithmetic is in this file's git log. It is a log of line numbers, and it is worth exactly one sentence here: the row is re-anchored and it carries
| [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md):71 | `ec/tools/test_disasm8051.py:52` | — | — | **declined** (fenced) |
| [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md):228 | `test_disasm8051.py:52` | by-name | comment | carries  — **re-anchored from `:169` by the tool's current run; the verdict is the reading recorded against the old line and has not been re-read**
| [`provenance-clone-depth-behaviour.md`](provenance-clone-depth-behaviour.md):37 | `ec/tools/test_check_history_checkouts.py:438` | by-path | other | carries |
| [`runner-red-suite-set.md`](runner-red-suite-set.md):103 | `tools/test_readme_suite_table.py:11-20` | by-path | other | carries |
| [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):47 | `ec/tools/test_check_testdata_index.py:1189-1193` | by-path | other | **records another line** — **re-anchored from `:1180-1184` by #1004's ninth added line above it; the cited lines are the same `class TheReachedSomethingRule` statement, and a `class` line reads as prose as it did before, so the shape column is unmoved and the verdict is carried rather than re-read** |
| [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):189 | `ec/tools/test_check_site_census.py:449` | by-path | assertion | carries — **re-anchored from `:166` by #1004's twenty-three added lines above it; that line's text is byte-identical, so the verdict is carried rather than re-read** |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):392 | `test_xdata_cluster_names.py:54` | by-name | comment | **does not carry** |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):418 | `test_xdata_cluster_names.py:659-674` | by-name | comment | carries |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):462 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | comment | carries |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):475 | `ec/tools/test_xdata_cluster_names.py:363-378` | by-path | other | **records another line** |
| [`xdata-6a-direction-rows-pinned.md`](xdata-6a-direction-rows-pinned.md):87 | `ec/tools/test_xdata_cluster_names.py:481` | by-path | comment | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):20 | `ec/tools/test_xdata_cluster_names.py:347` | by-path | other | **does not carry** — this merge's shift moved the case it names to `:381` |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):131 | `ec/tools/test_xdata_cluster_names.py:799` | by-path | other | carries — **shape re-derived from this tree's run, and #842's comment edit above the pin moved what `:799` holds; the verdict is the reading recorded before that and has not been re-read** |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):137 | `ec/tools/test_xdata_cluster_names.py:481` | by-path | comment | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):138 | `ec/tools/test_xdata_cluster_names.py:498` | by-path | comment | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):139 | `ec/tools/test_xdata_cluster_names.py:515` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):140 | `ec/tools/test_xdata_cluster_names.py:532` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):156 | `ec/tools/test_xdata_cluster_names.py:347` | by-path | other | **does not carry** — this merge's shift moved the case it names to `:381` |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):165 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | comment | **records another line** |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):334 | `ec/tools/test_xdata_cluster_names.py:596` | by-path | other | **does not carry** — this merge's shift moved the `> 300` floor it names to `:630` |
| [`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):376 | `ec/tools/test_xdata_register_map.py:9-12` | by-path | other | carries |
| [`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):469 | `test_xdata_cluster_names.py:425` | by-name | comment | **does not carry** — **re-anchored from `:401` by #904, whose §2 and §3 correction blocks were inserted above it**
| [`xdata-green-set.md`](xdata-green-set.md):283 | `ec/tools/test_xdata_cluster_names.py:347` | by-path | other | **does not carry** — this merge's shift moved the case it names to `:381` |
| [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622 | `ec/tools/test_xdata_cluster_names.py:400` | by-path | other | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):15 | `ec/tools/test_xdata_cluster_names.py:425` | by-path | comment | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):436 | `test_xdata_cluster_names.py:425` | by-name | comment | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):448 | `test_xdata_cluster_names.py:420-422` | by-name | comment | **does not carry** |
| [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):278 | `test_xdata_cluster_names.py:596` | by-name | other | **does not carry** — this merge's shift moved the `> 300` floor it names to `:630` |
| [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):406 | `test_xdata_cluster_names.py:596` | by-name | other | **does not carry** — this merge's shift moved the `> 300` floor it names to `:630`, and moved this row's own citing line `:389` → `:406` |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):28 | `ec/tools/test_xdata_cluster_names.py:898` | by-path | comment | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):132 | `test_xdata_cluster_names.py:149-153` | by-name | other | **does not carry** — this merge's shift moved the case it names to `:183` |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):149 | `test_xdata_cluster_names.py:910-916` | by-name | comment | **does not carry** — this merge's shift moved the case it names to `:944`; the shape is re-derived from this tree's run, and #842's comment edit above the pin moved what the span holds, so neither has been re-read |
| [`xdata-two-largest-case-restatement.md`](xdata-two-largest-case-restatement.md):22 | `ec/tools/test_xdata_cluster_names.py:88` | by-path | other | carries |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):1362 | `../tools/test_xdata_cluster_names.py:54` | beside | comment | **does not carry** — re-anchored `:1340` → `:1362` by this tree's run, byte-identical at both |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2687 | `../tools/test_xdata_cluster_names.py:68-90` | beside | other | carries — re-anchored `:2665` → `:2687` by this tree's run, byte-identical at both |

**44 carry, 2 carry on the adjacent line, 19 do not carry, 10 record another line
on purpose, 32 are declined, and none is unresolvable.** *(Those are the counts
on the merged tree; the 27/3/1/6/7/6 this page was written with, the
32/3/0/9/10/16 #850's merge measured, the 34/2/9/10/16 #888's, the
32/2/11/10/16 #888 × #890's, the 32/2/13/10/16 #888 × #885's, the
48/2/13/10/32 #885 × #771's, the 50/2/11/10/32 #930's repoint, the
51/2/11/10/32 #778's merge and the **43/2/19/10/32 #962's** measured are
the record of the trees they were taken on and
are kept in the sentence rather than deleted, per §4a-4d. **Ten moves now, and
the ninth is #1009's: it added one pin, that pin carries, and no verdict moved —
the same shape the seventh was, which is why the headcount and the carry count
rose together, `43` → `44` and `106` → `107`, with the nineteen, the ten and the
thirty-two unmoved.** It is corrected here and not in that write-up, for the
reason the last paragraph below gives for #962's: the number is counted out of
*this* table and not out of anything in
[`history-checkout-claims.md`](history-checkout-claims.md), and **`main` was
carrying the stale `43` and `106` when this merge took its base.**
The `43/2/19/10/32` this sentence also carried is **not a measurement of any
tree**, and that correction is main's rather than this merge's: it is the figure
the sentence held unre-counted from `d3304785`, whose own table is 107 rows and
reads `44/2/19/10/32` — as `5244f119` and this tree do — so the five columns
summed to 106 over a 107-row table for the whole of that window, and the head
sentence reads `44` for that reason. It is left written rather than deleted, per
§4a-4d, and the step that made it stale is named in its own paragraph below.
**Eleven moves, and the tenth is this merge's, and it is the first one on this
page that moved no number at all.** Neither side added or removed a pin: #1008's
census summary and its corrections repoint six citing lines and #1037's summary
adds prose below this table without citing a test file, so the headcount, the
carry count and the other three are **all unmoved** at `44/2/19/10/32` over 107 —
which is the same triple `origin/main` reads, and the first merge in this run
whose sentence and `main`'s agree for a reason other than a carried row.
Nine moves came before those two, and the fifth of those is the one worth reading
twice: #850's took the class 50 → 69 pins, #888's
took it 69 → 71 by adding two rows that **carried** on its own tree, #890's
landing beside them took those same two rows to **`does not carry`** — so the
carry count is **32**, the same number `main` had before either of them, and the
headcount is two higher than it was — and #885's landing beside those added two
more rows that do not carry either, for the same reason and by a different route.
**The fifth breaks the pattern of the four, and is the only move this page has
recorded that leaves the defect count exactly where it was while the class grows
by nearly half.** #771 added 32 rows and **all thirty-two carry** — sixteen of
them are the live-prose twins the fence rule obliged its write-up to add, and the
other sixteen are the transcripts they twin — so the carry count is **48** for
the first time since `main`, the headcount is 105 rather than 73, and **the
thirteen that do not carry are still the same thirteen**: the nine #850 left,
#888's two and #885's two, with #771's contribution to that column **zero**.
**The sixth is the only one a *correction* made rather than a merge, and the only
one that turns a row off the list rather than onto it.** #930's repoint put
#888's two back, so the class is at **50** with the headcount unchanged at
**105** and the number that do not carry back to the **eleven** #850 and #885
left between them. What moved across the last two is two rows and one line; what
did not move is the headcount, and that is the measurement: a repoint that had
added or deleted a pin would have shown here first. **The seventh is #778's, and
it is the first move here that adds a row and moves no verdict at all.** Its new
write-up brings one pin, [`xdata-two-largest-case-restatement.md`](xdata-two-largest-case-restatement.md):22
naming the `--no-eq-guard` recipe, which was read and **carries**, and the 33
re-registrations its edit to `ec/tools/test_xdata_cluster_names.py` forced
re-registered the reading each row already had rather than making a new one —
which is the property a re-registration is supposed to have, and the reason the
class is at **51** with the headcount at **106** and the eleven that do not carry
still the same eleven. **Two merges landed on `main` in the same window and
neither is an eighth, because neither moved a number or a verdict**: #946
re-registered two rows' *citing* lines — `../findings.md` `:9077` → `:9103` and
`tools/README.md` `:159` → `:168`, the first because #942's own section landed
above it and the second because #777's `tools/README.md` edit did — and the two
readings are the ones already in the table. So the seventh is #778's on the
merged tree exactly as on its own.
**The eighth is #962's, and it is the only move this page has recorded that takes
eight rows off the carry column without adding a single pin.** Its write-up added
a class to `ec/tools/test_xdata_cluster_names.py` and corrected a docstring above
it, so every line below shifted by 34, and eight pins across four citing files
noticed — three of them naming the same `> 300` floor, one merge later and for a
third reason, and three more naming the same case header beside it. All eight
were re-read and all eight are `does not carry` on this
tree, so the class is at **43** with the headcount still **106** and the number
that do not carry at the **nineteen** the heading below now reads. **The
`51/2/11/10/32` above is where the tree stood before it, and it is the figure
`main` was still carrying when this merge re-ran the tool over it:** #962
corrected its own §75 summary and this page's heading and added finding 9 below,
and left this sentence at the pre-merge numbers. It is corrected here rather than
in that write-up because the number it corrects is counted out of *this* table
and not out of anything in
[`xdata-guard-off-key-distinctness.md`](xdata-guard-off-key-distinctness.md),
which is the same reason the two repoints above are recorded here rather than
there. **The ninth is #794's, and it moves four citing lines and not one
verdict** — the four rows marked `†` below it, whose arithmetic and whose
reconciler output are in that issue's own note further down this file. Between
the two, the headcount, the read column, the 74/32 split and the
`0/16/22/5/31` landing-shape distribution are all unmoved: the shape split is
#962's and #794's, which adds four cases to a test file the census does not read,
and the corpus denominator is **156** — `main`'s **155** plus #794's own write-up,
and #794's tool change moved no markdown that carries a pin.
The nineteen that do not carry
are the eleven #850 and #885 left, #962's eight, with #794's contribution
**zero**; see the corrections under the transcript
above and the notes at the foot of this file.)*

**The sentence above is two of its numbers behind its own table, and the
correction is here rather than in it, per §4a-4d.** Counting the verdict cells of
the table above gives **43 carry** and **19 do not carry**, where the sentence
says **51** and **11**; the other three columns — 2 adjacent, 10 recording
another line, 32 declined — are right, and the five sum to 106 either way. The
gap is exactly eight, and it is #962's: re-reading the verdicts its
`test_xdata_cluster_names.py` shift moved turned eight rows from **carries** into
**does not carry**, which is the "eight verdicts were re-read" that
[`../findings.md`](../findings.md) §75 records and the "eleven that do not carry
is now nineteen" it says in the same breath. **That correction was written into
the table and into `../findings.md` and not into this sentence**, so a reader who
lands here and counts the rows finds the eight the sentence does not have. Neither
`#962` nor `#963` is a merge this page had to re-derive, and neither is this
merge: the `#929 × #962 × #780` merge moved no verdict at all, which is what its
correction above says, and the two rows it did re-derive are a repoint that kept
its reading. **The sentence is left as written and the counts are here**, so both
the wrong value and the right one stay visible.

**And the same paragraph is itself a record, because the sentence it corrects has
since been caught by the same defect a second time.** `d3304785` — #1013's — took
this table from **106 rows to 107** by adding one row that **carries**, and the
sentence was not re-counted: it has read `43 carry` at every commit from there to
`origin/main`'s `5244f119`, so the five columns summed to 106 over a 107-row table
for the whole of that window, and the `43` in this paragraph is the *then*-right
count rather than this tree's. **Counting the table on this tree with
`check_pin_table_rows.find_table()` gives 44 / 2 / 19 / 10 / 32 over 107**, which
is what the sentence now says, and the paragraph above is left exactly as written
for the same reason the sentence's own parenthetical keeps `51` and `43`. **No
verdict moved for this merge**: the merged tree's table is byte-identical to
`5244f119`'s apart from the one `tools/README.md` row's citing line, and the step
into `107` is #1013's. It is recorded here because the sentence is the one a
reader counts against, and a second correction leaving it unmentioned would be
the same silence the first one is.**
**"carries, adjacent"** is
a pin one line off the thing it names, and it is two of one hundred and six because
this corpus writes *"is at `:1862`"* against a `def` on the next line. No rule can
decide whether that is a pin or a typo, which is the first reason the judgement
half is a table and not a verdict.
**The 9 → 11 is #885's and the 11 → 13 is #885's too — the two halves are one
merge's — and the two new
citations are where #885's lands in the table** — both in the *does
not carry* column rather than the *carries* one
their own write-up predicted, because `:392` is not where the assertion is on
this tree. One is [`../findings.md`](../findings.md) §69's, one is
[`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622's, and
together with finding 6's four they make six pins naming `:392`, `:417` or
`:412-414` for the `> 300` assertion, which is at **`:588`**. The two `:563`
pins of finding 7 named the same assertion a third way round and were counted
apart precisely because they got wrong by a different cause, a line moving under
them rather than a line never having been the one named; **#930 repointed them
onto `:588` and they are in neither the six nor the eleven above** — that is the
13 → 11 step, and it is a reading of the two cited lines rather than a verdict
from anything.

† **Two changes to the table, 2026-09-26 (issue #890), and neither moves a
count.** That issue put 25 lines into `ec/tools/test_xdata_cluster_names.py` at
`:365`, which is the cascade this tool's own docstring describes — "#852 put four
lines into `ec/tools/test_xdata_cluster_names.py` at `:291` and every `file:line`
the tree cited into that file past `:291` went stale in the same commit,
silently". **56 pins past that line were repointed by +25** across seven
markdown files, and the eight rows below whose *citing* line moved (this file
grew §2a's footnote and `xdata-moved-ranks-fall.md` grew its correction) were
re-registered against the new lines. The verdicts, the shapes, the 69/24/44 and
the 53/16 all come back identical, which is the check: a repoint that moved a
count would show here first. **The `7185` this row carried was already stale on
`origin/main` — the pin is at `7190` on a clean tree — and is corrected here
because this branch was in the file anyway, not because it caused it.**

**A fourth change to the same table, 2026-09-26 (issue #794), re-registering
four rows, and no count moves either.** That issue's summary adds one sentence
to §47 — the shape list is five and a variant since the
`another capture's address` exemption was replaced by a resolution — and §47
sits above three `../findings.md` rows, so `:7370 + 7 = :7377`, `:7431 + 7 =
:7438` and `:9173 + 7 = :9180` is the whole of that move. The fourth row is
[`../../tools/README.md`](../../tools/README.md)'s own, and **it is this
issue's second correction that moves it**: the "What it runs" sentence is
corrected with the superseded value left visible beside it, six lines above
`:197`, so `197 + 6 = :203` — the sixth time that row has moved, and
`159 + 9 + 7 + 22 + 6 = :203` is the whole arithmetic. The superseded values
stay written, each true of the tree it was measured on, per §4a-4d. **The four
verdicts, the four shapes and the 106 headcount come back identical**, which is
the check a repoint is run for: a repoint that moved a count would show here
first. The tree's own `ec/tools/test_check_pin_table_rows.py` read **3
`unplaced-row` and 3 `row-without-record` with the old lines still in the
table**, and then **1 of each** once the `../findings.md` rows were
re-registered and the `tools/README.md` one was not; it reads **106 rows, 106
records, 106 placed, all seven classes 0** with all four rows above. The
arithmetic is what that tool printed, not a guess at it. The one count that
*does* move on this tree is the runner's, 1161 → **1165** and `857` → **`861`**
on the `ec/tools` discovery, both from the four cases #794 adds to
`ec/tools/test_check_testdata_row_claims.py` and both recorded in
`tools/README.md`'s own note beside the figures they correct.

**…and at the #962 × #794 merge every line of that note above is re-measured,
with its `1165`/`861` superseded rather than deleted.** "No count moves" was
true of #794's own tree and is **not** true of this one, and the reason is
entirely #962's: the eight verdicts it re-read are the 51 → 43 / 11 → 19 step
the lead sentence above now carries, and they are counted out of this table
rather than out of anything in that write-up. **The four re-registrations are
unaffected by it, which is the half worth stating plainly: the `:7377`,
`:7438`, `:9180` and `:203` above are where the merged run reads them, the
shapes are still `blank`, `other`, `other` and `assertion`, the four verdicts
are still `carries`, `carries`, **does not carry** and **records another
line**, and the `+7` and `+6` are the whole of the two moves on this tree as
they were on that one** — `main` adds nothing above `:197`, which is why
`197 + 6 = :203` here by the same route and not by a coincidence of numbers.
`check_pin_table_rows.py` reads **4 `unplaced-row` and 4 `row-without-record`**
with `main`'s four lines still in the table, and **106 rows, 106 records, 106
placed, all seven classes 0** with the four above — checked by running it, and
the arithmetic is what it printed. **The runner's figures are additive from
both sides rather than from either**: `1164`/`860` on `main` plus this issue's
four cases is **`1168`**/**`864`**, the `+4` is the same four cases counted once,
and both pairs are re-derived by running the two commands
`tools/README.md`'s note names. Nothing in the class moved: 106 pins, 28 files,
79 spellings, 58 targets, 74 resolves, 32 declined and the `53/19/2/32` read
column are identical on all three trees, and the corpus denominator is the one
figure the merge does move, `main`'s **155** plus this issue's own write-up for
**156**.

† **A fifth change to the same table, 2026-09-26 (issue #977), re-registering
the same three `../findings.md` rows a fourth time, and no count moves either.**
That issue corrects #747's write-up in place and adds **one** correction
paragraph at the end of `../findings.md` §47 — the shape count, the case count
and the rules table's inversion are 2026-09-25's, and §47 carried the stale
version of all three with no correction beside them. §47 sits above the same
three rows #794 moved, so `:7377 + 27 = :7404`, `:7438 + 27 = :7465` and
`:9180 + 27 = :9207` is the whole of that move; the `+27` is the correction
paragraph and its blank line, and it is **the third addition to §47 to push
these rows**, after #794's `+7` and #900's `+1`. **The three verdicts, the three
shapes and the 106 headcount come back identical**, which is the check a
repoint is run for: a repoint that moved a count would show here first.
`ec/tools/test_check_pin_table_rows.py` read **3 `unplaced-row` and 3
`row-without-record` with the old lines still in the table**, and then **106
rows, 106 records, 106 placed, all seven classes 0** with the three rows
above — the arithmetic is what that tool printed, not a guess at it. **That
issue introduces no pin at all**, which is the other half and the reason this
note is three rows rather than seven: its corrections cite
`test_the_dated_capture_rule`, the suite's class docstring and the tool's own
struck docstring bullet by name, because `test_*.py:NNN` is the fragile class
this census exists for and a named test in a named file needs no row here.
The superseded `:7377`, `:7438` and `:9180` stay written in the note above
rather than edited out of it, each true of the tree it was measured on, per
§4a-4d.

**And a sixth, 2026-09-26 (the `#929` × `#962` × `#794` × `#780` merge),
re-registering the `../../tools/README.md` row alone and no count moving
either.** That merge corrects `tools/README.md`'s "What it runs" sentence a
fifth time — the fourth correction's own `1168` superseded, and the base being
what `main` reads at `368e9e52` rather than the value the sentence carried —
and the correction is three lines above `:203`, so `203 + 3 = :206` and
`159 + 9 + 7 + 22 + 6 + 3 = :206` is the whole arithmetic. **The four
`../findings.md` rows are unaffected, and the reason is the one the census's own
denominator sentences keep giving: this merge's two edits to that file land at
`:9549` and `:10085`, and every one of those rows is at a line above them —
`:7191`, `:7404`, `:7465`, `:9207` — so no repoint is owed.** The tool read
**1 `unplaced-row` and 1 `row-without-record`** with `:203` still in the table,
and **106 rows, 106 records, 106 placed, all seven classes 0** with `:206` — the
arithmetic is what it printed, not a guess at it. The superseded `:203` stays
written in the note above and in the two prose places that name it, per §4a-4d,
each true of the tree it was measured on. **The shapes and the verdicts of that
one row come back identical** — `by-name`, `assertion`, **records another line**
— which is the check a repoint is run for, and the landing-shape split is
`0/15/22/5/32`, `main`'s `0/16/22/5/31` with #780's one assertion onto prose
composed on top of it. The runner's figures beside it are re-derived rather than
added: `origin/main` reads `1177` and the `ec/tools` discovery `873`, this
merge's ten cases in one suite take them to `1187` and `883`, and the red set is
the single suite every note above names.

**And a seventh, 2026-09-26 (the `#929` × `#962` × `#794` × `#780` × `#985`
merge), re-registering the same `../../tools/README.md` row alone and still no
count moving either.** `main` gained one commit after that merge was written,
`3e020cf4` (#985), and it committed a suite — `ec/tools/test_disasm8051_oracle.py`
at 31 cases — so the "What it runs" sentence is corrected a fifth time on a
different base again: `origin/main` at `3e020cf4` reads `1208` and the `ec/tools`
discovery `904`, and this merge's ten cases in one suite take them to `1218` and
`914`. **The suite count is the figure that moves most, `38` → `39`, and it is the
first of these five corrections to add a suite rather than cases to one** — which
is why that sentence's own "no merge added a suite" clause and
`tools/README.md`'s twenty-second note are both corrected beside themselves rather
than into themselves, per §4a-4d. **The pin moves again for the same reason it
moved last time, which is this merge's own corrected parenthetical rather than
#780's:** the correction is thirteen lines above `:203` here — three as #780
wrote it, seven more because it now has to carry #985's 31 cases and its suite
beside #780's ten, and three more for the superseded-value clause added beside
them — so `203 + 13 = :216` and `159 + 9 + 7 + 22 + 6 + 13 = :216` is the
whole arithmetic, and the row is re-registered to `:216` with the `:206` and
`:203` above it left written. **#985's own line is below the pin and moves
nothing** — its suite-table row is at `tools/README.md:1185` — while the row that
*is* named, `tools/README.md:1195`, moves by both halves, `1156 + 1` for #985's
row above it and the rest for this note's own corrected parenthetical, which is
the one thing a reader checking a pin is most likely to assume lands above it.
**The four `../findings.md` rows are still unaffected, and for the same reason as
last time**: this merge's two edits to that file land at `:9549` and `:10123`
rather than the `:10085` the note above names, and `:10123` is this merge's
renumbered §78 — §77 going to #811, which landed in the same window — which is
still below all four rows at `:7191`, `:7404`, `:7465` and `:9207`. The tool read
**1 `unplaced-row` and 1 `row-without-record`** with `:206` still in the table,
and **106 rows, 106 records, 106 placed, all seven classes 0** with `:216` — the
arithmetic is what it printed, not a guess at it. **The shapes and the verdicts of
that one row come back identical again**, `by-name`, `assertion`, **records
another line**, and the landing-shape split is still `0/15/22/5/32`; the red set is
still the single suite every note above names, re-checked rather than carried and
byte-identical to the same failure in a `git archive origin/main` extraction.
**Two of the ten records named in the shape table above are the same line, and
both re-register with it** — the row and the prose that reads `:303` **because**
it is the stale value — so `:206` gives way to `:216` in both, and neither
`check_citation_lines.py`'s verdict nor the `8`/`10`/`34` over `74` moves with
them: the records are counted, their lines are not.

† **And an eighth, 2026-09-26 (the `#979` × `#973` × `#780` merge),
re-registering the same `../../tools/README.md` row alone and still no count
moving either — but the only re-registration in this file's history that was a
red suite rather than a prediction.** `main` gained a second commit after the
note above was written, `563488c4` (#973), and `tools/README.md`'s "What it
runs" sentence is corrected on both sides of this merge at once, so the two
corrections are written side by side rather than one of them: `main` reads
`:203`, the branch's own tree read `:227`, and this tree reads **`:236`**. The
step is `203 + 33 = :236`, the largest of the four moves this row has had, and
`159 + 9 + 7 + 22 + 6 + 33 = :236` is the whole arithmetic. **The note above
predicted `:216` and the table it shipped with read `:227`**, so there were
already two superseded values behind this one and there are three now; all stay
written where they are, each true of the tree it was measured on, per §4a-4d.
**The tool read 1 `unplaced-row` and 1 `row-without-record` with `:227` still in
the table** — and then **106 rows, 106 records, 106 placed, all seven classes
0** with `:236`, the arithmetic being what it printed rather than a guess at it.
**The four `../findings.md` rows are still unaffected, and for the same reason
as each time above**: this merge's two edits to that file land at `:9546` and at
its new §80, and every one of those four rows is at a line above both. **The
shape and the verdict of that one row come back identical for the fourth time**
— `by-name`, `assertion`, **records another line** — and the census's own
figures are unmoved at **106 / 28 / 79 / 58** with `74` resolving, `32` declined
and the landing-shape split still `0/15/22/5/32`, which is the check a repoint
is run for: this one moved a line and not a record, a count or a shape.

† **And a ninth, 2026-09-26 (the `#978` × `#979` × `#973` × `#780` merge),
re-registering the same `../../tools/README.md` row alone again and still no
count moving either.** #978's "What it runs" correction is eleven lines above
the pin and nothing else on either side of this merge is: the eighth note above
is the last to have moved it, and its `33` is already in the sum. So
`236 + 11 = :247` and `159 + 9 + 7 + 22 + 6 + 33 + 11 = :247` is the whole
arithmetic — **the largest value this row has held and, unlike the `33` step
before it, a step no side of this merge could have predicted alone**, since
the eleventh line is the clause carrying `1243 + 21 = 1264` beside the `1233 +
10 = 1243` it supersedes, and that clause exists only because the two merges'
corrections are written side by side. **The tool read 1 `unplaced-row` and 1
`row-without-record` with `:236` still in the table** — checked by running it,
not predicted — and **106 rows, 106 records, 106 placed, all seven classes 0**
with `:247`. **The five `../findings.md` rows are still unaffected, and for the
same reason as each time above**: #978's four edits to that file land in §41,
§47, §76 and §79, all four of which are sections above the rows, and its new
§81 is below them. **The shape and the verdict of that one row come back
identical for the fifth time** — `by-name`, `assertion`, **records another
line** — and the census's own figures are unmoved at **106 / 28 / 79 / 58** with
`74` resolving, `32` declined and the landing-shape split still `0/15/22/5/32`.
**That `32` is worth one clause rather than a shrug, because this merge is the
one that added the suite whose name the newest prose spells with `:NNN` in it**:
`tools/README.md`'s twenty-sixth note and the suite's own write-up both write
`test_measure_index_repair_visibility.py:NNN` to say the pin is *not* taken
there, and the census declines it as a non-numeric line for the same reason it
declines every other prose mention of a path it is not citing. **Nothing new is
pinned, so `58` distinct resolved targets does not move** — a declined mention
is not a record, which is the same property the eighth note relies on when it
says a line pin would have moved the 106 / 79 / 58.

† **And a tenth, 2026-09-26 (the same `#978` × `#979` × `#973` × `#780` merge as
the note above, and the second re-registration it needed rather than the only
one): the four `../findings.md` rows, which the note above leaves registered to
lines this merge moved.** Its `still unaffected` clause stays written where it is
— it was true of no tree, since §41's `+2` lands above all four rows and moves
every one of them — and is corrected here beside itself rather than edited into,
per §4a-4d.

**What moves a pin is whether an edit adds lines above it, not which section the
edit is in, and the note above's reason does not survive its own arithmetic.** It
gives "all four of which are sections above the rows", naming §41, §47, §76 and
§79: two of the four are not above the rows. §76's edit is at
[`../findings.md`](../findings.md):10063 and §79's at `:10426`, both *below*
`:9207`. They move nothing because they are below the last row, not because of
the section they sit in, and the difference is what would have told the ninth note
to check the other three. §47's edit, at `:7286`, is the case that separates the
two readings outright: it is between `:7191` and the other three rows, and it is
5 lines for 5, so it moves nothing despite being above three of them.

**The whole of the step is §41's own edit, and it is two lines.**
`docs/findings.md:7052-7056` is where "…so this check would have been green
through both. Not claimed: that it would have caught them." gives way to the
measurement beside it — three lines for five, the `+2` of this note. It sits below
the two rows at `:4206` and `:4208` and above the other four, which is why four of
the table's six `../findings.md` rows move and two do not. So `7191 + 2 = :7193`,
`7404 + 2 = :7406`, `7465 + 2 = :7467` and `9207 + 2 = :9209`, and all four
superseded values stay written here, each true of the tree it was measured on, per
§4a-4d. **The count the note above gives is `five` rows and the table carries
`six`**: `:4206`, `:4208`, `:7191`, `:7404`, `:7465` and `:9207` — three of which
the notes further down name at `:7191`, `:7370` and `:7431`, before the `+27`
above the ninth took them to the `:7404`, `:7465` and `:9207` this merge then
moves again.

**The tool read 4 `unplaced-row` and 4 `row-without-record` with `:7191`, `:7404`,
`:7465` and `:9207` still in the table** — checked by running it, not predicted,
and four of each rather than one because four rows moved rather than the single
`../../tools/README.md` row the last three notes took — **and reads 106 rows,
106 records, 106 placed, all seven classes 0** with the four re-registered. **The
read, shape and verdict cells of all four are the ones those rows held before,
unedited**: `by-name`/`other`/**does not carry**, `by-path`/`blank`/carries,
`by-path`/other/carries and `by-path`/other/**does not carry**.
`check_citation_lines.py`'s verdict does not move with them either, for the reason
the seventh note gives: the records are counted, their lines are not.

**The census's own figures are unmoved, and re-derived rather than carried** by
running `census_test_line_pins.py` on this tree: still **106 / 28 / 79 / 58** with
`74` resolving, `32` declined and the landing-shape split still `0/15/22/5/32`,
which is the same run `origin/main` reads. A line moving is not a record moving,
and that is the property every note above rests on.

**The standing red set was wrong for this merge, and the correction is the note
above's, not the tree's.** Every note above names
`ec/tools/test_check_cluster_citations.py` as the one red suite and records
`ec/tools/test_check_pin_table_rows.py` as green on its own tree. That was false
of this one: with the ninth note's registration standing, this suite read
`FAILED (failures=3)` and the checker placed `102` of `106`, because the one row
§41's `+2` did not touch was re-registered and the four it did were not. **The
ninth note's `still unaffected` clause is the whole of the defect** — not a
missing row, not a moved target, and not a count: the reason it gives for the
four rows staying put is false, and a reader following it would not have looked.

‡‡ **And a twelfth, 2026-09-26 (the `#978` × `#974` merge, this file's own
tree), re-registering the same `../../tools/README.md` row for the sixth time and
still no count moving — and the first merge in this file's run to re-register one
row that three different trees had already named.** `main` read `:247` at the
`#978` × `#979` × `#973` × `#780` merge, the branch's own tree read `:249` at the
`#780` × `#974` one, and this tree reads **`:279`**: `159 + 9 + 7 + 22 + 6 + 33 +
11 + 32 = :279`, the `+11` being the ninth note above's and the `+32` this merge's.
**All three superseded values stay written where they are** — the `:203`, the
`:206`, the `:208`, the `:236`, the `:247` and the `:249` — each true of the tree
it was measured on, per [`../findings.md`](../findings.md) §4a-4d, and this is a
**sixth** value for one pin and the third time this file has held more than two.
**The `+32` is the second step above `+30` this row has taken, and it came out of
the sentence's own parenthetical rather than out of any note**, because every
merged-tree note in `tools/README.md` sits below the pin and this merge's four of
them are renumbers rather than additions: the fourteen-figure superseded list both
sides' histories add up to, the `1243 + 21 = 1264` clause beside the
`1233 + 10 + 5 = 1248` that superseded it, and the three-figure arithmetic and
the count of superseded values that go with it. **The tool read `1 unplaced-row`
and `1 row-without-record` with every superseded value put back in the table —
`:208`, `:236`, `:247`, `:249` and `:278` in turn, each run rather than predicted
— and reads **106 rows, 106 records, 106 placed, all seven classes 0** with
`:279`, the arithmetic being what it printed.

**The census's own figures are unmoved, and re-derived rather than carried** by
running `census_test_line_pins.py` on this tree: still **106 / 28 / 79 / 58** with
`74` resolving, `32` declined, the landing-shape split still `0/15/22/5/32` and
41 indexed test files — the same run `origin/main` reads, and the property every
note above rests on. `check_pin_table_by_cited_file.py` reads **41 / 11 / 30**,
which supersedes the eleventh note's "`40 / 11 / 29` needs no correction" clause
beside itself rather than into it: the step is #978's suite and nothing else.

**The four `../findings.md` rows the ninth note moved were not moved again here,
and that is `main`'s half of the merge rather than this one's.** They read
`:7193`, `:7406`, `:7467` and `:9209` on this tree with `:4206` and `:4208`
unmoved, because #978's four edits to that file land at `:7053-7056` (the `+2`
the tenth note above measures), `:7286`, `:10086` and `:10493`, and both of its
new sections land below the last of the six rows the table registers against
that file — the tenth note's own finding rather than a new one, re-run here
rather than carried and confirmed by the tool placing all 106 rows.

**The six rows #1008 moved, and they are six moved rather than one added.**
Issue #1008's write-up cites its suite *by path* and never as
`test_census_index_third_column_edits.py:NNN` — for #811's reason, the same one
that has kept three suite landings off this axis — so the census's **106 / 79 /
58 are unmoved**: the same pins, read at their new lines. What moved is the line
each is read at, because that landing's corrections sit *above* six of them.
**`docs/agent-pipeline.md:345 → :346`** is its item-10 sentence gaining a line;
**`../findings.md:7193 → :7202`**, **`:7406 → :7423`**, **`:7467 → :7484`** and
**`:9209 → :9226`** are its §41, §47 and §81 correction notes, `+9` from the
first and `+8` more from the second, and the last two inherit that `+8`;
**`../../tools/README.md:279 → :292`** is that file's suite-count sentence
gaining the re-derivation for the suite this landing adds. All six superseded
values stay written above, each true of the tree it was measured on, per §4a-4d,
and `check_pin_table_rows.py` confirms it by placing all 106 rows on the
re-pointed table rather than on the one it found. **`check_pin_table_by_cited_file.py`
reads `42 / 11 / 31`**, the step being that landing's one new suite and nothing
else, so the `41 / 11 / 30` the note above states stays written as its tree's.

**The standing red set was two for the length of this merge and the second is the
one this note is here for, as it was at the merge above.**
`ec/tools/test_check_pin_table_rows.py` read `FAILED (failures=3)` and is green at
36 cases with `:279`. **Three, and it is three whatever value the row names**:
the row was put back to `:208`, `:236`, `:247`, `:249` and `:278` in turn and
both the checker and the suite run over each, and the checker read `1
unplaced-row` and `1 row-without-record` and the suite `FAILED (failures=3)` in
all five. **The eleventh note's four is therefore not a function of the gap, and
its own explanation — one more stacked correction above the pin is one more red
case — is corrected beside itself here rather than edited into, per §4a-4d**; the
four stays written there as that note's tree's. What the measurement does show is
the property the re-registration is run for: a row naming any superseded line
fails the same way and nothing else about the table's size, shape or verdict
split moves with it. `ec/tools/test_check_cluster_citations.py` is the suite
every note above names: 48 tests, the single failure, on the same `:220` of
#822's `xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements against `main-ec-145`, re-checked here rather
than carried, so neither #978 nor #974 caused it and neither fixes it.

‡‡ **And a thirteenth, 2026-09-26 (the `#845` × `#974` merge, this file's own
tree), re-registering the same `../../tools/README.md` row for the seventh time
and still no count moving — and the second merge in this file's run to land one
row's re-registration and no other.** The `#844` × `#974` tree above read
`:279`; #845's own tree read `:267`, which was `:247` plus twenty lines of
#845's totals re-derivation on a tree that had none of `main`'s; and this tree
reads **`:312`**, which is that `:247` plus the twelfth note's own `+32` and
this merge's **`+33`**. **All three superseded values stay written where they
are** — the `:203`, the `:206`, the `:208`, the `:236`, the `:247`, the `:249`,
the `:267` and the `:279` — each true of the tree it was measured on, per
[`../findings.md`](../findings.md) §4a-4d, and this is a **seventh** value for
one pin and the fourth time this file has held more than two. **The `+25` came
out of the sentence above the pin and not out of any note**, for the reason the
twelfth gives: every merged-tree note in `tools/README.md` sits below it, and
this merge's two are #974's renumber and a new thirty-fourth, so neither is an
addition above. What the `+33` is made of is the two sides' totals corrections
written side by side — the branch's fourth single-suite step and its two-figure
arithmetic beside the `1243 + 21 = 1264` clause, and the new thirty-fourth note
header above them — and the arithmetic is what the file printed rather than a
guess at it.

**Two lines of that file's shape table moved with it and one of them is a record
of the very row above.** The shape table's `a repoint list naming the stale
value` row and item 2 of the list beneath it both pointed at `:249`, `main`'s
value for the #851/#849 paragraph that announces such a repoint list; this tree
reads **`:282`**, and the `:236` #845's own tree read is a third value for the
same line. **Neither superseded value is left standing where it was**, which is
the one departure from the pattern every note above follows and is worth naming:
they were two re-points of one line, not two records, so there was nothing to
keep visible in place of them — the `249` and the `236` are left written here and
in the twelfth note above, each true of the tree it was measured on, and the cell
and the item beside it both now name the line this file reads. **No census record
moves with either**, because this file is excluded from its own population — the
standing the tool prints on every run — so the count below is unmoved for the
same reason the row's own is.

**The census's own figures are unmoved, and re-derived rather than carried** by
running `census_test_line_pins.py` on this tree: still **106 / 28 / 79 / 58**
with `74` resolving, `32` declined, the landing-shape split still `0/15/22/5/32`
and **42** indexed test files, `main`'s `41` plus #845's new suite.
`check_pin_table_by_cited_file.py` reads **42 / 11 / 31**, which supersedes the
twelfth note's `41 / 11 / 30` and the twenty-sixth's `40 / 11 / 29` beside
themselves rather than into them: the step is #845's suite and nothing else,
because its write-up names its six cases by class and method and the suite *by
path*, never as `test_trace_xdata_refs.py:NNN`, so no pin was added for the table
to place. **The four `../findings.md` rows the ninth and twelfth notes moved were
not moved again here**, and that is re-run rather than carried: they read
`:7193`, `:7406`, `:7467` and `:9209` with `:4206` and `:4208` unmoved, because
both of this merge's edits to that file — #974's §84 and #845's §85 — land below
the last of the six rows the table registers against it, which the tool confirms
by placing all 106.

**The standing red set is one for the length of this merge, and the suite it
would have joined is not the one it joined above.**
`ec/tools/test_check_cluster_citations.py` — 48 tests, the single failure, on
the same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` with the same
two `0x0464`/`0x0465` disagreements against `main-ec-145` — reproduces on a clean
`origin/main` worktree, re-checked here rather than carried, so neither #845 nor
#974 caused it and neither fixes it.
`ec/tools/test_check_pin_table_rows.py` read `FAILED (failures=4)` while the row
still named `:279` and is **green at 36** with `:312`, and **the four is the
twelfth note's three plus one rather than a new count**: this merge re-wrote the
top of the sentence above the pin and added a note below it, and every case the
suite loses to a stale row loses to the staleness itself. It is a function of the
row naming any line the file no longer has, which is the property the
re-registration is run for and the twelfth note's own measurement already
established.

**Correction, 2026-09-26, at the `#1008` × `#845` merge: the block's `read N
markdown file(s)` line is re-transcribed to `167` and `43`, and every count the
tool prints *about pins* is carried through unchanged — `106` pins, `28` files,
`79` spellings, `58` targets, `74` resolves, `32` declined and `0/15/22/5/32` —
because this merge adds a suite and a write-up and neither carries a pin.** The
two numbers that move are both denominators, which is the shape the `#929` ×
`#778` correction above already records: #1008's write-up,
[`testdata-index-repair-census.md`](testdata-index-repair-census.md), is the
`+1` markdown file and #1008's
`ec/tools/test_census_index_third_column_edits.py` the `+1` test file, each
counted by the other side's landing being absent. **`origin/main` at `5881153d`
reads `166` and `42` on a clean worktree**, and the `166`/`42` is the pair the
merged tree adds one to rather than the pair it adds to; the `161` and `40` the
block carried until now were **already stale on `main`** by five and two, so they
are not this merge's to attribute and are left written here beside the newer
pair rather than treated as a step either side took. All three pairs stay visible
per §4a-4d.

**The one row this merge re-registers is the `../../tools/README.md` row, and it
is the **eighth** value one pin has carried rather than a new pin.** The block
above is what made it move: #1008's correction to the suite-count sentence sits
*above* it and the merged tree's own does too, so the row reads **`:354`** where
`main` reads `:312` and the branch's own tree read `:292` — `:279 → :292 → :312
→ :354`, with `main`'s `:312` and the branch's `:292` the two values the two
sides wrote and `:279` the `#844` × `#974` tree's that both inherited. The
thirteenth note above records `:279 → :312` as the seventh re-registration and
this is the eighth, and both counts stay written. **The five other rows #1008
moved are not moved again here**, which is re-run rather than carried:
`docs/agent-pipeline.md` reads `:346`, and the four `../findings.md` rows read
`:4206`, `:4208`, `:7202`, `:7423`, `:7484` and `:9226`, because this merge's
§73 correction and its new summary both land **below** the last of them — the §73
correction sits under §74 and the new summary is the file's last section, against
a highest registered row of `:9226` — which the tool confirms by placing all 106.
**On this tree that summary is §87 rather than §86**: #1009's summary took §86 on
`main` in a window after this branch forked, and the rule §87's own numbering note
states gives `main` the number it held first, so the branch's own gives way again.
The rows above are left written for the tree they were measured on and the
`#1008` × `#1009` section at the foot of this page carries this tree's.

**`check_pin_table_by_cited_file.py` reads `43 / 11 / 32`**, superseding the
thirteenth note's `42 / 11 / 31` and the twelfth's `41 / 11 / 30` beside
themselves rather than into them. **The step is two suites, not one, and that is
the first time on this axis**: #845's `ec/tools/test_trace_xdata_refs.py` and
#1008's `ec/tools/test_census_index_third_column_edits.py` each landed beside
#978's on their own side of this merge, each measured `42 / 11 / 31` against a
tree the other side's suite was not on, and each was right. Neither is named by a
pin — both write-ups cite their suite *by path* and never as
`test_trace_xdata_refs.py:NNN` or `test_census_index_third_column_edits.py:NNN` —
so the pin count stays **106** and `len(files) - len(tail)` stays **11** on the
merged tree too, and the tail simply takes the 43rd file. That suite's own
asserts are re-set to the measured value rather than argued, with the superseded
`42 / 11 / 31` left written in the same shape the sixth through tenth steps left
theirs. **`check_pin_table_rows.py` reads 106 rows, 106 records, 106 placed, all
seven classes 0**, and the verdict tally below the table — `43`/`2`/`19`/`10`/`32`
— is unmoved by either landing, which is what a re-registration is: same pin,
same reading, new line.

**The standing red set is one again, and this merge was briefly the reason it was
two.** `ec/tools/test_check_pin_table_rows.py` read `FAILED (failures=4)` while
the row still named `:312` and is **green at 36** with `:354`; as the thirteenth
note records, the four is a function of the row naming any line the file no longer
has rather than a count of anything, so it moves with the staleness and not with
the merge. The one that remains is `ec/tools/test_check_cluster_citations.py` —
48 tests, the single failure, on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` with the same two `0x0464`/`0x0465`
disagreements against `main-ec-145` — re-run here on a clean `origin/main`
worktree at `5881153d`, where it fails identically, so neither #1008 nor #845
caused it and neither fixes it.
‡ **What the tree carrying both #890 and #900 moved, re-registered against it,
and still no count.** The *cited* targets are this branch's, because #890's 25
lines are what moved them; the *citing* lines are likewise this tree's, because
neither issue had them. Four rows re-registered: `xdata-moved-ranks-fall.md`'s
second and third at `:352` and `:364` on the branch and `:383` and `:395` on
main are at **`:404` and `:416`** here, and `../findings.md`'s `:7364` and
`:7425` and [`../../tools/README.md`](../../tools/README.md)'s `:157` — stale
on `main` before this branch, by #900's edits to those two files — are at
**`:7369`, `:7430` and `:159`**. **The one figure this branch does move is the
`read N markdown file(s)` line of the transcript above, `143` → `144`:** #890
added `docs/findings/xdata-write-direction-correction.md` and #900 added no
markdown file at all — its `142` → `143` was a correction of a stale
transcript, since the tool reports `143` on the tree this branch forked from as
well as on `main` — and the new file carries no `test_*.py:NNN` pin, which is
why 69/24/44/40 and 53/16 are untouched while the denominator moved. The three
prose places that name `tools/README.md:157` are repointed with the row. **The
`:7369` and `:7430` this note registers were not moved again by either merge
after it; `#771`'s is the one that did, by exactly one line each, to the
`:7370` and `:7431` the table above carries.**

§ **And here a repoint *does* move counts, which is what separates it from the two
legends above, and the table is re-read rather than re-spelled.** Issue #930
repointed finding 7's two rows off `:563` and onto `:588` — the line the `> 300`
floor is on — so both **carry** again at shape `assertion`, the target count is
**57** rather than 58, the carry count is **50** rather than 48, and the number
that do not carry is **eleven** rather than thirteen. The headcount does **not**
move: 105 occurrences and 78 spellings come back identical, because the change
re-spelled two rows and neither added nor deleted one, and that is the check this
table is for. The rows' *citing* lines stayed at `:212` and `:323` without being
re-registered, which is why the write-up's edit was kept line-count-neutral above
the second of them; the two rows were the only ones in that file that moved, and
`xdata-moved-ranks-key-collision.md` §5's amendment is taken back in place beside
them per §4a-4d. **The one citing line this merge moved is the row for
finding 8's half in [`../findings.md`](../findings.md) §69, `9028` → `9046` at
the `#885 × #771` merge → `9059` on the tree #930 first measured → `9077`
here**, because #771's §70 and #930's own correction paragraph both landed in
that file above it; it is re-registered above and the superseded `9028` stays
written bare in the `#888 × #885` note at the foot of this file that measured it,
per §4a-4d. **Both of this note's "stayed put" figures have since moved, and
that is the `> 300` floor's two rows rather than anything #930 did**: the merged
tree this pass lands in carries #929's own edits to
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md) above
both of its sentences, so the pair is at **`:278` and `:389`** and not `:212`
and `:323` — the repoint was line-count-neutral on #930's tree and is not
line-count-neutral here, which is the same cause as the `9077` → `9114` step the
`#929` merge note records. The table above and finding 7 carry the new lines,
and `:212`/`:323` stay written here because they were true of the tree this note
measured.
**The six `> 300` pins of findings 6 and 8 are not repointed here** and
are #920's, for the provenance reason finding 7 below now records. The superseded
number is written bare throughout for the reason
[`../findings.md`](../findings.md) §65 gives — spelling it would be the 79th
spelling in the census the correction is reporting on, and would move the very
figures it reports. `Why no checker` is unchanged: none of this is a verdict, and
the two rows carry because a reader looked at the two lines, not because the tool
decided anything.

**The "carries in part" row is gone from this tree, and the argument it carried
is not.** It was the sharpest of the three qualified values:
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):433
cited `:286` for *two* figures in the suite's docstring and named the second,
while [`../findings.md`](../findings.md):7191 says `:286` holds a third-generation
figure and `:286` was the second — **one line, two verdicts, and nothing
mechanical in the tree able to tell them apart**, which was the argument for the
split in one sentence. #850 repointed `:433` to `:307`, which carries, so
`:286` now has one verdict rather than two. The category is empty here and the
second half of the split is still right; what is lost is a worked example of it,
and it is named rather than papered over.

## The nineteen that do not carry

*(The nine this section was written with, the two the #888 × #890 merge added and
the two the #888 × #885 one added beside them are all below — but the #888 × #890
pair is no longer *on* the list, because #930 repointed it and it carries again.
The `9`s, the `11`s and the `13` in the lead paragraphs that the three headings
before this one carried are kept visible in the italicised notes under it rather
than edited out, per `../findings.md` §4a-4d; item 7 below is what the repointed
pair now reads as. **The #962 merge added item 9 and moved the count from the
eleven to the nineteen**, which is the second time this heading has moved in
this direction after #930's thirteen to eleven: #962 shifted
`test_xdata_cluster_names.py` by 34 lines, and the eight pins that noticed name
four different targets, three of which are the `> 300` assertion findings 6, 7
and 8 are about — the same assertion, wrong for the third time, by a third
route. **No item below items 1–8 changed verdict and none was deleted**, on this
merge's own terms: a line shift is what turns an item on, not off, and repointing
is what turns one off again.)*

**Nine items below and twenty-one pins, of which item 7's two now carry, so the
list is eight items and nineteen pins — and finding 6 is the reason the count is
not one higher than the items** — finding 1 was one of the six when this was
written and #850
repointed it into carrying, so it is kept struck through rather than deleted.
Finding 4 is one stale pin written twice, in two files, describing the same
removed constant; finding 6 is one moved assertion written **four** times across
**two** files; finding 7 is the same assertion written **twice** more by #888 —
now repointed and carrying, and kept on the list for the record rather than
deleted from it;
finding 8 the same assertion written **twice** again by #885 — **eight pins
naming one line, in five files**, and the reason eleven pins sit under seven
items; and
finding 9 eight pins naming **four** targets in one file, moved by this merge.
**The issue's own citing-line reference is not among
the nineteen** — it
was finding 1, and on this tree it carries, which is the one claim of the issue's
two that #850's own change turned into a `carries` rather than a
`does not carry`. Five of the thirteen carried over from the six this section
recorded; **four are #850's** (all four finding 6), **two are #888's** (both
finding 7), **two are #885's** (both finding 8) and **eight are #962's** (all
eight finding 9).
**Finding 7 was the eleventh and finding 8 the thirteenth, and they were the only
two a merge in this repository produced rather than found lying in the tree** —
two pins that were *born* correct and were made wrong, in the same commit that
made this file's own §2 transcription stale, by moving the line they name, and
two that were born correct against a line another branch had already moved. The
count was thirteen because four pins that carried on their own trees stopped
carrying here, not because anything about the other nine moved. **#930 repointed
finding 7's pair and they carry again, so the count fell by two, thirteen to the
eleven** — and the eleven that are left are the same pins this section's list
names, one for one, because the pair's return to `carries` took it off the list
rather than repairing anything in it.

*(The lead paragraph as #850's merge wrote it — **six items and nine pins**, one
struck through, four new and all four #850's — is the record of that tree and is
carried in this note rather than edited out of the sentence above, per
`../findings.md` §4a-4d, and the heading's `9` is its record in the same way.
What moved at the #888 × #890 merge is the heading and the two sentences that
follow it, and nothing in the list below items 1–6 changed verdict; what moved
at the #888 × #885 one is the heading, those two sentences and the addition of
item 8. **The two sets are disjoint** — `:563` and `:392`
are different lines in different files — so nothing in finding 7 changed verdict
when finding 8 landed beside it. What moved at #930 is the heading, the eleven
in place of the thirteen, and item 7's verdict: **no item below items 1–6
changed, and no item was deleted, because repointing is what turns an item off
this list** — which is why item 7 is kept here struck into the record rather than
struck out of it.)*

1. ~~**[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):403**
   — `test_xdata_cluster_names.py:355-370`~~ — **repointed by #850 and now
   carrying.** It cited `:355-370`, which is §6a's assertion block, for
   `test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key`; that
   case is at **`:630`** and #850 repointed the sentence to `:626-641`, which does
   contain it. The span opens four lines early on the previous case's message,
   which is a note rather than a defect: the claim is carried. **The issue places
   this pin at `:154-157`; it is at `:403`.** The claim is right and the line
   number was not, which is the whole argument, in the register
   `registers.yaml` and `check_cluster_citations.py` already use.
2. **[`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99** —
   `ec/tools/test_grade_0751_isolation.py:2232-2233`, cited for the sentence
   *"a capture carrying one is still fatal for the whole run however it got
   there."* That sentence is a **comment at `:2687`**, above
   `test_a_mark_that_is_not_one_of_the_forms_is_an_error`. `:2232-2233` is
   `self.assertEqual(section.count("from the <value> in these files' §6 names"), 2)`,
   which is about a different case entirely. **New when this was written — the
   issue did not name it**, and the file that names it is #498's, not this
   issue's.
3. **[`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226**
   — `ec/tools/test_grade_0751_isolation.py:16`, cited for *"the suite locates
   its fixtures off `Path(__file__).parent`"*. `:16` is a **blank line**;
   `HERE = Path(__file__).parent` is at **`:17`**. Off by one, on the same file,
   one line above the span its sibling citation at
   [`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md):263 gets right
   (`:16-20`, which does cover the `spec_from_file_location` block).
4. **[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):392**
   and **[`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):1341**
   — both name `test_xdata_cluster_names.py:54` for `GUARD`, the literal the
   `--no-eq-guard` recipe used to patch. `:54` is now `with open(path,
   newline="") as f:`, and `GUARD` **is not in the file at all**: #753 dropped the
   copy-and-patch recipe and replaced it with `--no-eq-guard`. The same stale
   pin, written twice, in two files, both describing a recipe that no longer
   exists. *(`:54` was a blank line on the tree this was written on; #850's
   239 lines into the suite put a statement there. The pin is the same defect
   either way and is now wrong in a second way as well.)*
5. **[`../findings.md`](../findings.md):7191** — `test_xdata_cluster_names.py:286`,
   cited for *"`…:286` carries a third-generation figure in its docstring"*.
   `:286` is `self.assertEqual(names, {})`; the third generation, *"427 clusters
   become 439, 48 … 379"*, is at `:307-309` and the second, *"430 → 439 with 64
   ranks intact and 366 changed"*, beside it. The sentence names neither.
6. **All four pins are one assertion, and #850 is what moved it.** **`> 300`** —
   `assertGreater(len(moved), 300)` — is at
   [`test_xdata_cluster_names.py:588`](../../ec/tools/test_xdata_cluster_names.py)
   on this tree, and the comment it rests on, *"a regeneration that renumbers
   nothing is not the case the identity columns exist for"*, is at `:584-585`.
   *(`:582-584` is what this item first recorded; the quoted comment is two
   lines, and `:582` is the `def test_the_regeneration_really_moves_the_ranks`
   above them. Re-opened against the merged file, where the two sit eleven lines
   lower than they did on #890's tree.)*
   **#850 put 239 lines into that suite and repointed two citations — the
   checklist's `:183` and nothing else — so four pins elsewhere still name a
   line of §2b's comment for it.** They said `:392` and `:387-389` before #890
   repointed them by +25; **they now say `:417` and `:412-414`, and they are
   wrong in the same way for the same reason, which is that a +25 repoint moves
   a pin without changing what it names:**

   - **[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):401**
     — `:417`, cited as *"`assertGreater(len(moved), 300)` stays at
     [`test_xdata_cluster_names.py:417`]"*. `:417` is a comment about the
     guard-off pd cluster count `51` (`:392` before the repoint) and is not
     where `> 300` is.
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):15** — `:417`, cited
     as *"whether `> 300` at `ec/tools/test_xdata_cluster_names.py:417` still says
     what the comment beside it says it says"*.
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):436** — `:417`, cited
     as *"**It is the first, and `> 300` stays at `test_xdata_cluster_names.py:417`,
     untouched.**"* — `:392` before #890's repoint
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):448** — `:412-414`, cited
     as *"the comment at `test_xdata_cluster_names.py:412-414` asks that a
     regeneration that renumbers nothing is not the case the identity columns
     exist for"*. `:412-414` is three lines of the §2b comment (`:387-389`
     before #890's repoint), and the comment being quoted is at `:584-585`.
   **The first three of the four are sentences this census would have caught
   before #850 landed and did not, because nothing ran it then** — which is this
   file's own argument, one merge later, and the strongest argument in it. The
   fourth is the same defect in a `def`-shaped span. None is repointed here: §7
   below says why, and the re-open condition is unchanged.
7. **NEW, and the only entry here a merge produced rather than found — and, since
   #930, the only entry that has been repointed rather than recorded.**
   **Both
   pins are one line, written twice, in one file** —
   [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):278
   and `:389`, both **naming `test_xdata_cluster_names.py:588` for
   `assertGreater(len(moved), 300)` as of issue #930.** **On #888's tree that was
   written as `:563` and it was correct**: the floor was at `:563` there, and §5
   of that write-up goes at some length into why a file new to the census must
   cite a line that holds the claim rather than one a superseded record happens
   to mention. **#890 then put 25 lines into that suite above it, moving the
   floor to `:588`, and both pins named
   `("0x0843", ("84", "42"), ("126", "0"))):` — a fixture line — until #930
   repointed them onto the floor.** So the two sentences were defective in
   exactly the way item 6's four are, and they got there the same way, and
   neither #888 nor this census's author saw it happen: the pins were correct
   when written and the line moved underneath them. The `assertion` → `other`
   reclassification in §2's transcript and the `42` → `41` in its target count
   were the same two rows and nothing else, and **the repoint takes both back** —
   `assertion` again, 41 again, both rows carrying again. **It is no longer "not
   repointed here"**, for the reason §7 gives rather than against it: the merge
   that makes citing prose stale does not repoint it, the follow-up list does,
   and this is that list's entry being worked. The argument, the before-and-after
   run and why the six of items 6 and 8 were deliberately left in the same pass
   are
   [`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md); the superseded
   number is written bare there and in that write-up, for the reason
   [`../findings.md`](../findings.md) §65 gives.

   **The last two bullets' citing lines are the second repointing of these two
   rows, and all three values stay in the table above rather than being
   deleted.** The file read `:319`/`:331` when this table was written; **#885,
   working from the pre-#889 base, repointed them to `:331`/`:343` and was right
   for its own tree**; **#900 repointed them to `:383`/`:395` and was right for
   its own**; and **#890's own twenty-five lines into the fall write-up put them
   at `:404`/`:416` on the tree that merge produced, re-measured by
   `--verbose` after the merge.** #885's forty-one lines into that write-up all
   land below `:395`, so its side did not move the pair a second time — which is
   where the two sides came out differently, and the `#885` merge note below says
   the same of it at length. **The pair has since been repointed twice more, to
   `:415`/`:427` and then to the `:436`/`:448` the table above carries**, both
   times by another merge landing on this file rather than by either side being
   wrong; the `#929` merge note at the foot of this file is where the last of
   those is recorded, and the `:404`/`:416` above is the tree that produced them
   rather than a value this table contradicts.
8. **NEW, and both pins are the same assertion finding 6 names, one merge
   later.** #885's merge added two more citations of
   `ec/tools/test_xdata_cluster_names.py:392`, one in
   [`../findings.md`](../findings.md) §69 and one in
   [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622, and
   **both were correct on the tree they were written on** — `:392` was the
   `assertGreater` there, and #885's own write-up says so and reports both as
   carrying. They are the same defect finding 6 records, arrived at without
   anyone moving a line: #850 moved the assertion in the same window, the two
   branches never shared a tree, and each was written against a `:392` that was
   right for it. **`:392` names a different line on every tree since** — a §2b
   comment where #885 read it, `decreased, {},` on the tree this file now sits
   in, where #890 has since put the assertion that no address's `write`
   decreases — so both land on a line that does not carry the claim, and land on
   a *different* wrong line on the two trees.

   **This is the sharpest result in the file, and it is a measure of the method
   rather than of either branch.** #885 predicted its own two pins would carry
   and the prediction was right *for its tree*; #850 predicted nothing and was
   right for its own; #888 predicted the same for its two and was right for
   *its* tree too, and wrong here for the mirror-image reason. None of the three
   was wrong. A census run only on the merged tree
   cannot tell a pin that was always wrong from one that a concurrent merge made
   wrong, so this section records the cause rather than the verdict alone: **six
   pins in four files now name `:392`, `:417` or `:412-414` for the `> 300`
   assertion, which is at `:588`**, four of them because #850 moved it and two
   because a
   branch written against the old line landed beside it; **and two more, in a
   fifth file, name `:563` for the same assertion, which is finding 7 and is
   counted apart because the line moved under those rather than having been
   moved before they were written.** None of the eight is repointed here,
   for the reason the follow-up list below gives.
9. **NEW at the #962 merge, and the only entry here with no `> 300` in it.**
   Eight pins across **four** citing files name **four different targets in one
   file**, every one of them correct before this merge: adding a class to
   `test_xdata_cluster_names.py` and correcting a docstring above it shifted
   every line below by 34, and these are the pins that noticed. Three name
   `:347` for `test_the_census_is_the_one_6a_measured` (**now `:381`**) —
   [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):20
   and `:156`, and
   [`xdata-green-set.md`](xdata-green-set.md):283. Three name `:596` for the
   `> 300` floor (**now `:630`**) —
   [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):334,
   and
   [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):278
   and `:389`. One names `:149-153` for
   `test_changed_membership_is_a_new_key_not_a_collision` (**now `:183`**) and
   one names `:910-916` for `test_every_row_records_the_evidence_for_its_name`
   (**now `:944`**), both in
   [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md). **The
   three `:596` pins are finding 6's assertion, one merge later and for a
   different reason** — #850 and #885 moved it, and this merge moved it again
   under citations that had already been repointed onto it, so the same
   assertion is now wrong for the third time by three different routes. None of
   the eight is repointed here, for the reason the follow-up list below gives;
   each verdict cell names the target's new line so a re-pointer does not have
   to re-derive it.

## The ten that record another line, and why that is the blocker

These are **correct sentences about a line that has moved**, and the reason each
one is right is that `docs/findings.md` §4a-4d requires the superseded value to
stay visible beside its correction. A checker with no rule for them reddens on
sentences that are true, and [`prose-line-citations-held.md`](prose-line-citations-held.md)
§"The one judgement call" is explicit that this is *"the surest way to get a
check switched off, and then nothing would be left."*

**The class has at least eight unmarked shapes of supersession, and the two that
`check_citation_lines.py` already knows — a `>`-opened line and a paragraph
opening with `CORRECTION` — catch exactly two of the ten below, and the two they
catch are both sound citations.** That is the finding, and it is why the verdict
is no checker rather than a deferral:

| shape | where | caught by `check_citation_lines.py`'s vocabulary? |
|---|---|---|
| a repoint list naming the stale value, in running prose | [`../../tools/README.md`](../../tools/README.md):282 — `test_xdata_cluster_names.py:303` → `:307` in four places | **no** |
| a "deliberately not fixed" bullet naming the wrong pin | [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):446 | **no** |
| a "the citation check caught it here" sentence | [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):579 — `:513` named *because* it was the wrong line | **no** |
| an "At the time of writing, `file:NNN`:" lead-in to a quoted block | [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):25 — **the pin is gone, the lead-in is not**: #780 rewrote it as *"At the time of writing the file read:"* and re-pointed the record to `:47`, so the shape survives here without the `file:NNN` that made it a record, and `:47` is the seventh row's shape | **no** |
| a pin qualified by a commit — *"…(`:3608` at `c9e72c1`)"* | [`0751-capture-row-shape.md`](0751-capture-row-shape.md):41 | **no** |
| a dated findings section describing the tree as it was | [`../findings.md`](../findings.md):4206 and `:4208`, §16's pre-#186 fakes | **no** |
| a blockquote correction naming the post-fix location | [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645 | yes — and it is one of the **carries** |
| a section kept whole per §4a-4d, so a pre-#850 value is quoted as it stood | [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):177 — `:307` inside *The residual* , which the branch's own header marks as a record of a tree the file no longer has | **no** |
| a merged-tree note naming both the old and the new value in one sentence | [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):189 — *"were at `:307` on the pre-#850 file and are at `:339` on this one"* | **no** |
| the same sentence, quoted verbatim inside a `>` block | [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):165 | yes — and it is one of the **records** |

**Eight of the ten are invisible to the vocabulary that already works**, and the
two it does catch are correct sentences. **The fourth row is the one this merge
moves, and neither of those two counts moves with it**: #780 rewrote that
write-up's lead-in and re-pointed the record it named, so the shape keeps its
instance and the record is now a line the seventh row's shape already describes
— one shape listed twice, ten records still, and the "eight" and the "two" are
counts of the ten *records* rather than of the distinct shapes beside them,
which is what they were before this merge too.** That is not a rule waiting to be
written; it is a shape per author, and the last two rows are the proof that the
blockquote rule is not merely safe here but *insufficient*: the same superseded
value is caught or missed depending only on whether the sentence that quotes it
was written with a `>` in front of it. **The three #850 rows are the sharpest of
the ten**, because all three are the *same* sentence pattern in one tree's own
prose and the two ends of it are two different verdicts.

**What is deliberately not done about them.** Repointing the citing prose is
twenty-six files' worth of edits against open agent PRs, and **every one of
these ten is already recorded in place** — that is what makes each of them
right, and
`xdata-4-4-identity-rederivation.md`'s own "Deliberately not fixed" list says
outright that deciding *what a drifted pin was meant to name* is a next pass's
call and not a merge's. This branch takes no position on that and edits no
citing prose. The table above is the hand-off.

## Why no checker

The issue asks whether one is warranted and says that if it needs a judgement
this issue does not make, to say so rather than shipping a checker that reddens
on the next merge. **It needs that judgement, and the measurement says so rather
than my having to assert it.** Four things, in the order they decide it:

1. **The pins are not one kind of thing.** 5 name a `def test_` line, 19 an
   assertion, 10 a comment, **6 a blank line** and 34 something else. The
   citation means "the line where this claim is decided", and that line is the
   test header in 5 cases out of 74. A `def`-anchored rule is wrong; an
   assertion-anchored rule is wrong; a blank-line-anchored rule is worse than
   both, because the blank is an artefact of the span convention and 6 of them
   move whenever a line is inserted one line above. **No single anchor covers
   them and the range form needs a third rule on top.** *(`11`/`9`/`26` and `57`
   are what this item was written with; #771's write-up took the split to
   `17`/`10`/`35` over `73`, #930's repoint to the `19`/`10`/`33` and #778's
   merge to the `19`/`10`/`34` over `74` above, and the five figures are
   re-measured rather than derived.)*
2. **Supersession is unmarked prose in this class, and that is the blocker.**
   `check_citation_lines.py` gets away with a two-shape skip because a
   supersession there *has* a shape. Here it does not: eight of the ten
   records above are ordinary running prose or a bullet, and
   [`../../tools/README.md`](../../tools/README.md):282 cites `:303` **because
   `:303` is the stale value it is reporting**. A checker with no skip rule
   reddens on every one of the ten, and with the rule
   `check_citation_lines.py` already has it still reddens on eight more — the
   two it catches are the two `>`-opened rows, and both are correct sentences.
   *("reddens on two … and five more" is what this said with seven records and
   one `>`-opened row; the eight above is what the table now says, and the
   table is the thing a reader can check.)*
3. **A resolver has to read two spellings, and one of them is a judgement.**
   `ec/annotations/xdata-register-map.md`'s `../tools/…` is only a path once you
   know the page writes its paths relative to itself; a resolver that reads
   against the tree alone reports two sound pins as missing files. The tool here
   reads both and prints which answered, and a *checker* could not: it would have
   to pick, and a wrong pick reads as a broken citation.
4. **There is nothing for a file-level rule to catch.** `out-of-range` is 0,
   `unresolved-path` is 0 and `ambiguous-path` is 0. Every pin in the tree names
   a file that exists and a span it has. **The entire defect is in the
   line-*content* half**, and that half is the one a rule cannot make — as
   finding 6 above shows, one assertion and four sentences give four different
   verdicts, none of them mechanically decidable. Findings 7 and 8 make the same
   point from the other side: **eight sentences naming one assertion, written by
   three branches that never shared a tree, all of them right where they were
   written and all of them wrong here** — and nothing in a merged tree
   distinguishes the two cases.

**So the tool ships as a census that renders no verdict and never fails on
drift**, and the re-open condition is written down rather than left to a later
reader: a checker becomes writable when **either** this class is taught a
supersession marker its own authors use — a `RECORDED:` prefix, say, which eight
of the ten records above could carry today with a two-word edit each —
**or** a decision is taken that pins into a test file must name a `def` and be
held as one, which is a policy about how this repository writes citations
rather than a fact about the pins. Neither is a fact about the tree, so neither
is this issue's to decide, and the issue itself says so.

## What this does not check

In the same register as every other checker here, and the same caveat: each of
these is **"not done by this method", never "absent"**.

- **Whether the cited line still carries the claim.** The whole second half. It
  is this file's table and it was made by reading; the tool renders no verdict on
  it, and a tool that guessed at the second half would be exactly the overclaim
  `CLAUDE.md` forbids.
- **A `.py:NNN` pin into anything that is not a `test_*.py`.** Measured over the
  same files with the same extractor and the test class excluded: **373
  occurrences, 229 distinct `(file, line)` targets, 34 files** —
  `xdata_register_map.py` 77, `grade_0751_isolation.py` 46,
  `pd_index_geometry.py` 39, `ec_watch.py` 34. The planning stage's estimate of
  this wider class was 180 occurrences and 39 targets; **that does not reproduce
  under any of four narrower definitions I tried**, so the figure above is the
  one recorded and the estimate is not used. This class is not owned here either
  — see the follow-ups.
- **A pin written without a path**, the `:444-448` shorthand a page uses once the
  file is named in the sentence above. There is no file to resolve it against
  and reading it would mean guessing which of the thirty-five test files was
  meant.
- **A blockquote.** A `>`-opened line is read, not skipped, and
  [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645
  is the one pin in this class that a supersession skip would have passed over
  and that turns out to be **correct** — evidence that the skip is not merely
  safe here but insufficient.
- **A markdown-to-markdown pin.** The issue's second item is one —
  [`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md):221 cites
  `xdata-cluster-names-guard-off-recipe.md:406-407` for the sentence *"the cheap
  tier not running the tool's `--check`/`--self-test`, which are red on `main`"*,
  which is at **`:446-447`** (inside the bullet at `:445-448`);
  `:406-407` is two lines of a `>`-quoted paragraph about where that file's dated
  correction blocks are. **Both of the issue's claims are confirmed exactly as
  filed, and this one is not in this census** because the class here is a pin into
  a *test file*; a markdown-to-markdown checker is `check_citation_lines.py`'s own
  next step and is named as such below. The class is therefore **wider than
  `tools/README.md`'s eighth-thing paragraph says**, and a fix scoped to `.py`
  targets would miss this one.
- **Whether the prose is right about the claim even where the line is right.**
  Only that the line is the one the sentence was written for.

## Verified on this tree

```console
$ python3 ec/tools/census_test_line_pins.py
$ echo $?
0
$ python3 -m unittest discover -s ec/tools -p test_census_test_line_pins.py
.........................................
Ran 41 tests in 1.258s

OK
$ bash tools/run-tests.sh
35 suite(s) run, 1076 tests; one or more FAILED.
```

**The one red suite is not this branch's.** It is
`ec/tools/test_check_cluster_citations.py`, 48 cases, on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220` with the same two
`0x0464`/`0x0465` cluster disagreements `tools/README.md` has named as
reproducing on a clean `origin/main` since #822. **Confirmed rather than assumed
at the #885 merge, and again here**: the same suite fails the same single case
with the same two citations on a clean `origin/main` worktree, and
`check_cluster_citations.py` reports them before and after this merge. This
change touches no cluster,
no CSV and no membership, and neither causes it nor fixes it.

The suite is 41 cases and it is the reason the two directions are demonstrated
rather than asserted: a run that located nothing reports it and exits non-zero,
**and** a run whose every pin is broken still exits zero, with a case for each.
`ec/annotations/registers.yaml` is untouched — no `status:` moved, no row edited,
no CSV or `xdata-symbols.csv` regenerated, no Ghidra export re-run, no
`.gpr`/`.rep` opened. **The census reads text.**

**Red demonstrated, not asserted.** On a scratch copy holding
`ec/tools/census_test_line_pins.py`, the real
`ec/tools/test_xdata_cluster_names.py` and the real
[`xdata-green-set.md`](xdata-green-set.md), moving that page's pin
`ec/tools/test_xdata_cluster_names.py:339` to `:340` — the one-line change a
merge above the `def` makes — the tool reports the new landing and **still exits
0**. *(Re-run at the #850/#887 merge, because #850 is what moved the `def` from
`:307` to `:339`; the method, the shape change and the exit status are the same
three as the `:307` → `:308` pair this replaced, and the old pair is left here
as the record of the tree it was measured on per §4a-4d.)*

```console
$ python3 ec/tools/census_test_line_pins.py --verbose     # before
  docs/findings/xdata-green-set.md:283  ec/tools/test_xdata_cluster_names.py:339  resolves  …  the pin names the path (by-path)
      def test_    def test_the_census_is_the_one_6a_measured(self):
$ python3 ec/tools/census_test_line_pins.py --verbose     # after :339 -> :340
  docs/findings/xdata-green-set.md:283  ec/tools/test_xdata_cluster_names.py:340  resolves  …  the pin names the path (by-path)
      comment     # The only case in this class that holds the run to a published figure
$ echo $?
0
```

That is the [`prose-line-citations-held.md`](prose-line-citations-held.md)'s
`:817` → `:818` demonstration, on the class this issue exists to survive: **the
shape changed from a `def` to a comment and nothing turned red.** A checker here
would have had to decide whether that is a defect, which is the judgement above.

### The one other file this branch had to touch, and why

`ec/tools/test_check_doc_figure_pins.py` went **red on this branch landing**, with
five failures, and the cause is this suite rather than the tree:
`check_doc_figure_pins.py` searches *every* module in `ec/tools/` for an int
inside an asserting call and reads a hit as a pin, and one of this census's
committed-tree figures was **`50`** — so the moment the suite landed, the census's
own count made the checklist's §2b console-block cluster count `50` (an unrelated
figure that happens to be the same integer) measure `held-by-check-literal`, and
§2b's own `unheld` marking disagreed with the measurement. *(That figure is
**`69`** after #850's merge, **`71`** after #888's, **`73`** on the tree the
`#888` × `#885` merge produced and **`106`** on the tree this now lands in, for
the reason the note at the foot of this file gives; the exclusion is what keeps it
from mattering, which is the point of an exclusion rather than of the number — and
it is **preventive rather than current** on this tree, since `106` is not a figure
§2b's tables hold, which is checked rather than assumed: the tool reads
**18 figure(s), 18 measured held, 0 measured unheld** over
**190 literal(s) inside a check**, the same run `main` gives.)*
§2b's own `unheld` marking disagreed with the measurement. *(That figure is:
**`71`** on the tree #885 merged into, `69` at the #850 merge and `50` when the
suite landed — for the reason the note at the foot of this file gives. `71`
collides with nothing in §2b, so the measurement below is re-run on the merged
tree and not carried over. The exclusion is what keeps the question from
mattering at all, which is the point of an exclusion rather than of the
number.)*

That is not a new defect: it is the one `check_doc_figure_pins.py` already
anticipates in its own `SELF_MODULES` comment — *"nothing mechanical can tell a
test that pins a figure against the census from one that pins it against this
tool's verdict about the census — they are the same call shape, and only the
second is circular"* — and #849's own audit would have hit the identical thing if
its suite had named `390`. The general rule is the one the exclusion already
states: **a module that publishes a figure another tool measures cannot also be
the evidence for it.** So the two census modules join that tuple, which is a
constant and a docstring line, and nothing else in that tool moves: on the tree
this was written on §2b went back to **eight held and ten unheld** with a printed
denominator of **`175 literal(s) inside a check`**, which is what
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) quotes, so that transcript
is still the record of the tree it was measured on. *(Neither figure is the
merged tree's, and neither is claimed to be: §2b reads **eighteen held, none
unheld** over **`190 literal(s)`** there because #850 gave each of the ten
unheld figures a literal at an `assertEqual`, which is a different cause with a
different answer. The exclusion did its job either way — without it the census's
own `73` would have been searched like any other integer in `ec/tools/`.)*

**The alternative was to write this suite so it never says `50`, and that is the
accommodation worth naming.** A count that avoids a search is a count that was
chosen to be invisible, and the next reader would have no way to know the figure
was shaped rather than measured. The exclusion is one line, it is the rule the
tool already states, and it costs a denominator that was going to move anyway.

### Merged-tree note (2026-09-26, #891 landing beside #887, #850 and #889)

**Two of this table's own citing lines went stale in the merge, and they are
repointed — which is follow-up 1 below happening to this write-up rather than to
the pages that follow-up names.** The first column is the *citing* line. The
two rows naming `xdata-moved-ranks-fall.md` said `:319` and `:331`, and the
citations they name now sit at `:383` and `:395`; the third row, `:15`, is above
every insertion either merge makes and did not move. **The two were already
stale on `main` before this merge, by twelve lines rather than by sixty-four**,
because #889 put its `deciles()` note into that write-up at `:328` — ahead of
both — and re-measured the census's counts and its `test_*.py` targets without
re-measuring this file's citing column, which the tool cannot see. That is the
exclusion below's price paid once already, and this merge is where it is paid
twice: the merged file names `:383` and `:395`, re-measured against the merged
file, and the three places this file's own prose names the same two citing lines
— finding 6's third and fourth bullets and follow-up 1's `xdata-moved-ranks-fall.md`
pin — are repointed with them so the table and the prose agree.

**Correction to the sentence above, made at the #885 merge: it named three
places and the tree carried two.** Finding 6's third and fourth bullets were
repointed to `:383`/`:395`; **follow-up 1's `xdata-moved-ranks-fall.md` pin still
read `:331` in this note's own tree**, which was the pre-#889 value the same note
calls stale two paragraphs up. It reads `:395` now, and the `#885` merge note
below carries the third repointing. The claim was not "not found by this method"
— it was checked and the check came back short, which is the only kind of
correction §4a-4d is for.

**Neither the tool's figures nor this table's verdicts move with any of it**,
and that is the shape of the defect rather than a coincidence: a citing line is
not a pin. `census_test_line_pins.py` re-run on the merged tree prints `69
pin(s) in 24 markdown file(s): 44 distinct spelling(s), 40 distinct resolved
target(s)` with `0 out-of-range`, `test_census_test_line_pins.py` is green, and
the verdicts are readings of the *cited* line, which no merge touched. **The
`50` / `37` / `32` this note first carried is the branch's tree**, measured
before #850's nineteen new `test_*.py:NNN` citations were beside it; the `69` /
`44` / `40` the suite pins is the merged tree's, and #891 moves neither.

**What found them was a recount of the sibling class, and the exclusion this
file makes is why nothing here did.** The grep over
`xdata-moved-ranks-fall.md` that `tools/README.md`'s merged-tree notes run
returns **eighteen** on this tree, and **seven of the eighteen are this
file's** — three rows of this table, three bullets of finding 6, and follow-up
1 — because the `):NNN` end of that pattern matches a link followed by a line
number exactly as it matches a citation. The census excludes its own write-up
from its own population, deliberately, so **a pin census cannot see its report
going stale**: the exclusion is right, and this is its price, named here beside
the repointed rows rather than left for the next reader to rediscover. Three
more of the eighteen are #889's three citations — two into this same write-up
(`xdata-decile-small-set-contract.md`'s `:199` and `:220`, stale by the same
insertions and repointed to `:208` and `:240`/`:234` for the same reason) and
one into the tool — which is a sibling's write-up this merge broke in the same
way it broke this one's, and `tools/README.md` carries the count. **The
eighteen is #891's tree, and this branch adds three more to it**, all
from the branch's new `xdata-write-direction-correction.md`, which cites the
write-up three times (`:116`/`:129`, `:148` and `:156-165`) and none of the
three moved. The seven that are this file's are still seven — three rows, three
bullets, follow-up 1 — at the re-registered lines above.

### Merged-tree note (2026-09-26, #888 landing beside #891)

**The block at the top of this file re-runs and every one of its numbers is
unchanged, and that is a measurement rather than an absence of one.** #888 and
#891 both rewrote `xdata-moved-ranks-fall.md`; #888's two new pins are already
counted in the `71`/`25`/`45`/`55` block, and #891's rewrite of the same file put
**no** `test_*.py:NNN` pin in it, so the three-way merge is that run byte for
byte — `144` markdown files read included. **The two merges' edits to that one
file therefore do not cancel**: #891 moved the two stale citing lines to `:383`
and `:395`, and #888's two added `cluster_key unique …` lines in §1–§2 plus its
six `ok` lines and their notes in §9 moved them again, to **`:394`** and
**`:406`** on the merged file. This file's table and finding 6's two bullets are
re-measured to those, and follow-up 1's `xdata-moved-ranks-fall.md` pin — which
the #891 note claimed to have repointed and did not — is repointed with them, so
the table and the prose agree for the second time in two merges.

**Two more citing lines were stale and are now fixed, both of them leftovers
rather than anything this merge broke.** Finding 5 and follow-up 1 both named
[`../findings.md`](../findings.md)`:7185` for the "third-generation" pin the table
above carries at **`:7190`**; the tool's own `--verbose` run puts it at 7190 and
both prose references now say so. **Three lines in
`xdata-moved-ranks-second-count.md`** named the fall file at `:458`, `:535` and
`:564` and are repointed to `:469`, `:546` and `:575` — its `:590` citation of
the §9 transcript is above every insertion and did not move, which is a useful
reminder that these citations are not all displaced together. None of this is
visible to the tool, which is the whole subject of the note above: **a citing
line is not a pin, and a pin census cannot see its own report go stale.** The
exclusion stays; the price is paid by re-reading, as it was the last two times.

**The verdicts, the nine that do not carry, the ten that record another line and
the re-open condition are all unchanged.** The re-run changes no *cited* line —
#850's `> 300` floor is at `:563` on this tree whichever file cites it — so the
table's readings are untouched and only its first column moved.

*(**And at the #888 × #890 merge, that last paragraph is the one that does not
survive, along with two of the citing lines above it.** `:563` was the floor on
#888's tree and is at `:588` here, so the re-run *does* change cited lines this
time, and in one file only: `ec/tools/test_xdata_cluster_names.py`. That is
enough to move three of this page's own numbers — the target count 40 → 41, the
shape split `5/13/9/6/22` → `5/11/9/6/24`, and the nine that do not carry → the
eleven, the two new ones being #888's own pins, which #888 measured as carrying
and this merge made not carry. It changes no verdict among the nine #850 left, so
the readings are still untouched where it matters; what moves is the two that
were born correct. **The citing lines moved too**, for the reason the paragraph
above spends itself on: `xdata-moved-ranks-fall.md`'s two stale ones are at
**`:415`** and **`:427`** on the merged file rather than `:394` and `:406`, the
`#891` note's `:383`/`:395` and this note's `:394`/`:406` both being the record
of the trees they were measured on. The table, finding 6's bullets, finding 7
and follow-up 1 are all re-measured to `:415`/`:427`, and
`xdata-moved-ranks-second-count.md`'s four fall-file anchors are repointed a
second time — `:469`/`:546`/`:575`/`:601` → **`:490`/`:567`/`:596`/`:622`** — while
its `:3`, for the fourth time running, is still above every insertion any of
these merges makes. `144` markdown files read becomes `145`.)*

*(**And at issue #930, which does the repointing that note says it is not doing —
and that is the rule, not an exception to it.** That note's last paragraph is the
one place this file says the repointing "lives in that file's follow-up list",
and #930 is that list's finding-7 entry being worked: the two by-name pins move
onto `:588`, the line the `> 300` floor is on. The re-run therefore **does** move
this page's numbers, and moves them the way a correction rather than a merge
does.

**The tree is named first, because the paragraph above is not one.** That note
measures a projected `#888 × #890` merge that never landed; #930 landed on the
`#885 × #771` tree instead, which is `main`, and every figure below is
`census_test_line_pins.py` run on that tree and on no other. The run is **105
pins, 27 files, 78 spellings, 57 targets, 73 resolves, 32 declined,
`5/19/10/6/33`, 148 markdown files read**, against the
`105/27/78/58/73/32/5/17/10/6/35/147` that same tree gives on its own — so each
delta is read off the one run, and not off the `41` targets, `5/11/9/6/24` and
`145` files the note above records. Those belong to that merge, they stay
written as its figures, and they are not to be differenced against these.
Three figures move, and all three are #888's two rows and nothing else:

- **the target count 58 → 57**, because `:588` was already a target under the
  checklist's by-path spelling and `:563` has now lost its last name;
- **the shape split `5/17/10/6/35` → `5/19/10/6/33`**, because `:588` is an
  `assertion` and the fixture row it replaces was an `other` — two `other` become
  two `assertion`, and nothing else in the split moves;
- **the thirteen that do not carry → the eleven, and the carry count 48 → 50**,
  as finding 7's pair comes off the list and carries again. The nine and the
  eleven above are that projected merge's; the thirteen is what the table reads
  on this tree.

**The headcount does not move**, and that is the part worth making: **105**
occurrences, **27** files, **78** spellings, **73** resolves and **32** declined
are identical on the two runs, because two rows changed spelling and neither was
added nor deleted, and the citing lines stayed at `:212` and `:323` without
re-registration. `147` markdown files read becomes `148`, the one figure that
moves because the correction's own write-up is a new file — and that file
carries no `test_*.py:NNN` pin, so the denominator moved and nothing else did.
**The six of findings 6 and 8 are untouched**
and are #920's: they were stale in the tree when this census found them, where
these two were correct when written and were made stale by a merge beside them,
and doing all three in one pass would collapse the distinction the count of
eleven against thirteen exists to record. **No item below items 1–6 changed
verdict, the ten that record another line are unchanged, and `Why no checker`
stands** — the repoint is a reading recorded in the table, and no verdict was
rendered by anything to record it.)*

## What is left, as follow-ups

1. **Repointing the citing prose**, which is the issue's own pointer and is not
   done here for the merge-conflict reason above. In the order the table gives
   them: [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99 →
   `:2687`; [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226
   → `:17`; the two `:54` pins → wherever `GUARD` now is, which is nowhere, so
   the sentence rather than the line is what needs rewriting;
   [`../findings.md`](../findings.md):7191's "third-generation" → the sentence
   has to distinguish `:307-309` from `:286` or drop one of the two; **and the
   four `> 300` pins of finding 6 → `:588`, with
   [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):448 → `:584-585`;
   ~~and the two `:563` pins of finding 7 →
   [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):212
   and `:323` → `:588`, which is the same target the other four name.~~**
   **Each is one line in one file, which is why they are a follow-up and not a
   merge** — and the `> 300` four is a different kind of follow-up from the rest,
   because #850 is the change that made them stale and #850 is the change that
   would have caught them. It is a useful measurement rather than a defect: the
   same merge moved a line and left four sentences naming where it was.
   **Finding 7's two were a third kind of follow-up again, and the only one with
   a different author**: #850's four were stale in the tree when this census
   found them, whereas these two were *correct* when #888 wrote them and were
   made stale by #890's repoint landing beside it in this very merge. Nothing in
   #888 could have known, and nothing repointed them, because the file that
   carries them was new to the census and the tool that would have said so is
   not in any gate. That is this file's own argument — *no checker* — costing
   two pins, and it is the strongest evidence in it for a supersession marker.
   **Issue #942 has since added a tool that says so about the bookkeeping, and
   it does not overturn the sentence above.** `ec/tools/check_pin_table_rows.py`
   holds the 106 rows of the table above to the run this census makes of the
   same markdown, and reports any row it cannot place, any record with no row,
   and any row whose read kind, shape or resolved path differs — all four
   mechanical columns, which are five things this census already computes. **It
   reads no verdict cell, and it exits 0 on a tree where every verdict is
   wrong**, so the checker declined above and the checker that now exists are
   not the same thing: this file's argument is against a rule that *renders a
   verdict*, and this one renders none. What it does not catch is the larger
   half: a verdict that has quietly stopped being true, and a row that is right
   about a stale line. It is not in any gate either — the prepared patch is
   `docs/ci/agent-gates-pin-table-rows.patch` — so until a human lands it, a
   drifted row still arrives in a green tree. The write-up is
   [`pin-table-row-reconciliation.md`](pin-table-row-reconciliation.md).
   **And finding 8's two are a fourth kind again, and the only kind where no
   tree is wrong at any point.** Taken together the eight `> 300` pins are one
   follow-up with four causes: #850's four, #888's two and #885's two all →
   `:588`, with
   [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):436 and `:448` →
   `:584-585`, and the two `:392` pins named in
   [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622 and
   [`../findings.md`](../findings.md) §69 → `:588`, which is the same target the
   other six name. #850 is the change that made four of them stale and the
   change that would have caught them; #890's repoint is the change that made
   the next two stale *after* they had been written correctly; and #885's merge
   added the last two against a `:392` that was right on the tree it was written
   on. It is a useful measurement rather than a defect: one merge moved a line
   and left four sentences naming where it was, a second moved it again and left
   two more born wrong, and a third branch then wrote two more against the same
   number without any of the three trees being wrong.
   **The finding-7 third of that follow-up is now done, at issue #930**, which is
   this list doing the repointing §7 assigns to it rather than any merge doing it
   on its own account: both rows are at `:588` and carry, the two lines stayed at
   `:212` and `:323` so nothing else in that file had to be re-registered, and
   the argument is [`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md).
   **The finding-6 four and the finding-8 two are deliberately still here, and
   are #920's** — same target, different provenance, and doing all three in one
   pass would erase the distinction the thirteen and the eleven exist to record.
   The struck-through half stays struck
   through rather than deleted, per §4a-4d, because it is the record of what this
   list said before the work behind it was done.
2. **The wider `.py:NNN` class** — 373 occurrences, 229 targets, 34 files, on the
   measurement above. It is not owned by this census, not by #870 (which is
   `registers.yaml`'s six `xdata_register_map.py` pointers), and not by
   [`prose-line-citations-held.md`](prose-line-citations-held.md) follow-up 2
   (which is the prose → *source-line* checker beside `citation_frames.py`).
   Whatever censuses it inherits this tool's two readings, because a
   tree-only resolver reports two sound pins in one of those files as missing.
3. **A supersession marker for this class**, if the no-checker verdict above is
   ever revisited. Eight of the ten records are ordinary prose and could each
   carry a two-word marker today; a rule reading that marker is the difference
   between a writable check and a checker that reddens on the tree that records
   the drift it exists to catch.
4. **A markdown-to-markdown pin checker**, for
   [`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md):221's
   `:406-407` → `:446-447` and whatever else that class holds. The issue names
   this one and it is out of scope here for the reason in *What this does not
   check*; it belongs beside `check_citation_lines.py`, which already has the
   supersession vocabulary a markdown-to-markdown rule would need.
5. ~~**The `tools/README.md` totals paragraph is one suite short of the runner**
   and is left that way on purpose.~~ **Done at the #850/#887 merge, and the
   reason this follow-up gave for not doing it is the reason the merge had to.**
   Re-deriving the totals is [`tools-readme-totals.md`](tools-readme-totals.md)'s
   subject and #817's in general, and both #850 and #887 add a *case* or a suite
   without moving that paragraph — so the paragraph went stale twice, in two
   different directions, and the tree it now sits in disagrees with its own
   runner. The totals and the notes that re-derive them are corrected there at
   this merge; what is left of this follow-up is the standing rule the two
   branches agreed on and neither applied, which is that a branch adding a suite
   re-derives the totals in the same PR.
6. **A pin into a non-test `.py` is outside this census entirely**, and the two
   that were open are now decided rather than left to be re-raised. This census's
   population is `test_*.py` — the regex is
   `(?P<path>[\w./-]*test_[a-z0-9_]+\.py)` at
   [`../../ec/tools/census_test_line_pins.py`](../../ec/tools/census_test_line_pins.py):113
   — so a markdown pin into `ec/tools/xdata_moved_ranks.py` is not one of the
   `106`, and the per-pin table cannot take a row for it without turning
   [`check_pin_table_rows.py`](../../ec/tools/check_pin_table_rows.py)'s
   106-against-106 reconciliation red. `tools/README.md`'s
   `xdata_moved_ranks.py:243` and
   [`xdata-write-direction-correction.md`](xdata-write-direction-correction.md)'s
   `:181` sat in exactly that position, which is the mechanical reason three
   merges walked past them: **they are not in the class this file measures.**
   Both are decided in
   [`xdata-moved-ranks-pin-decisions.md`](xdata-moved-ranks-pin-decisions.md),
   which reads the eight markdown lines that spell that one module rather than
   asserting a population no sweep here can see. A general `.py:NNN` resolver is
   follow-up 2 above and is not this file's to write.

## Where the per-merge log used to be, and why it is not here

**This file carried sixteen dated `## The #NNN merge, <date>` sections, one
per merge that touched the table, and they are gone — deliberately, and not because
any of them was wrong.** They are in this file's history; `git log -p` on
`docs/findings/test-line-pin-census.md` has every one.

They were a log, and a log is what git is for. Each section recorded what one
merge did to the table — which rows moved, by how much, and why — and the table
below already carries the accumulated result of all sixteen. Keeping a second
copy of that history in a live file is not preservation, it is a maintenance
obligation: the next merge would append a seventeenth section, in the same
place, for the same reason the other sixteen are there. That is the conflict
this repository keeps re-learning, and it is the reason this file was the most
frequently edited document in the tree after `docs/findings.md` — 22 merges in
40, against 31 for a file that has since been frozen shut.

What survives is the part that is reasoning rather than chronology, and it is
in the sections above: the population, the five-column shape, the verdict
column nobody can derive, the per-pin table itself, and the two sections on
what this does not check. The sixteen are recoverable by hash and by `git
log`; nothing in the tree depends on their line numbers, because this file is
`SELF_DOC` — the census excludes it from its own population — and
`check_pin_table_rows.py` finds the table *structurally*, never by line number,
which is the one decision that made cutting them safe rather than a 1,924-line
citation sweep.

**Do not recreate the log.** A correction to this table is a row change plus,
where the reasoning matters, a paragraph in the section it belongs to. It is
not a new dated section. `docs/findings/no-append-logs.md` is why, measured
across the three files where this has now happened.
