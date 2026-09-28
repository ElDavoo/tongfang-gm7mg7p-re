# `cause`'s membership line counted the population under a pronoun the 408 also answered to, and the two are now named on their own lines (issue #904)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over committed CSVs, with every scratch output under
`/tmp` and `git status --porcelain` printing nothing after the runs. Same
framing as
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):3, whose §2,
§3, §4 and §6 are corrected in place by §5 below.

**The calibration comes first: no published figure moves.** §5 re-derives §1
through §6 of that write-up on the merged tree and gets every one of them back —
`366/64/439`, `315/124/445`, the 71/266/23/40 flip table, `1219` over `1171`,
`22.5%`, and the whole rate table. What is below is that a line of the report
said *"their members"* and the two lines above it were both scoped to a
**different, smaller** set of keys than the figure under them was taken over. A
latent defect in what the output *says*, not a wrong figure in the tree.

## 1. The line, and the two readings it admitted

`cause_report` printed, over the real pair:

```console
    the population: 439 guard-off key(s) in the 430-row pair, 445 in the 439-row pair
    408 of the first reappear in the second under the same key, 31 only in the first, 37 only in the second
    the rank delta of those 408: 0 on 56, +/-1 on 20, +/-2 on 3, further on 329; mean +6.80, range -9..+12
    their members: 1219 membership(s) over 1171 distinct address(es); 274 of them in the page, held 275 time(s) -- one address is in two rows, which is a `pd` holder and a `main-ec` holder of the same byte; the 439-row pair's holds 425
```

`their` has two referents on that page and the output does not say which. Read as
**the 439** — the nearest binding is the `the population:` line three above —
`1219` is the whole older guard-off census's membership, and that is what it is.
Read as **the 408**, on the two intervening lines' scope, the same `1219` is
439 keys' worth printed beside a sentence about 408 keys, and the 31 the
sentence puts *"only in the first"* are inside the number without being marked.

It is load-bearing, which is why it is not a wording nit. The 439 is the
denominator of the rate table's `population` column and the background every
cell's rate is read against; §4 of the derivation write-up then reads the 71's
`37.4%` and the control's `19.1%` against that column's `22.5%`, and its
size-9+ paragraph reads `30.5%` against *"the population's 22.5%."* A reader
who resolves the pronoun the other way recomputes the whole §6 comparison over a
different set, with nothing in the report to tell them.

## 2. The choice: keep the population, and print the 408's own figures beside it

The issue offers two readings — restrict the sum to the 408 and rename it, or
keep the population and print the 408's figures beside it. **The second is
taken**, and the first is not a matter of preference: six things in the tool
already bind the word *population* to the 439-key set, consistently.

| binding | where | what it says |
|---|---|---|
| the `the population:` line | `:973` | `439 guard-off key(s) in the 430-row pair, 445 in the 439-row pair` |
| the rate table's column header | `:1136` | `population` |
| the `0/1219` parenthetical | `:1172-1174` | *"the population's added count is 0 by construction"* |
| the module docstring | `:48-50` | *"the population the rates are read against -- every guard-off key of one generation, and where it lands in the other"* |
| `pair_report`'s collision consequence | `:348` | *"cause's population and its per-program holder index are over the key"* |
| `cause_report`'s own collision consequence | `:970` | *"the population and every rate's `A` column are over the key, so a shared key hides a rank"* |

Renaming the concept to mean the 408 rewrites all six to fix one pronoun. Three
further reasons, which are about the measurement rather than the naming:

1. **The rate rows are membership-weighted.** Each cell column is
   `sum(page)/sum(size)` over that cell's records (`:1142-1143`), so the population
   column has to be too or the column is not comparable to itself. Restricting
   the prose line to the 408 while leaving `members in the page` and `members of
   the added` on 439 would put two denominators for one quantity on the same
   page — the same defect one row lower down.
2. **The cells are drawn from a different key space.** The four cells are the
   400 *committed* shared keys; the population is the guard-off keys. The
   population was already a differently-scoped background rate, and narrowing it
   to the 408 narrows it further without making it the cells' own universe.
3. **§6's surviving result rests on it.** `37.4% / 19.1% / 22.5%` and the
   size-9+ paragraph's `30.5%` are all read against the population. Keeping the
   denominator means the one number everything else is compared to does not move
   on a labelling change.

**Consequence: no figure in any table moves.** What moves is what the output and
the prose *call* each set.

