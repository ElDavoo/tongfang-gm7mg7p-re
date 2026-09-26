# Which test file the corpus's pins name, and the indexed suites none of them does (issue #941)

**Nothing here is a hardware claim, and nothing here is a firmware claim.** No
image is opened, no register is read back, no capture is taken, and no laptop, EC
or Windows machine is involved anywhere below. Every figure is a count of lines
in files in this repository, and the one command that produces them is in it.
Same framing as [`test-line-pin-census.md`](test-line-pin-census.md) and
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md): a census of text
about text.

**This is a fifth axis on a census somebody else owns, and it renders no
verdict.** Issue #887's [`census_test_line_pins.py`](../../ec/tools/census_test_line_pins.py)
publishes four axes on the class of `test_*.py:NNN` citations the committed
markdown carries, and every one of them is a property of **where a pin is
written** — 106 occurrences, 79 distinct spellings, 58 distinct resolved targets,
28 citing files. The axis that decides how much damage an edit does is **which
test file the pin names**, and nothing on that page breaks the class down on it.
The tool is
[`check_pin_table_by_cited_file.py`](../../ec/tools/check_pin_table_by_cited_file.py)
and the suite is
[`test_check_pin_table_by_cited_file.py`](../../ec/tools/test_check_pin_table_by_cited_file.py).

**The `carries` / `does not carry` table is untouched, and this is a count of
records, exactly like every other figure on that page.** A pin's verdict is a
reading of whether the cited line still says what it is cited for, it lives in
the census write-up's per-pin table, and neither tool can produce it. Nothing
here moves 106, 79, 58, the shape split or the verdict tally;
`test_census_test_line_pins.py` is green against this merge, which is the test
that says so rather than a promise in this paragraph. *(The `105`, `78`, `57` and
`27` this paragraph was written with are the census's figures on the tree this
issue measured on; #778's write-up added one pin and repointed 33 others, which
is the whole of the `106`/`79`/`58`/`28`, and the correction paragraph under the
block below says so at the length it deserves.)*

## The measurement

```console
$ python3 ec/tools/check_pin_table_by_cited_file.py
which test file the census's pins name, and the indexed suites none of them does
  106 pin(s) over 40 indexed test file(s): 11 named by a pin, 29 named by none

  cited test file                                   resolves out-of-range     declined  occurrences
  ec/tools/test_xdata_cluster_names.py                    34            0           10           44
  ec/tools/test_grade_0751_isolation.py                   21            0           15           36
  windows/tools/test_manual_fan_ctrl_probe.py              5            0            3            8
  ec/tools/test_disasm8051.py                              4            0            1            5
  windows/tools/test_ec_watch.py                           3            0            2            5
  ec/tools/test_xdata_register_map.py                      2            0            0            2
  windows/tools/test_system_id_probe.py                    1            0            1            2
  ec/tools/test_check_site_census.py                       1            0            0            1
  ec/tools/test_check_testdata_index.py                    1            0            0            1
  ec/tools/test_citation_gap_scan.py                       1            0            0            1
  tools/test_readme_suite_table.py                         1            0            0            1
  44 of 106 occurrence(s) name one suite, and 80 of 106 name the two above -- the cost of an edit to that file, not an accusation

  0 unresolved-path, 0 ambiguous-path (records this file could place nowhere; counted, named, and never guessed)

  indexed but named by no pin (29 of 40):
    ec/tools/test_bank1_e582_framing.py
    ec/tools/test_census_test_line_pins.py
    ec/tools/test_check_capture_claims.py
    ec/tools/test_check_capture_names.py
    ec/tools/test_check_citation_lines.py
    ec/tools/test_check_cluster_citations.py
    ec/tools/test_check_doc_figure_pins.py
    ec/tools/test_check_pin_table_by_cited_file.py
    ec/tools/test_check_pin_table_rows.py
    ec/tools/test_check_testdata_row_claims.py
    ec/tools/test_citation_callers.py
    ec/tools/test_citation_frames.py
    ec/tools/test_disasm8051_oracle.py
    ec/tools/test_export_ownership.py
    ec/tools/test_grade_gpu_door.py
    ec/tools/test_grade_timer_sweep.py
    ec/tools/test_group_functions.py
    ec/tools/test_inc_dptr_sites.py
    ec/tools/test_walk_branch_arms.py
    ec/tools/test_walk_budget_census.py
    ec/tools/test_xdata_carry_notice.py
    linux/lightbar/test_probe_6005.py
    tools/test_agent_gates_patches.py
    tools/test_doc_patch_refs.py
    windows/tools/test_charge_target_test.py
    windows/tools/test_ctgp_dben_probe.py
    windows/tools/test_ec_validate.py
    windows/tools/test_ecrw.py
    windows/tools/test_gpu_block_watch.py
  read 161 markdown file(s) and 40 test file(s) under the tree, on census_test_line_pins.py's population: .git/vendor/ and docs/findings/test-line-pin-census.md excluded there
  no verdict is rendered here and none fails: whether a cited line still bears the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
  every negative above is 'not read by this method', never 'absent'
$ echo $?
0
```

