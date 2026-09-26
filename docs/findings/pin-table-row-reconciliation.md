# The per-pin table's four mechanical columns are now reconciled against the run, and its fifth is not read (issue #942)

**Nothing here is a hardware claim, and nothing here is a firmware claim.** No
image is opened, no register is read back, no capture is taken, and no laptop, EC
or Windows machine is involved anywhere below. Every figure is a count of rows
and records over text committed in this repository, and the one command that
produces them is in it. Same framing as
[`test-line-pin-census.md`](test-line-pin-census.md) and
[`test-line-pin-repoint-563.md`](test-line-pin-repoint-563.md): a census of text
about text.

```
$ python3 ec/tools/check_pin_table_rows.py
106 table row(s) against 106 census record(s) under …/tongfang-gm7mg7p-re: 106 placed
  0 unparsed-row, 0 unplaced-row, 0 row-without-record, 0 duplicate-key, 0 read-differs, 0 shape-differs, 0 path-differs
  no verdict cell was read: whether a cited line still carries the claim it is
  cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
```

*(Transcribed again on the merged tree, per the `§4a-4d` rule this repository
applies to its own figures: **#778's** write-up
`xdata-two-largest-case-restatement.md` brings a pin with it, and its edit to
`ec/tools/test_xdata_cluster_names.py` re-registered 33 others, so records went
105 → 106 and the table was re-derived from the merged tree's own run to follow.
That branch's own `*Pins*` section measured the same 105 → 106 and 73 → 74
before this tool existed to report it — the two agree because the census is the
census, not because one was copied from the other. The `105` in the block above
is the record of the tree #942 measured and is left visible, per the same rule
that keeps the older counts in [`test-line-pin-census.md`](test-line-pin-census.md)
in its sentence rather than out of it. **The merged tree's re-registration count
is 33 target columns and six citing lines, not three** — the three extra are
`doc-figure-pin-audit.md`'s own, moved by the thirteen-line correction the
`check_doc_figure_pins.py` fixture re-pick added to that file, which is the
coupling this tool exists to catch being caught in the act one more time.)*

## The gap, in one sentence

Four of the per-pin table's five columns are not a reading at all — the citing
file, the citing line, the cited target, the read kind and the shape are five
things `census_test_line_pins.py` already computes and prints under `--verbose` —
and **no rule anywhere joined them to the run.** Only the fifth column is the
judgement, so the table looked like a self-checking artefact and was not one. A
row whose citing line quietly moved stayed a perfectly normal row.

## What it has cost this repository, by hand

Five times, each paid by a person rather than by a run:

| when | what moved | what it took |
|---|---|---|
| #891 | `xdata-moved-ranks-fall.md`'s citing lines, as the census write-up's merged-tree note records: `:319` → `:383` and `:331` → `:395` | re-reading `--verbose` against the table |
| #889's note | two more citing lines in that same file | the same |
| #930 | `../findings.md:9046` → `:9077`, re-registered in the merge that landed the correction above it | the same |
| #941 | `../findings.md:9077` → `:9103`, re-registered in the merge that landed the fifth-axis pointer above it — a 26-line insertion carrying no pin of its own | the same |
| #920 | six `> 300` pins to repoint, still open | still open |

A merge that only *adds a paragraph* invalidates rows. That is the whole
argument for this tool, and the sentence at
[`test-line-pin-census.md`](test-line-pin-census.md)'s finding 7 — *"the tool
that would have said so is not in any gate"* — is the write-up costing itself
two pins for want of one.

## What was measured before anything was changed

Every figure below is this branch's own run of the tool over the merged tree,
not a figure carried forward. The plan recorded these and they were
re-measured before the tool was written; the second reading is the one the tool
and its suite hold.