## 3. What the change is

Four edits, all inside `cause_report`. `pair_report`, `across_report`,
`swept_report`, `cause_pd_report`, `rank_shift_report` and `collapse_line` are
untouched, and `pair` and `across` output is byte-identical — checked by
diffing `git show b0b0c09c:ec/tools/xdata_moved_ranks.py` (this change's parent,
which is the file before it — and `main` does not touch it, so the same blob
every earlier merge base named) against the new file over five invocations
including `--rows`, `--swept` and the registers pair, §5. The commit is named
rather than `HEAD` because `HEAD` is this change once it is committed, so a
reader re-running the `HEAD` spelling would diff the file against itself and
get a green that cannot go red.

1. **The sums are hoisted** into one `member_set()` helper, so the membership
   line, `members in the page`'s denominator and `members of the added`'s
   denominator all read the same `pop_memberships` local. They were three
   separate expressions of the same sum before, which is how a line and a table
   can drift apart without either being wrong on its own.
2. **The line names its set.** `their members:` becomes `the population's 439
   key(s) in the 430-row pair:`, restating the key count on the line so nothing
   inherits a bare pronoun from two lines up.
3. **A sibling line, immediately after and at the same indent**, carries the
   reappearing set's own five fields — the same memberships, distinct
   addresses, distinct page addresses, page memberships, the same two-rows
   caveat and the same B-side tail — so the two read as a pair. It does **not**
   open with `the population:`, because the collision-line case at
   `:2038-2046` finds that line by `ln.lstrip().startswith("the population:")`
   and asserts its exact text; the `the population:` line itself is left
   byte-identical.
4. **The one rate cell that does not divide by the population is bracketed on
   the cell** — `[of the 408 that reappear, not of the population]` — in the
   mode's own idiom, the shape the `intact in both` substitution bracket at
   `:1104-1105` already uses.

**On (4) being past the issue's literal ask.** The issue names the membership
line. The `reappears within 2` cell is the same defect one table row down: it is
`rate(spread[0] + spread[1] + spread[2], len(both))` — `79/408` — sitting under a
column header that reads `population`, one row below a `408/439 92.9%` cell
that divides by 439, and §4 of the derivation write-up prints both in one row
labelled `population (439)`. It is fixed the way the file already fixes a
qualifier, and it changes no number. Flagged as an extension rather than folded
in silently.

The real pair after the change:

```console
    the population's 439 key(s) in the 430-row pair: 1219 membership(s) over 1171 distinct address(es); 274 of them in the page, held 275 time(s) -- one address is in two rows, which is a `pd` holder and a `main-ec` holder of the same byte; the 439-row pair's holds 425
    the reappearing 408 key(s) in the 430-row pair: 984 membership(s) over 946 distinct address(es); 137 of them in the page, held 137 time(s); the 439-row pair's holds 425
    the pd side: committed identical (50 pd row(s) either way); guard-off identical (51 pd row(s) either way)
```

and the table's one bracketed cell:

```console
    reappears within 2       10/60  16.7%  29/252  11.5%    0/22   0.0%   35/40  87.5%  79/408  19.4%  [of the 408 that reappear, not of the population]
    members in the page    102/273  37.4%  86/450  19.1%    5/42  11.9%  18/216   8.3% 274/1219  22.5%
```