*(Re-transcribed on the merged tree, per the same `§4a-4d` rule the rest of this
file follows: the `105`/`37`/`26` block above is what this issue measured on its
own tree, and **six** later merges moved it — #944's
`tools/test_doc_patch_refs.py` and its markdown write-up beside it, #778's
write-up with its edit to `ec/tools/test_xdata_cluster_names.py`, and then the
four that name no pin of this class and so move only the denominator beside it:
#780's `testdata-index-evidence-column.md`, the two `main` gained in the same
window — #964's `testdata-row-claims-dated-capture.md` and #982's
`testdata-addr-column-claim.md` — and #979's
`testdata-row-claims-multi-date-sentence.md`; #980 adds none, editing a write-up
already counted. **#985 is the first of the six that moved a suite as well as a
denominator**, `main` having gained it after this branch forked. Every figure
that moved, and why:

| figure | this issue's tree | merged tree | what moved it |
|---|---:|---:|---|
| pins | 105 | **106** | #778's write-up brings one pin, naming the `--no-eq-guard` recipe |
| indexed test files | 37 | **39** | #944's suite and then #985's `ec/tools/test_disasm8051_oracle.py`; the 33 repointed pins and the one new one all name files already in the index, so the count is by construction and moved by no figure in the table |
| named by a pin | 11 | **11** | #778's one new pin names `test_xdata_cluster_names.py`, already named |
| indexed and unpinned | 26 | **28** | the same two suites, into the tail |
| `test_xdata_cluster_names.py` resolves | 33 | **34** | #778's one new pin, by path |
| `test_xdata_cluster_names.py` occurrences | 43 | **44** | the same pin |
| one suite / the two | 43 / 79 of 105 | **44 / 80 of 106** | the same pin, in the first row |
| markdown files read | 150 | **160** | #944's two markdown files, one of them this tool's own sibling write-up, #780's `testdata-index-evidence-column.md`, the two `main` gained in the same window (#964's and #982's write-ups), #985's `disasm8051-oracle-from-the-annotations.md`, and #979's `testdata-row-claims-multi-date-sentence.md` |
| resolves / declined, summed | 73 / 32 | **74 / 32** | the census's own, and `test_census_test_line_pins.py` is green at 74/32 |
| the other nine rows | — | **unchanged** | #778's 33 repointed occurrences all resolve to `test_xdata_cluster_names.py` and to nothing else |

**#780's is the cheapest merge in this series and it is worth naming as such
rather than leaving the denominator's move unattributed.** Its write-up
(`testdata-index-evidence-column.md`) is one of the markdown files the
census reads, it cites no `test_*.py:NNN`, and it added no suite — so it moved
that denominator by one file and **nothing else on the block**, `157` → `158`
measured against `origin/main` at `368e9e52` and one more than the `156` its own
tree read. **#985's is the same kind of move and one file larger, `158` → `159`,
and it is the only one of the six that also took the suite denominator** — its
`disasm8051-oracle-from-the-annotations.md` is a markdown file the census reads,
its `test_disasm8051_oracle.py` a suite the index counts, and the suite joined
the tail rather than the named set, for the reason the twenty-first note in
`tools/README.md` gives and this file's own `thirty-nine` correction above
records. **#979's is the same kind of move again and the last of them, `159` →
`160`**: `abfe76e6` committed
[`testdata-row-claims-multi-date-sentence.md`](testdata-row-claims-multi-date-sentence.md),
one of the files the census walks and the only thing it moved — measured on both
sides by this tool's own walk on a `git archive` of each rather than by counting
the diff, so the step is a run and not an assumption, and `159` at `abfe76e6` and
`160` here are both that walk's output. *(The `124` this paragraph first recorded
is a fourth value for the
same denominator, superseded twice before this paragraph and left written per
§4a-4d, as the paragraph at the foot of this file records for the `151` and the
`152`.)* Its own re-registering edit, the
`testdata-index-suite-count-floor.md:25 → :47` repoint, is a `file.py:NNN` pin
rather than a markdown one and so does not appear in this table at all; it is a
`shape` movement in
[`test-line-pin-census.md`](test-line-pin-census.md)'s own table, and it is the
one that makes the merged shape split **`0/15/22/5/32`** rather than `main`'s
`0/16/22/5/31` — `main`'s own re-measurement having superseded the `18`/`35`
this paragraph first published, which was #780's own tree's two-way
assertion/`other` reading before #962's five-pin shift moved it.*

