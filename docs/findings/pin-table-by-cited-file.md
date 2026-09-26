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
written** — 105 occurrences, 78 distinct spellings, 57 distinct resolved targets,
27 citing files. The axis that decides how much damage an edit does is **which
test file the pin names**, and nothing on that page breaks the class down on it.
The tool is
[`check_pin_table_by_cited_file.py`](../../ec/tools/check_pin_table_by_cited_file.py)
and the suite is
[`test_check_pin_table_by_cited_file.py`](../../ec/tools/test_check_pin_table_by_cited_file.py).

**The `carries` / `does not carry` table is untouched, and this is a count of
records, exactly like every other figure on that page.** A pin's verdict is a
reading of whether the cited line still says what it is cited for, it lives in
the census write-up's per-pin table, and neither tool can produce it. Nothing
here moves 105, 78, 57, the shape split or the verdict tally;
`test_census_test_line_pins.py` is green against this merge, which is the test
that says so rather than a promise in this paragraph.

## The measurement

```console
$ python3 ec/tools/check_pin_table_by_cited_file.py
which test file the census's pins name, and the indexed suites none of them does
  105 pin(s) over 36 indexed test file(s): 11 named by a pin, 25 named by none

  cited test file                                   resolves out-of-range     declined  occurrences
  ec/tools/test_xdata_cluster_names.py                    33            0           10           43
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
  43 of 105 occurrence(s) name one suite, and 79 of 105 name the two above -- the cost of an edit to that file, not an accusation

  0 unresolved-path, 0 ambiguous-path (records this file could place nowhere; counted, named, and never guessed)

  indexed but named by no pin (25 of 36):
    ec/tools/test_bank1_e582_framing.py
    ec/tools/test_census_test_line_pins.py
    ec/tools/test_check_capture_claims.py
    ec/tools/test_check_citation_lines.py
    ec/tools/test_check_cluster_citations.py
    ec/tools/test_check_doc_figure_pins.py
    ec/tools/test_check_pin_table_by_cited_file.py
    ec/tools/test_check_testdata_row_claims.py
    ec/tools/test_citation_callers.py
    ec/tools/test_citation_frames.py
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
    windows/tools/test_charge_target_test.py
    windows/tools/test_ctgp_dben_probe.py
    windows/tools/test_ec_validate.py
    windows/tools/test_ecrw.py
    windows/tools/test_gpu_block_watch.py
  read 149 markdown file(s) and 36 test file(s) under the tree, on census_test_line_pins.py's population: .git/vendor/ and docs/findings/test-line-pin-census.md excluded there
  no verdict is rendered here and none fails: whether a cited line still bears the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
  every negative above is 'not read by this method', never 'absent'
$ echo $?
0
```

Both halves of the issue's ask are in that one command, and both reconcile: the
`resolves` column sums to the census's own **73**, the `declined` column to its
**32**, and the two together to the **105** occurrences it reports. A breakdown
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
| `ec/tools/test_xdata_cluster_names.py` | 33 | 10 | 43 |
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

**Thirty-three sentences in the corpus name a line in
`ec/tools/test_xdata_cluster_names.py` and twenty-one name a line in
`ec/tools/test_grade_0751_isolation.py`, and that is the number an edit has to be
paid against.** Those two figures are the "done looks like" of the issue, and
they are the cost of inserting a line above either file: #850 put 239 lines into
the first and left four sentences naming where the floor was, #890 put 25 more in
and made two born-correct pins stale, and #885 wrote two more against a line that
was right on its own tree.
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md) is the sixth of
that series being paid: #930's two-row repoint took the first file's target count
back down by one, and the two rows it edited are two of the 33 above.

**A heavily-cited suite is not thereby wrong, and this table is not an
accusation.** It is a count of sentences that would need re-measuring if a line
moved, which is a different fact from whether any of them is already stale. The
clearest case is the first row: `ec/tools/test_xdata_cluster_names.py` is the
file the census write-up records **finding 6's four pins across two files** in,
and the six `> 300` pins of findings 6 and 8 are #920's and stay `does not carry`
— while the pair #930 repointed onto that floor's own line carries again. The
same file is both the most-cited in the corpus and one the census holds a record
about, and neither of those is a consequence of the other. The tool prints the
cost and stops there: it renders no verdict on a single pin, and the
concentration line says so on every run rather than leaving a reader to work out
which of these numbers is a defect.