**The 408's figures are new, and they are not a fifth rate.** `984
membership(s) over 946 distinct address(es)` and `137 ... held 137 time(s)` are
printed beside the population's because the sentences above them are *about*
those keys and a reader who wants to know what they hold had nowhere to look.
The difference — `235` memberships and `225` distinct addresses — is the 31
one-sided keys of the 430-row pair, which is the check that the two lines are
over the sets their labels claim and not over each other.

Note also what the sibling line does **not** carry: the `-- one address is in
two rows` caveat is absent from it, correctly, because 137 page memberships
over 137 distinct page addresses is 137 over 137 — no page address in the
reappearing set's rows is in two of them, so the per-set computation finds no
split to report. The caveat is a per-set fact, and it is now computed per set.

## 4. The cases, and what each is red against

Three cases go into the **existing** `cause` fixture — the A/B/D/E block at
`:1568`-`:1650` — rather than a new fixture pair, because that block already
satisfies the property the issue asks for by construction and a second fixture
would be a second place to keep in step.

`off_d` holds six rows over six keys and `off_e` six over six, and they share
`{k9, k6}`. So **the population is 12 memberships over 10 distinct addresses and
the reappearing set is 6 over 6** — different numbers by construction, because
the four one-sided A rows (`k2` 1, `k10` 2, `k5` 1, `k12` 2) carry six
memberships that are on one line and on no other. B's one-sided rows (`k1` 2,
`k13` 3, `k11` 2, `k14` 3) carry ten. A membership on either set moves one
figure without moving the other, which is the property.

| case | red against |
|---|---|
| the population line reads `12 membership(s) over 10 distinct address(es)` and names the 6 keys; the reappearing line reads `6 membership(s) over 6 distinct address(es)` and names the 2; **on different lines**, and neither figure appears on the other's | a bare pronoun back (the line stops naming its set), and a merge of the two lines back into one — `pop != rep` is what holds that red, since the figures would then share an index |
| the table's population cells still read `2/6 33.3%`, `0/12 0.0%` and `0/12 0.0%` | the `population` column narrowed to the reappearing set, which reads `0/6` in the last two |
| the `reappears within 2` cell still reads `2/2 100.0%` **and** carries the bracket | the bracket dropped, which leaves the 408's denominator under a header naming the 439 |

**Four** mutations were run against a scratch copy of the file, one more than
the three cases above because the first row names two failure modes and each was
tried separately: a bare `their members:` and a merge of the two membership lines
back into one, the `population` column narrowed to the reappearing set, and the
bracket dropped. Each turned its case red with the rest of the run green. The
third table case is a second `check()` rather than a continuation of the second:
the two halves are two denominators and two different fixes, and one case with
two failure modes is a case whose message can only name one of them.

`--self-test` is the command; every case that printed `ok` before this change
still prints `ok`, in the same order, and the three new ones (53 `ok` lines
become 56, one `check()` per table row above) are added beside the existing
population assertions rather than at the tail — which
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) §9 records as
the merge-sensitive property it is.

## 5. The re-derivation, on the merged tree

`xdata-flip-cause-derivation.md` §1's recipe, re-run whole:
`git cat-file -e e169a0e4…^{commit}`, `xdata_register_map.py --check` (**1326
register rows, 439 cluster rows, both exit 0**), `git worktree add --detach
/tmp/xdata-old e169a0e4…`, the two `--no-eq-guard` census runs, then the §2
`cause` invocation. It reproduces:

- `pair` on the old pair: **366 moved, 64 intact, 439 rows**; on the present
  tree **315 / 124 / 445**, and the `351 / 364` and `307 / 311` behind them.
- `cause`'s flip table at **71 / 266 / 23 / 40**, mean `+6.80`, range `-9..+12`.
- `1219 membership(s) over 1171 distinct address(es)`, `274` on the page held
  `275` time(s), `425` in the 439-row pair.
- The whole rate table, cell for cell: `60/71 84.5%`, `252/266 94.7%`,
  `22/23 95.7%`, `40/40 100.0%`, `408/439 92.9%`, `10/60 16.7%`, `29/252 11.5%`,
  `0/22 0.0%`, `35/40 87.5%`, `79/408 19.4%`, `102/273 37.4%`, `86/450 19.1%`,
  `5/42 11.9%`, `18/216 8.3%`, `274/1219 22.5%`, `0/1219 0.0%`.
- **`22.5%` unmoved in the table**, which is the acceptance condition: the
  denominator the §6 comparison rests on does not move on a labelling change.

**What was checked and did not need correcting.** §6's three surviving figures
(`37.4%`, `19.1%`, `22.5%`) and the size-9+ paragraph's `30.5% / 19.1% /
22.5%` are all read against the population and all reproduce; they are left as
they are and this paragraph is the record that they were checked. The `#884`
blockquote in
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
— *"at the rate the whole census reappears at (**79 in 408**)"* — is **not**
among them: *"the whole census"* names the population, and the figure under it
is conditioned on reappearance, which is the same defect §5's other three
instances carry. It gets the same one-line note rather than an exemption, since
the parenthetical pins the number without repairing the label. The §2 console
block of the derivation write-up is left as the record of the run that produced
it and gains a correction block beneath its own, in the shape #929's already
is.

## 6. Declared, and not taken