**The 33 repointed pins are invisible in this table by construction, and that is
the point of the axis rather than a gap in it.** A repoint moves the *line* a
spelling names, not the file, so the `resolves` column cannot see it and no row
here reweighted — the same distinction
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md) is about, arriving
from the other end. Only the one genuinely new pin moved a cell, and it moved the
first row by one in each of its two columns.)*

Both halves of the issue's ask are in that one command, and both reconcile: the
`resolves` column sums to the census's own **74**, the `declined` column to its
**32**, and the two together to the **106** occurrences it reports. A breakdown
whose columns do not add up to the census it is a breakdown of would be a second
opinion, and a second opinion is a second set of numbers; the suite asserts both
reconciliations on a fixture that exercises every column and both of the named
buckets, so the identity is held rather than observed once.

**The third column is `out-of-range`, and it is 0 on this tree.** It is there
because the census keeps the *path* on a record whose line outran its file — the
file is named even when the line is not one the file has — and folding those
records into `declined` would be a lie about what happened to them. It is
printed as a zero on every run rather than only when it is not, for the reason
[`test-line-pin-census.md`](test-line-pin-census.md)'s report prints all five of
its verdicts: a column that appears only when it is non-zero cannot be told from
one that stopped being measured.

## Which test file a pin names, and why that is the axis

| cited test file | resolves | declined | occurrences |
|---|---:|---:|---:|
| `ec/tools/test_xdata_cluster_names.py` | 34 | 10 | 44 |
| `ec/tools/test_grade_0751_isolation.py` | 21 | 15 | 36 |
| `windows/tools/test_manual_fan_ctrl_probe.py` | 5 | 3 | 8 |
| `ec/tools/test_disasm8051.py` | 4 | 1 | 5 |
| `windows/tools/test_ec_watch.py` | 3 | 2 | 5 |
| `ec/tools/test_xdata_register_map.py` | 2 | 0 | 2 |
| `windows/tools/test_system_id_probe.py` | 1 | 1 | 2 |
| `ec/tools/test_check_site_census.py` | 1 | 0 | 1 |
| `ec/tools/test_check_testdata_index.py` | 1 | 0 | 1 |
| `ec/tools/test_citation_gap_scan.py` | 1 | 0 | 1 |
| `tools/test_readme_suite_table.py` | 1 | 0 | 1 |

**Thirty-four sentences in the corpus name a line in
`ec/tools/test_xdata_cluster_names.py` and twenty-one name a line in
`ec/tools/test_grade_0751_isolation.py`, and that is the number an edit has to be
paid against.** Those two figures are the "done looks like" of the issue, and
they are the cost of inserting a line above either file: #850 put 239 lines into
the first and left four sentences naming where the floor was, #890 put 25 more in
and made two born-correct pins stale, and #885 wrote two more against a line that
was right on its own tree.
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md) is the sixth of
that series being paid: #930's two-row repoint took the first file's target count
back down by one, and the two rows it edited are two of the 34 above. *(The
`33` and `43` this file was written with are the record of the tree this issue
measured on and are left beside the correction under the block above rather than
edited out of silence, per [`../findings.md`](../findings.md) §4a-4d; the `34`
and `44` are #778's one new pin, and its 33 repointed occurrences are invisible
in this column by construction.)*