## The other direction: which indexed suites no pin names

Thirty-six `test_*.py` files are in the tree and **eleven** of them are named by
a pin the census resolves to a file. The other **25** are indexed and unpinned,
and the tail is printed in full on every run for the reason the counts are: a
list a reader has to ask the tool for is a list nobody checks. It includes
`ec/tools/test_census_test_line_pins.py` and this suite, the five other
`test_check_*` suites, `ec/tools/test_citation_frames.py`,
`ec/tools/test_walk_branch_arms.py`, `windows/tools/test_ecrw.py` and
`linux/lightbar/test_probe_6005.py`.

**This half matters for the target count, and the connection is a sentence the
census write-up has been making from the other end.** Its argument for 57 distinct
resolved targets turns on whether a target was **already named** — #890's repoint
"split" one target into two, and #885's pair "arrived the other way … so they
added a target rather than splitting one". Which case a new pin falls into
depends on the population being eleven files out of thirty-six, and until now
that population was not written down anywhere. It is now the second table.

**A suite in the tail is not a gap.** It says *no pin in this population names
it*, which is a statement about the population and not about the suite: a suite
whose whole job is to check a generated CSV has no reason to be cited by a line
number, and several of the 25 are load-bearing
([`tools/test_readme_suite_table.py`](../../tools/test_readme_suite_table.py) is
not, which is the other kind). The tail is the answer to "where would a new pin
add a target rather than split one", and it is a list that moves every time a
suite lands — which is why no case freezes it by name and only its length is
held.

**This suite is one of the 25, and that is not an oversight.** Nothing in the
committed markdown cites a line of it, because it was written beside the tool
rather than by a later prose pass, so it is in the tail exactly as
`ec/tools/test_census_test_line_pins.py` and the six `test_check_*` suites are. A
case holds the self-reference with the reason in the comment, so the two can never
be mistaken for a miss; when a later write-up cites one of these suites' lines,
that case goes red and the suite moves between the two tables, which is the axis
working rather than breaking.

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

| figure | before | after | why |
|---|---:|---:|---|
| occurrences | 105 | **105** | this file carries no pin, so it added none |
| resolves / declined | 73 / 32 | **73 / 32** | unchanged, and the census's own suite is green |
| spellings / targets | 78 / 57 | **78 / 57** | unchanged |
| markdown files read | 148 | **149** | this file |
| indexed test files | 35 | **36** | this suite |
| named by a pin | 11 | **11** | this suite is in the tail, not this table |
| indexed and unpinned | 24 | **25** | the same suite |
| suites in the runner | 35 | **36** | `bash tools/run-tests.sh` finds it |

**The three moved figures move by construction and the four did not move at all,
which is the same distinction
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md) is about.** A new
markdown file is a new file in the denominator; a new `test_*.py` is a new file
in the *population* the breakdown is a breakdown of, so this suite is one of the
25 rather than one of the eleven. The **148**, **35** and **24** are the record
of the tree the issue was measured on and are left here beside the corrections
rather than edited out of silence, per [`../findings.md`](../findings.md) §4a-4d.

**The 148 and the 35 are also printed by `census_test_line_pins.py` itself**, and
its output line for each moves with this merge — the run now reads `149 markdown
file(s)` and `36 test file(s)`. That transcript is quoted verbatim in
[`test-line-pin-census.md`](test-line-pin-census.md) and in a dozen
merged-tree notes in [`../../tools/README.md`](../../tools/README.md), and
**none of them is edited here**: that file is a merge magnet with open PRs
against it, and re-typing eleven quoted transcripts to move a denominator would
be a far larger diff than the measurement it records. The two figures are named
here instead, and the run is the re-derivation. A reader who wants the old pair
reads this table; a reader who wants the current one runs the tool.

**A write-up that is pin-free is the normal state, not a trick.** No path in this
file is followed by a line number, because the census's reader would count each
of those as an occurrence of the class this page is a fifth axis on. The guard is
already committed: `test_census_test_line_pins.py`'s
`test_the_committed_counts_are_the_ones_the_write_up_publishes` holds 105, 27, 78,
57 and the shape split, so a stray pin turns **that** case red and the prose is
what gets fixed. 122 of the 149 markdown files the census reads carry none.

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