| quantity | measured |
|---|---|
| table data rows | **106** (header `:883`, separator `:884`, rows `:885`–`:989` — re-derived on the `#929` × `#962` × `#794` × `#780` × `#985` × `#979` tree, +1 on the `105` the `#942 × #780` merge measured; the `:846`/`:847`–`:952` a first draft of this row carried and the `:470`/`:472`–`:576` it names are that other tree's) |
| census records over the same markdown | **106** — 74 `resolves`, 32 `declined`, and 0 of each of the other three |
| rows that could not be placed | **0** |
| records with no row | **0** |
| read-kind, shape and resolved-path differences | **0** |
| duplicate `(citing file, citing line, spelling)` keys | **0** |
| read cells, of the 74 that resolve | 53 `by-path`, 19 `by-name`, 2 `beside` |
| shape cells | 0 `def test_`, 15 `assertion`, 22 `comment`, 5 `blank`, 32 `other`, plus 32 `—` — the merged split, and both of its movements are other issues': `main`'s re-measurement moved five pins off a `def test_` header onto prose or code when #962 corrected a docstring above them, and #780's repoint of the `testdata-index-suite-count-floor.md:25 → :47` row at the rule that replaced the code it cited landed its pin on prose rather than on an assertion. The `5`/`18`/`10`/`6`/`34` the `#942 × #780` merge published and the `19`/`34` this page was written with are each left here as what the tree they were measured on read, per §4a-4d. |

**Every figure above is re-derived on this tree by running the two tools rather
than by carrying either side's reading, and the run is the check the table is
for.** `ec/tools/check_pin_table_rows.py` reads **106 table row(s) against 106
census record(s): 106 placed, 0 unparsed-row, 0 unplaced-row, 0
row-without-record, 0 duplicate-key, 0 read-differs, 0 shape-differs, 0
path-differs**, and the read and shape columns above are counted out of that
table rather than out of anything in this page. The `105`/`73` the
`#942 × #780` merge measured and the `105`/`37`/`26` this page was written with
stay written where they are, each true of the tree it was measured on.

So the table reconciles today, which is the calibration the issue claims and the
reason the tool lands green. The point of a green check on a correct tree is not
that it found something: it is that the **next** drift is loud.

## Two things about the table's own spelling, which are findings rather than trivia

**Finding A — the table abbreviates one read kind.** The census's
`BY_BESIDE` constant is `beside-the-citing-file`; the table writes `beside` in
the two rows that need it. A naive equality check reddens on a correct tree.
The tool carries an explicit one-entry alias map and **an unrecognised read
cell is a reported problem rather than a pass**, so a fourth spelling fails
instead of sliding through. The reverse fix — normalising the two cells in the
table — was deliberately *not* taken: it edits a shared, actively churning file
for a cosmetic reason, and the alias keeps the diff out of it. A second
abbreviation is in the same table and is handled the same way: the 32 declined
rows write an em dash where the census writes a bare hyphen, and reading that as
an unknown cell would redden a third of a correct tree.

**Finding B — the citing cell has two spellings, 105 : 1.** 105 rows write
`[`path`](path)` with `:NNN` outside the link, one of them with a trailing `†`
marker. One row writes `` `docs/agent-pipeline.md:345` `` with the line *inside*
the code span. A parser that handled only the first form would report the whole
table unparsed, and one that skipped what it could not parse would place nothing
and pass. Both forms are accepted; a row in neither is a reported
`unparsed-row`. The `†` is stripped for the match and **kept in the message**,
because a row that carries the mark is the row the write-up is superseding, and
a message that dropped it would name a different row than it is about.

## A correction to this issue's own argument, for `path-differs`

The issue argued for a separate resolved-path class on the grounds that
*"re-deriving the path … is what catches a citing file moving to a different
directory, where the read cell can still read `beside` and still be right about
nothing."* **Measured, that does not survive the match key**, and the superseded
version is left here rather than deleted, per §4a-4d.

A row is matched on `(resolved citing path, citing line, target spelling)`. A
record's `path` has exactly one source — `census.resolve()`, called on
`(spelling, dirname(citing))` — and the key pins **both of those inputs
exactly**. So on a placed row the re-derivation is an identity by construction
and cannot differ; the case it was argued for is already caught by `read-differs`,
which reads the read kind out of the record's own `how` rather than re-deriving
it. The class is **kept**, for the one thing it is still good for: it is the
assertion that fires if `census.resolve()` ever stops being a pure function of
its inputs, which is a real regression and one nothing else here would notice.
It is not a fifth independent column check, and
`test_path_differs_fires_when_the_record_and_the_row_disagree` demonstrates it
is not dead code rather than leaving that as a claim.

## What the tool does *not* catch

The longer list than the seven classes, and every negative in it is *"not read by
this method"*, never *"absent"* — the caveat `ec/annotations/registers.yaml`
carries for a static scan, load-bearing here for the same reason it is there.

- **A verdict that has quietly stopped being true.** By construction. This tool
  checks that the table still *describes* the run; whether a pin carries its
  claim is a reading, and a reading is a human looking at a line. A green run is
  not a statement about any of the 106 verdicts.
- **A row that is *right* about a stale line.** If a merge moves a line and the
  citing prose is re-registered in the same commit, this tool is green and the
  *claim* is no better than it was. The tool tracks the table against the run;
  it does not track either against the truth.
- **A spelling the census never emitted.** The population is
  `census_test_line_pins.py`'s, with its own `PRUNED` and its own `SELF_DOC`
  exclusions read from the census rather than restated here. A pin into a
  non-`test_*.py` file is in a different census with a different owner (#913),
  and a pin inside `vendor/` is committed third-party material rather than this
  repository's prose. Neither is in this population, and "not in this
  population" is not a claim about whether either is sound.
- **The table's row *order*.** The table says *"one row per occurrence, in the
  census's own order"*, and order is not one of the five columns. A
  walk-order dependency would fail a tree that is otherwise correct the moment a
  markdown file is added or removed, so it is deliberately not checked — and
  said here rather than left silent.
- **A record the run could not resolve.** `unresolved-path`, `ambiguous-path`
  and `out-of-range` are all 0 today. When one is non-zero the census already
  names it, and a row for such a record is counted as *uncompared* and printed
  as such — the census records no read kind and no shape for it, so there is
  nothing to hold the row to, and the count is what stops that reading as a
  clean run.

## The coupling this adds, which is a cost and not only a benefit

The census reads every markdown file in the tree except
`docs/findings/test-line-pin-census.md` itself, and the table is a copy of that
population's rows. So **writing a `test_*.py:NNN` citation into any other
markdown file now requires a new row in that table**, and omitting one is a
`row-without-record`. That is the price of making the join checkable, it is
small, and it is worth stating: this file and the other four it touches write no
such spelling, deliberately, rather than growing the table by a row apiece.
`docs/findings/test-line-pin-census.md` is exempt, because the census excludes
it — a measurement of the measurement is not evidence about the census.

## Where it runs, and where it does not

`ec/tools/check_pin_table_rows.py` is **not in any gate today.** `.github/` is
copied from the agent-pipeline template and the pipeline's push token has no
`workflow` scope, so a branch editing it fails at the *end* of a PR rather than
at the start; the change is prepared as
[`docs/ci/agent-gates-pin-table-rows.patch`](../ci/agent-gates-pin-table-rows.patch)
and a human lands it with `git apply`, as
[`docs/findings/prepared-gate-patches.md`](prepared-gate-patches.md) sets out and
[`docs/agent-pipeline.md`](../agent-pipeline.md)'s item 12 carries across a
re-copy. **Until a human lands it, no commit runs it**, and a row that drifts
does so in a green tree — which is the standing
`test_census_test_line_pins.py` holds for the census itself, in the same words.

`tools/run-tests.sh` needs no edit: its own `find` discovers the new suite, so
it is collected by the runner today. The command above is the gate-to-be.

The patch's `gate` line goes at the **head** of the list rather than the end,
and the reason is composition, not reading: the end of the list is
`agent-gates-testdata-row-claims.patch`'s context window, and two patches
editing one contiguous region cannot both be applied in either order. Every
ordered pair is asserted to land by `tools/test_agent_gates_patches.py`, so no
landing order has to be written down anywhere. Same trade, and same reason, as
item 11's patch.

## Suite

`ec/tools/test_check_pin_table_rows.py`, 36 cases, discovered by
`tools/run-tests.sh` with no edit to the runner. The five the issue names, one
per failure mode — a row whose citing line moved, a row whose shape changed
under it, a record with no row, a row with no record, and a run that placed
nothing — then the cases a loosened version would let through: exit 0 on a tree
where every verdict is wrong, both citing-cell spellings and the `†` marker, the
`beside` abbreviation honoured and an unknown read cell reported, a duplicate key
reported rather than guessed, an unparsed row reported, a missing header
reported, the two-header case refused, and the white-box `path-differs` case
above. Fixtures are small inline trees built per call, the
`test_census_test_line_pins.py` `tree()` pattern, so each case reads as the error
it is about. The last class is the committed tree: 106 rows place, every class
is 0, and the read and shape cells are held to the census's own vocabulary and
split.

Nothing here reads firmware, opens a capture, or reads back a register, and
nothing in it needs the machine.

One red line in that run is not this branch's. `tools/run-tests.sh` ends
`37 suite(s) run, 1139 tests; one or more FAILED` on the tree #941 merges onto,
and the single failing suite
is `ec/tools/test_check_cluster_citations.py`'s
`test_committed_prose_matches_committed_census`:
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):220
cites `0x0464` and `0x0465`, which are members of `main-ec-145` and of none of
the clusters that line names. It reproduces identically in a clean worktree at
`origin/main`, and this branch touches neither that recipe nor
`ec/annotations/xdata-clusters.csv`, so it is pre-existing and has nothing to do
with the tool above. The new suite is green in the same run: 36 tests, passed.
*(The `36` and `1112` this paragraph was first written with are the record of the
tree it was measured on and are left here beside the correction rather than edited
out of silence, per [`../findings.md`](../findings.md) §4a-4d: #941 adds a suite
and a write-up, so `36 + 1` and `1112 + 27` are the pair this tree reads.)*