**A heavily-cited suite is not thereby wrong, and this table is not an
accusation.** It is a count of sentences that would need re-measuring if a line
moved, which is a different fact from whether any of them is already stale. The
clearest case is the first row: `ec/tools/test_xdata_cluster_names.py` is the
file the census write-up records **finding 6's four pins across two citing
files** in,
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) and
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) — the four bullets at
[`test-line-pin-census.md:1451-1466`](test-line-pin-census.md), and two is what
the census itself counts, because that write-up's own per-pin table copies those
four spellings rather than citing them independently and so is not a third. Its
roll-up further down puts **findings 6 and 8's six pins in four files**
([`test-line-pin-census.md:1094`](test-line-pin-census.md)), the other two being
finding 8's, and the six `> 300` pins of findings 6 and 8 are #920's and stay
`does not carry`
— while the pair #930 repointed onto that floor's own line carries again. The
same file is both the most-cited in the corpus and one the census holds a record
about, and neither of those is a consequence of the other. The tool prints the
cost and stops there: it renders no verdict on a single pin, and the
concentration line says so on every run rather than leaving a reader to work out
which of these numbers is a defect.

*(**Correction, 2026-09-26, at the `#778 × #780` merge, re-measured at the
`#929` × `#962` × `#794` × `#780` × `#985` merge: the two
`test-line-pin-census.md` line references above are repointed, and they are
re-pointed again here — `1373-1392` → `1435-1454` and `:1057` → `:1078`, and
nothing about what they name has changed.** The first correction records the
third position those two references took, each side of that merge having measured
a different one of the first two: #780's own tree read them at `828-841`/`:914`
and #778's at `888-903`/`:973`, neither of which is the base, and its
`940-955`/`:1026` was the composed tree's. **Those two values were themselves
already stale on the tree that wrote them**, which is the half of this correction
worth recording plainly rather than only the new numbers: the four bullets are at
`:1373` and the roll-up at `:1057` on #780's own tip, not the `940-955`/`:1026`
its paragraph gives, because that paragraph was written before the branch's own
later edits to that write-up's measurement block. **This merge settles all three
trees by extraction rather than by differencing**, the way the rest of this file
does: `origin/main` at `368e9e52` reads `:1204`/`:908`, this branch's tip reads
`:1373`/`:1057`, and this merged tree reads `:1434`/`:1078` — `+61` and `+21`
over the branch's own, which is this merge's census correction above the roll-up
and its seventh correction note between the two. The four bullets and
the roll-up line are the same four bullets and the same roll-up line on all three
trees; only where they sit moved. They are re-read on the merged tree rather than
carried across, and the superseded pairs stay visible here per §4a-4d rather than
edited out of silence. **No other file cites a line of that write-up**, so the
move stops here.)*