The issue offers the other reading too: re-derive §1 through §6 with the **408**
as the denominator and move the `22.5%` and the §6 comparison with it. **It is
declined**, for §2's reasons. If a maintainer wants it, it is a separate change,
and this is what it would have to move: the `population` column header and three
of the four rate rows' denominators (`:1154`, `:1168`, `:1171`), the `0/1219`
parenthetical, the `population (439)` row and the `79 in 408` reading in §4 of
the derivation write-up, and the `22.5%` in §6 that the `37.4%` and the
size-9+ paragraph's `30.5%` are both read against. It is not merely a rename
there, which is the honest reason it is not bundled into a label fix.

## 7. What this does not do

- **No CSV, YAML, threshold or gate moves.** `xdata-clusters.csv`,
  `xdata-registers.csv`, `xdata-cluster-names.csv`, `registers.yaml` and every
  annotation CSV are byte-untouched, and no `status:` value changes.
- **No live test, and none is implied.** `cause` reads CSVs and the
  re-derivation is `git worktree` plus two census runs; every file it reads is
  committed text. Nothing here claims a register was read back or a machine was
  observed.
- **Nothing is opened in another repository**, and there is no upstream patch
  here to submit.
- **No new tool, no new mode and no new fixture pair.** `cause` gets no sixth
  flag; the cases belong to the fixture that already satisfies them.
- **`--swept` is untouched.** Its second-holder count over the union, and the
  49 `program=both` rows behind it, are #899's; the two `or` reads are #896's.
  Both are `swept_report()`'s and neither is in the code this change touches.

## 8. The gate run, and what was red before it

`bash tools/run-tests.sh` **is red, and it was red before this change.** The
red set is the same **eleven** tests before and after, established by stashing
the change and re-running rather than by reading a summary: four in
`test_gpu_block_watch`, three in `test_check_eq_guard_citations`, one each in
`test_check_cluster_citations` and `test_check_doc_figure_pins`, and **two in
`test_check_pin_table_rows`** —
`test_the_committed_table_reconciles_and_exits_zero` (the `unplaced-row
docs/agent-pipeline.md:409` whose record is absent) and
`test_every_class_is_zero_on_the_committed_tree` (`'row-without-record': 1`).
The one `xdata-flip-cause-derivation.md` §9 records —
`test_check_cluster_citations`, 1 of its 48 — is among them, and **this change
adds nothing to any of the eleven.** None is in a file this change touches.
The two `test_check_pin_table_rows` cases are the same
`docs/agent-pipeline.md:409` row
[`test-line-pin-census.md`](test-line-pin-census.md) writes a paragraph about
and deliberately leaves alone, so they are documented in one file and counted
in this one; re-counting the set on `origin/main` and on this change's parent
gives the same eleven, which is what makes "adds nothing" a measurement rather
than an assertion.