*(**Correction, 2026-09-26, at the `#979` × `#780` merge: both references above are
re-pointed a fourth time — `1435-1454` → `1451-1466` and `:1078` → `:1094` — and
again nothing about what they name has changed.** The whole of the `+16` is the
sixteen-line correction that write-up itself gained above the roll-up, recording
that `main` gained `abfe76e6` (#979) after its `#985` paragraph was written and
taking the markdown-file denominator from `159` to `160`; the same edit is
`#780`'s and the correction records both sides' halves rather than only this
branch's. **The `:1434` a first draft of the paragraph above gives is off by one
on its own tree and is left written**, since it was a shorthand for the start of
the range it names and the range it named — `1435-1454` — is the one that was
right. Re-read on the merged tree rather than carried across, and the superseded
pair stays visible here per §4a-4d rather than edited out of silence.)*

## The other direction: which indexed suites no pin names

Thirty-eight `test_*.py` files are in the tree and **eleven** of them are named by
a pin the census resolves to a file. The other **27** are indexed and unpinned,
and the tail is printed in full on every run for the reason the counts are: a
list a reader has to ask the tool for is a list nobody checks. It includes
`ec/tools/test_census_test_line_pins.py` and this suite, the six other
`test_check_*` suites, `ec/tools/test_citation_frames.py`,
`ec/tools/test_walk_branch_arms.py`, `windows/tools/test_ecrw.py` and
`linux/lightbar/test_probe_6005.py`.

**This half matters for the target count, and the connection is a sentence the
census write-up has been making from the other end.** Its argument for 58 distinct
resolved targets turns on whether a target was **already named** — #890's repoint
"split" one target into two, and #885's pair "arrived the other way … so they
added a target rather than splitting one". Which case a new pin falls into
depends on the population being eleven files out of thirty-nine, and until now
that population was not written down anywhere. It is now the second table.
*(The `thirty-eight` and the `27` this sentence carried are `thirty-nine` and
**`28`** on this merged tree, and the `eleven` is unmoved: #985's
`ec/tools/test_disasm8051_oracle.py` took the denominator by one and, as the
block above re-transcribes, joined the tail rather than
the named set — its write-up cites it by path and never as
`test_disasm8051_oracle.py:NNN`, deliberately, for the reason
`test-line-pin-census.md` records. The superseded values are left written per
§4a-4d.)*

**A suite in the tail is not a gap.** It says *no pin in this population names
it*, which is a statement about the population and not about the suite: a suite
whose whole job is to check a generated CSV has no reason to be cited by a line
number, and several of the 27 are load-bearing
([`tools/test_readme_suite_table.py`](../../tools/test_readme_suite_table.py) is
not, which is the other kind). The tail is the answer to "where would a new pin
add a target rather than split one", and it is a list that moves every time a
suite lands — which is why no case freezes it by name and only its length is
held.

**This suite is one of the 27, and that is not an oversight.** Nothing in the
committed markdown cites a line of it, because it was written beside the tool
rather than by a later prose pass, so it is in the tail exactly as
`ec/tools/test_census_test_line_pins.py` and the six other `test_check_*`
suites are. A
case holds the self-reference with the reason in the comment, so the two can never
be mistaken for a miss; when a later write-up cites one of these suites' lines,
that case goes red and the suite moves between the two tables, which is the axis
working rather than breaking. *(The `37`, `26` and `57` this section was written
with are the record of the tree this issue measured on; the extra suite is #944's
`tools/test_doc_patch_refs.py` and the extra target is #778's, and
`tools/test_doc_patch_refs.py` is in the tail above beside the other twenty-six.)*

## The one number that did not reproduce, and why

**The plan's figure was 32 declined pins by-path, and the census's own resolver
reports 16.** Feeding a declined spelling back through
`census.resolve()` — the same function, the same index — gives sixteen
`resolves` and sixteen `unresolved-path`, not thirty-two `resolves`. The reason
is worth stating because it is a property of the spelling rather than of the
resolver: the sixteen `grep -rn` transcript pins in
[`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md) are spelled
with a leading `./`, and the census's `files` index is keyed on the unprefixed
path. So the by-path reading misses, and the beside-the-citing-file retry misses
too, because `./ec/tools/…` normalises to itself against a citing directory and
lands nowhere.

`os.path.normpath()` on the spelled path alone puts **all thirty-two** in
`by-path`, and the issue's table comes back exactly. That is the whole of what
this tool adds over the census for a declined record, and it is deliberately
narrower than a repair:

* it is a **spelling** normalisation, and the docstring says so in those words.
  `./ec/tools/x.py` and `ec/tools/x.py` are one path written two ways;
* a path whose normalised form is **not** in the tree is not repaired into the
  file that happens to share its base name. The census's `unresolved-path` is
  that repair declined, and
  [`test-line-pin-census.md`](test-line-pin-census.md) records what making it
  costs — four sound citations reported as broken paths. So there is **no
  basename fallback** here either, and a declined pin nothing answers for lands
  in a **named** `unresolved-path` or `ambiguous-path` bucket, counted and
  printed with the spelling that landed there.

A case per shape holds that: the `./` prefix normalised away, a bare module name
answered by the census's own index, two files of one base name refused, and a
path nowhere in the tree landing in a named bucket rather than in one of the two
files' rows. The last is the case a basename fallback would fail, and it is in
the suite because a fallback is the obvious way to make the table's totals
reconcile.

## What this merge moved, and what it did not

*(This section is #941's own record of the merge that landed **this** file, and
the figures in it are the ones that were true then. **Two merges have landed
beside it since** — #944 and #778's — and their figures are the table under the
transcript above and the paragraphs below, which are a run of the merged tree.
Both records are kept rather than one edited into the other, per
[`../findings.md`](../findings.md) §4a-4d.)*

| figure | before | after | why |
|---|---:|---:|---|
| occurrences | 105 | **105** | this file carries no pin, so it added none |
| resolves / declined | 73 / 32 | **73 / 32** | unchanged, and the census's own suite is green |
| spellings / targets | 78 / 57 | **78 / 57** | unchanged |
| markdown files read | 149 | **150** | this file |
| indexed test files | 36 | **37** | this suite |
| named by a pin | 11 | **11** | this suite is in the tail, not this table |
| indexed and unpinned | 25 | **26** | the same suite |
| suites in the runner | 36 | **37** | `bash tools/run-tests.sh` finds it |
| tests in the runner | 1112 | **1139** | this suite's 27 cases, and nothing else moved |

**The three moved figures move by construction and the four did not move at all,
which is the same distinction
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md) is about.** A new
markdown file is a new file in the denominator; a new `test_*.py` is a new file
in the *population* the breakdown is a breakdown of, so this suite is one of the
26 rather than one of the eleven. The **149**, **36** and **25** are a run of
this same tool over **this branch's base** and are left here beside the
corrections rather than edited out of silence, per
[`../findings.md`](../findings.md) §4a-4d. *(They are not the tree the issue was
measured on: #945 landed a suite and a write-up after that, so a pair carried
forward from it would be one merge stale on arrival. Every figure in this file is
a run of the tree it will merge onto, and re-typing the transcript above is what
that costs.)*

**The two runner rows above moved, and the runner they came from is red — it was
red before this file landed.** `bash tools/run-tests.sh` read
`37 suite(s) run, 1139 tests; one or more FAILED` on that tree, and the one
failure was `ec/tools/test_check_cluster_citations.py`'s
`test_committed_prose_matches_committed_census`, on
[`xdata-cluster-names-guard-off-recipe.md:220`](xdata-cluster-names-guard-off-recipe.md)
— `0x0464` and `0x0465` against `main-ec-145`, which is #822's file and the red
set [`runner-red-suite-set.md`](runner-red-suite-set.md) has carried since #816.
**On the merged tree the runner reads `40 suite(s) run, 1243 tests; one or more
FAILED`, and the red set is back to the single suite the paragraph above names
rather than the two the `#778 × #780` tree carried.** The
`test_check_cluster_citations.py` failure is unchanged — same case, same line,
same message, and it reproduces identically on a clean `origin/main`, so neither
this file nor #778's merge causes or fixes it; it is named here rather than fixed
here, which is the convention [`../findings.md`](../findings.md) §66's merge note
follows, cited by section rather than by line here: a write-up whose subject is
stale line citations is the last place to leave one. **The second red suite the
`#778 × #780` tree carried is this one,
`ec/tools/test_check_pin_table_by_cited_file.py`, and it is green here**, so the
"two red suites" clause above is superseded at this merge and left written in
the one that measured it. **It was red because
`test_the_committed_index_figures_are_the_ones_the_write_up_publishes` held 37
indexed suites** — `main` having deferred that re-measurement to "whichever
change next owns this file" after #944's `tools/test_doc_patch_refs.py` took the
count to 38, so the pin was the last thing in the tree still saying `37` — and
because two of its three failures were #778's, the committed breakdown's first
row and the concentration pair, both moved by the one new pin and both
re-measured beside the transcript above. **#780 owns the file and re-set the
pin**, to **39 / 11 / 28**: `ec/tools/test_disasm8051_oracle.py` is #811's
suite and its write-up cites it by path and never as
`test_disasm8051_oracle.py:NNN`, deliberately, so nothing new is pinned,
`len(files) - len(tail)` stays **11**, and the tail takes the 39th unpinned
suite. The `37/11/26`, the `36/11/25` and the `38/11/27` stay written in that
case's own comment, each true of the tree it was measured on, per §4a-4d. The
second row
reconciles by arithmetic rather than by re-reading the runner: `1035 + 41` was
#887's `1076`, #945's `test_check_pin_table_rows.py` took it to `1112` with its
own 36 cases, `1112 + 27` is this suite's own 27, `1139 + 22` is #944's
`tools/test_doc_patch_refs.py` — the whole of the move to `1161`, because #778's
edits changed no suite's case count — and **`1161 + 10` is #780's own step**:
`ec/tools/test_check_testdata_index.py` grew from 59 cases to 69, and #778's and
#780's are both suite-growth-free apart from that one. **The `1171` above is
superseded on this tree, and so is the `1211` that replaced it on `main`** —
`origin/main` at `abfe76e6` re-derived `1211` for the `#979` × `#985` merge, and
`1211 + 10 = 1221` is this merge's step on top of it, with the suite count
moving `38` → `39` on `main`'s side for the reason the twenty-first note in
`tools/README.md` records. **Neither pair is this tree's**: `main` has since
gained #973's commit, so the sentence `tools/README.md` carries is corrected
again and this tree reads `40 suite(s) run, 1243 tests` and `939` for
`python3 -m unittest discover -s ec/tools` — `1233 + 10 = 1243`, the same one
step #780 contributes measured from the other side's tree, with the suite count
unmoved at the `40` `main` already read. Both superseded pairs stay written
above, each true of the tree it was measured on, per §4a-4d.

**The 149 and the 36 are also printed by `census_test_line_pins.py` itself**, and
its output line for each moves with this merge — the run then read `150 markdown
file(s)` and `37 test file(s)`, and on the merged tree it reads **`161`** and
**`40`**. That transcript is quoted verbatim in
[`test-line-pin-census.md`](test-line-pin-census.md) and in a dozen
merged-tree notes in [`../../tools/README.md`](../../tools/README.md); the
`test-line-pin-census.md` copy is re-transcribed above and the notes beside it
record `153`/`38` at the `#778 × #780` merge and `161`/`40` at this one, and the
rest are left as the history they are,
the same trade this issue made. A reader who wants the old pair
reads this section; a reader who wants the current one runs the tool.

**A write-up that is pin-free is the normal state, not a trick.** No path in this
file is followed by a line number, because the census's reader would count each
of those as an occurrence of the class this page is a fifth axis on. The guard is
already committed: `test_census_test_line_pins.py`'s
`test_the_committed_counts_are_the_ones_the_write_up_publishes` holds 106, 28, 79,
58 and the shape split, so a stray pin turns **that** case red and the prose is
what gets fixed. 133 of the 161 markdown files the census reads carry none.

**The `150` and the `37` above are this file's own tree, and both are one short
of it; the tree this lands in reads `161` and `40`, and `133` of the `161` carry
no pin.** Measured, not differenced, and each of the three steps is one markdown
file and not one record: a `git archive origin/main` extraction gave
`census_test_line_pins.py` reading `151` markdown files and `38` indexed test
files, the `#929` × `#777` merge that put this write-up beside
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
and [`doc-patch-reference-gate.md`](doc-patch-reference-gate.md) took it to
`152` and left the indexed count at `38`, and the `#929` × `#778` merge that put
[`xdata-two-largest-case-restatement.md`](xdata-two-largest-case-restatement.md)
beside it takes the corpus to **`153`** while leaving the indexed count at `38`
again. **The tree this merge lands in reads `161` and `40`**, and the eight
markdown files between `153` and `161` are the five `main` gained in the same
window — #964's, #982's, #985's, #979's and #973's write-ups — with #780's own
beside them, every one of them a write-up that cites no line of a test file,
which is
the same shape the three steps above record and the reason no record moved with
them. **The `153`, the `38` and the `125` are left written, each true of the
`#778 × #780` tree it was measured on**, per §4a-4d. **The `152` and the `124`
this paragraph first recorded are superseded by
that one file and are left written here**, and the `151` is superseded in turn by
`main` having taken #778 since the extraction was taken. **The `160` and the
`39` this paragraph carried when it was written are superseded the same way, by
#973's commit landing beside #780's rather than replacing it**, and both stay
written above each true of the tree it was measured on.

**The step is one file each and not a record each**, which is the point this
write-up's own axis is about: of the three new files only #778's carries a
`test_*.py:NNN` pin, and it carries exactly the one its own
[`test-line-pin-census.md`](test-line-pin-census.md) correction already counted,
so the class is the same size it was on this file's own tree — **`106`** pins in
**`28`** files, `79` spellings and `58` targets — and the count of files carrying
no pin is the only figure above that moves. All
superseded values stay written per [`../findings.md`](../findings.md) §4a-4d,
[`test-line-pin-census.md`](test-line-pin-census.md) carries the re-transcribed
block and a per-merge section for it, and this write-up's own
`test_check_pin_table_by_cited_file.py` index pin is re-set to the measured
**39 indexed / 11 named / 28 named by none** with the reason in the comment
beside it — which `main` left red on purpose and this change, as the next owner
of that file, is the one its note was waiting for. *(The `38`/`11`/`27` this
paragraph carried is the value the pin held between that re-set and #985's
suite, and it is left written; the case's own comment carries all three
superseded triples beside the live one, per §4a-4d.)*

*(**And that pin has since moved twice more, by the same rule and one suite
each.** Issue #811's `ec/tools/test_disasm8051_oracle.py` and issue #973's
`ec/tools/test_check_capture_names.py` are both new `test_*.py` files that no
pin names — both write-ups cite their suite *by path* and never as
`<module>.py:NNN` — so the two landed beside each other rather than one
replacing the other, and the pin is re-set to the measured **40 indexed / 11
named / 29 named by none**. The `39/11/28` and the `38/11/27` above stay
written, each figure true of the tree it was measured on per
[`../findings.md`](../findings.md) §4a-4d; `39/11/28` is triple-true, because
each side of the merge re-measured to it against a tree the other side's suite
was not on, and the two steps are additive. `11` named by a pin does not move
because the pin count is still **106**; the `38` → `39` → `40` and `27` → `28`
→ `29` steps are those two suites. **The `console` transcript above is
deliberately left at `38`/`152`** — it is a record of one run on the tree this
issue measured on, and it reads `152` markdown files where the tree now carries
more, so it has been a dated snapshot rather than a live claim since before
these steps and stays one. **That clause is superseded, beside itself and not
into itself, per §4a-4d: the transcript is re-run rather than left, and it reads
`40`/`161` here** — the branch re-ran it to `39`/`160` for the `#778 × #780`
merge and this merge re-ran it again on the tree that carries both, so the
`38`/`152` and the `39`/`160` are two further values in a history that has three
entries in it, each of which the diff carries and none of which the file states
as current. Re-running it is what costs the two suites their place in the
sentence above: `test_disasm8051_oracle.py` and `test_check_capture_names.py`
are in the transcript's tail list because the run that produced it is this
merge's, not because the paragraph naming them was edited.)*

*(**And the same `40 / 11 / 29` holds on the second merge's tree, which is the
one this landed on, for a reason worth one sentence.** The two suites named
above are #811's and #973's, and this write-up's two merges are `47 → 38` and
then `39 → 40`, so which of the two merges the second suite arrives in does not
change the answer — `test_check_capture_names.py` is in the tail either way, and
so is `test_disasm8051_oracle.py`. **The figure was re-measured on the merged
tree rather than carried, and it is the same one**, which is what a pin whose
inputs are "the set of `test_*.py` files" should do: the merge order is not a
variable. The `106` behind the `11` is unmoved on this tree too —
`check_pin_table_rows.py` reads 106 / 106 / 106 with all seven classes 0 — so
nothing here needed re-deriving beyond running the one suite that owns the
assert.)*

## The name, which is a standing rather than a measurement

The issue asked for `ec/tools/check_pin_table_by_cited_file.py` and for
`test_<tool>.py` beside it, and both are here. In this tree `census_*` means
"renders no verdict" and `check_*` means "it can redden", and **this tool cannot
reden on drift** — it exits 0 on a tree where every pin is wrong, and a case says
so. That is a mild misnomer, and it is the one naming judgement nobody here can
settle from a measurement, so it is stated rather than hidden: the standing is in
the tool's docstring, a case holds it from the output side (the report contains
neither `carries` nor `does not carry`), and the alternative name —
`census_pin_table_by_cited_file.py` — is recorded there beside it. The
`test_<tool>.py` pairing the issue asked for is the reason it was not taken, and a
rename later is cheaper than one now.

**And what this tool is not.** It is not in
`.github/scripts/agent-gates.sh`, and cannot be from an agent branch: the plan
stage's push token has no `workflow` scope, so a branch touching `.github/` fails
at the very end of the run. It runs by hand, where
`census_test_line_pins.py` stands today. A census nobody runs is the shape of
defect issue #819 was, so a case holds that standing rather than leaving a reader
to assume a gate exists. For the same reason
[`../../tools/README.md`](../../tools/README.md)'s table gained a row and
[`../findings.md`](../findings.md) §65 gained a pointer: a suite with no row in
that table turns a currently-green suite red, and that is mechanical rather than
optional.

## What is left, as follow-ups

1. **The unpinned tail is now a measured figure that no case holds by name** —
   only its length reconciles. The next suite added moves it silently, and
   whether that should be a figure anything is responsible for is a decision for
   a later issue rather than a list to freeze here.
2. **The `normpath` normalisation is a second reader of the census's
   spellings.** Today the only difference it erases is a `grep -rn` `./` prefix,
   and if a future write-up spells a pin that way in live prose the two readers
   could drift. Whether the normalisation belongs *inside*
   `census_test_line_pins.py` instead is worth deciding; it is deliberately not
   done here, because that is a change to the census's own behaviour and this
   issue is a second reader of it, not a rewrite of it.
3. **A fifth axis on a class whose other four have each moved at a merge will
   move at the next one too, and no gate runs either tool.** The table is
   printed on every run for that reason rather than quoted once, and
   [`test_check_pin_table_by_cited_file.py`](../../ec/tools/test_check_pin_table_by_cited_file.py)
   holds the committed breakdown as a `{path: (resolves, declined)}` dict so that
   a merge which adds a pin to a fifth file **moves a figure** rather than
   quietly reweighting a breakdown nobody has read.