> **Two rows of the per-pin table were re-anchored.** The document corrections
> §5 records insert prose *above* two existing `test_*.py:NNN` citations, so
> the **citing** lines those two rows record moved, and
> `check_pin_table_rows.py` reports a row the run does not describe — the
> sixth re-anchoring the tool's own docstring names, and the reason it exists.
> The derivation write-up's row moved `:401` → `:469`, and `docs/findings.md`'s
> §62 row moved twice — `:9411` → `:9437` by `main`'s `#489` correction
> paragraph and then `:9437` → `:9461` by this change's own, both of them above
> it — with each shift recorded beside the row it moves.
> **Pins into `xdata_moved_ranks.py` above line 996 do move, and this
> paragraph does not claim otherwise.** An earlier draft of it said *no pin into
> `xdata_moved_ranks.py` moves*, on the grounds that every edit in the file is
> below line 996 and the highest pin into it is `:733`; **both halves are
> false**, and the correction is worth stating as a bound rather than a
> reassurance. The diff's hunks are at this change's merge base `b0b0c09c` — and
> therefore at `origin/main`, which does not touch the file — lines **996,
> 1126, 1129, 1132 and 1563**, so the true bound is that **no edit is above
> 1563**. Pins below 996 are unmoved: `:181`, `:243`, `:257`, `:436`, `:487`,
> the `31f683e5:`-pinned `:695-702`, and the bare `:335`, `:339`, `:455`, `:963`
> in [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
> §1. Two of that table's cells sit above 996 and move by the **+31** the 996
> hunk adds: the `collapse_line` call at `:1007` and the three `keyed_by(` call
> lines at `:1022`/`:1023`/`:1024`, which read **1058/1059/1060** in the merged
> tree.
>
> **That table is left uncorrected here, and the reason is worth recording
> rather than hiding.** Its §1 enumeration is a single `grep` run, and it was
> **already off by five lines on `main` before this change** — the `keyed_by`
> calls read 444/738/850/946/1027/1028/1029 there, against the `:439`/`:733`/`:845`/
> `:941`/`:1022`/`:1023`/`:1024` the table prints, and `collapse_line`'s call reads
> 1012 against the printed `:1007`. So this change moves four already-wrong numbers
> further from right rather than breaking correct ones. Re-anchoring only the
> three `keyed_by` ones would leave a single `grep` enumeration holding two
> vintages, which is worse than either; re-anchoring all of it is a correction
> to that write-up's own record and belongs to a change that says so, not to a
> labelling fix that would carry it silently. **It is owed and is not done
> here.**
>
> None of this reaches the *test*-pin table: `census_test_line_pins.py` reports
> the same **129 pins in 30 markdown files** on this tree and on `origin/main`
> at `b0b0c09c` — #421's `provenance-clone-depth-behaviour.md` is what carries
> them now — and its `read` line's population is `229` markdown files and `75`
> test files on this tree against `228` and `75` on `main`, the whole of the
> difference being this write-up, which cites no `test_*.py:NNN` and adds no
> suite. So nothing that table records needed re-registering for this change,
> which is the claim the paragraph was reaching for, and the one that is
> actually checkable; the re-registration the `read` line's own step does force
> is carried in [`test-line-pin-census.md`](test-line-pin-census.md), which is
> where it belongs.
>
> `docs/findings/INDEX.md` is a third thing, and the figure it is given here
> needed checking rather than restating. Measured on `git archive` trees: the
> merge base `b0b0c09c` is `origin/main` itself, lists **143** rows, reads
> `143 write-ups.` and **exits 0**; this tree, with its own write-up added,
> lists **144** rows, reads `144 write-ups.` and **exits 0**. So the count line
> moved `143` → `144` across this diff, and its one step is accounted for here:
> this change's own write-up. **That step is the one row**, and the count is a
> function of the tree — the generator reads the first `# ` heading of every
> `*.md` under `docs/findings/` less this index and `test-line-pin-census.md`,
> so a tree's figure is its markdown file count **less two** — which is why no
> hand-kept number in a shared file survives a merge here, and why the figure is
> regenerated rather than typed: adding the row and leaving `143 write-ups.`
> standing is precisely the staleness `--check` exists to catch, and it is the
> state this change's own first draft shipped.
>
> **The red set is unchanged, and re-counted rather than carried**: `bash
> tools/run-tests.sh` on the merged tree runs **75 suites and 2202 tests** and
> fails the same **eleven** — four in `test_gpu_block_watch`, three in
> `test_check_eq_guard_citations`, one each in `test_check_cluster_citations`
> and `test_check_doc_figure_pins`, two in `test_check_pin_table_rows` — and
> `b0b0c09c` fails those same five suites with those same per-suite counts, so
> this merge adds nothing to any of the eleven and the "adds nothing" claim
> above survives onto this tree. **The two `test_check_pin_table_rows` cases are
> still the `docs/agent-pipeline.md:409`/`:410` pair**; what moved beside them
> is the pin they are held against, `127` → `128`, which is #421's own
> `provenance-clone-depth-behaviour.md:37` row placing and not a
> re-registration of the row they name, which stays where it is.
>
> **`xdata_moved_ranks.py` is not byte-identical on the two trees, and `main`
> not touching it is only half of why.** The merge base `b0b0c09c` is
> `origin/main` itself and does not touch the file, so the merge contributes
> nothing to it — but the whole of the difference between the two trees is
> **this change's own diff**, `105` insertions and `15` deletions by
> `git diff --numstat`. Every pin this write-up makes into the file is therefore
> in merged-tree numbering and was re-anchored to it: `main` reads
> `collapse_line` at `:1012` and the three `keyed_by(` calls at
> `:1027`/`:1028`/`:1029`, which read the `:1043` and `:1058`/`:1059`/`:1060` the
> paragraph above predicts here — the **+31** the 996 hunk adds. The
> `53` → `56` `--self-test` count is `56` on this tree against `53` on
> `main`, and it is a difference at all only because of that same diff.
