# Which of the census checklist's figures a check actually holds, measured (issue #849)

Issue #820 made
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
canonical, and its §2b is the one place that says which of its figures a
re-deriver has to redo by hand. Issue #849 found the split was the wrong way
round, and this file is the write-up: what was measured, how, what came out,
and what is left over.

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure is a
count of bytes in files in this repository, and the two commands that produce
them are in it. Same framing as
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):11.

## The finding

§2b's heading read **"Eight, unpinned — these are the ones that decay
silently"**, and that was wrong in both directions at once.

A re-deriver reading it would redo by hand the figures the cheap gate already
turns red on — work the tree does. **Across the section that split is seven held
against eleven unheld**: five of the seven are §6b's console block (`1326`,
`440`, `1218`, `157`, `858`) and two are §6a's `43` and `4,966`, which
`--check` holds by comparing `ec/annotations/xdata-clusters.csv` cell for cell
and which the old heading therefore called unpinned when they were not. And the
figures that really were unpinned — eight of §6a's per-subset sums, correctly
listed there, and the console block's `9320`, `390` and `50` — were left looking
like company, which is the direction that costs more: the one person who reads
the list and trusts it is the one who needed the warning.

`9320` was the sharpest of the eleven, because it was not merely unpinned. It
was `OWNERSHIP["main_refs"]`, a value in a module-level constant, and **a value
in a constant is a pin-shaped thing**: it sits next to eleven other values that
`--self-test` really does assert, it is documented in the re-pin history above
it (`1062/8546 -> 1218/9320`), and nothing in its neighbourhood says otherwise.
But the key was read by no check at all. `OWNERSHIP`'s own comment already had
the rule — *"the --self-test ownership block asserts all four rather than
leaving the promise to a reader"* (`ec/tools/xdata_register_map.py:1228`) —
thirty-six lines above a promise left to the reader, at `:1264`.

**A pin is a check, not a promise.** That is the sentence the constant's comment
already used for the `--eq-guard` flip's four figures, and it is the rule
applied here to the two that were promises.

## The measurement

`ec/tools/check_doc_figure_pins.py` resolves every numeric figure in a named
section's tables to one of four verdicts and prints the `file:line` that
decided it:

| verdict | what it means |
|---|---|
| `held-by-assertion` | a value in a module-level dict in `ec/tools/*.py` **whose key is subscripted outside the constant's own span**, preferring a subscription inside a `check()`/`assert*` call |
| `held-by-check-literal` | an int constant inside a `check()` or numeric `assertEqual`/`assertGreater` call, **or** a cell on a CSV line the row itself cites, where the CSV is one `xdata_register_map.py --check` regenerates |
| `unheld` | none of the above |
| `not read by this method` | a shape the reader declines — counted, printed with its reason, and **never** failing the run |

```console
$ python3 ec/tools/check_doc_figure_pins.py \
    docs/findings/xdata-census-rederivation-checklist.md --section 2b
    1326  held-by-assertion      ORACLE["distinct"] @ ec/tools/xdata_register_map.py:654, asserted at ec/tools/xdata_register_map.py:3485-3490  [marked held]
     440  held-by-assertion      OWNERSHIP["clusters"] @ ec/tools/xdata_register_map.py:1292, asserted at ec/tools/xdata_register_map.py:3968-3975  [marked held]
    1218  held-by-assertion      ORACLE["main_distinct"] @ ec/tools/xdata_register_map.py:655, asserted at ec/tools/xdata_register_map.py:3485-3490  [marked held]
    9320  held-by-assertion      OWNERSHIP["main_refs"] @ ec/tools/xdata_register_map.py:1264, asserted at ec/tools/xdata_register_map.py:3936-3940  [marked held]
     157  held-by-assertion      ORACLE["extmem_pd_distinct"] @ ec/tools/xdata_register_map.py:649, asserted at ec/tools/xdata_register_map.py:3339-3356  [marked held]
     858  held-by-assertion      ORACLE["extmem_pd_refs"] @ ec/tools/xdata_register_map.py:649, asserted at ec/tools/xdata_register_map.py:3339-3356  [marked held]
     390  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
      50  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
    3948  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
    3206  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
    7189  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
    7935  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
     193  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
     142  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
     279  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
     239  unheld                 no occurrence in ec/tools/*.py and no committed cell  [marked unheld]
      43  held-by-check-literal  cell 43 of ec/annotations/xdata-clusters.csv:4, compared whole-file by --check  [marked held]
    4966  held-by-check-literal  cell 4966 of ec/annotations/xdata-clusters.csv:4, compared whole-file by --check  [marked held]
docs/findings/xdata-census-rederivation-checklist.md §2b: 18 figure(s), 8 measured held, 10 measured unheld, 0 not read by this method (searched 9 module-level constant(s), 175 literal(s) inside a check, and the cited lines of 2 committed CSV(s))
docs/findings/xdata-census-rederivation-checklist.md §2b: the section's own marking agrees with the measurement
```

**Eighteen figures, eight held, ten unheld.** The old heading's "eight" was a
count of table *rows* (five from §6a, three from the console block), and the
issue's own summary said "five of its nine numbers are pinned" — the "nine" is
not a count of anything on this page. The console block prints eight figures and
five of them were held; the two `0.5` threshold tokens the block also prints are
`DEFAULT_THRESHOLD = 0.50` (`ec/tools/xdata_register_map.py:400`) and were
already held. **The measured count is recorded rather than the issue's**, which
is the calibration rule applied to the issue as well as to the page.

The transcript above is a re-run on the tree this change lands in, and its
`175 literal(s) inside a check` is the one figure in it that another issue can
move: the literal search is over *every* tool module, so a suite landing
anywhere under `ec/tools/` changes the denominator without any of the eighteen
verdicts changing. That figure was 167 before #846's
`test_walk_budget_census.py` and 173 on the tree this write-up was written on,
and #801's `ec/tools/check_citation_lines.py` took it to 175 in this merge. Both
ends of that step are measured rather than inferred: running this tool against
`origin/main`'s own copy of `ec/tools/` with that file and its suite moved aside
returns **173** — the figure this paragraph already gives for the pre-#801 tree,
so the whole 173 → 175 is those two modules, and it is a step of 2 rather than
one per case because `check_literals()` keys by value and #801's suite
contributes 2 *distinct* literals. That run reports the same eighteen figures,
seven of them held there rather than eight because the `check()` this issue adds
is not on that tree, and `9320` is the only verdict of the eighteen that differs
between the two. So the denominator moved 173 → 175 while the eighteen figures
did not, which is the shape of the method's one real weakness, named under
*What the method cannot see* below as a search rather than a proof. The 167
figure is quoted from #846's own record and was not re-measured here.

## What the fix was, and what it is not

One `check()` in `ec/tools/xdata_register_map.py`, immediately after the
export-ownership file-wide assertion, asserting the main-EC half of the census
against `OWNERSHIP["main_distinct"]` and `OWNERSHIP["main_refs"]`. It mirrors
the shape the default-census check already uses. A line in the comment block
above the constant names the check that reads the two keys, so the answer to
"what holds this?" does not require reading the file.

`python3 ec/tools/xdata_register_map.py --self-test` prints
`ok  and its main-EC half is 1218 distinct / 9320 references … (got 1218/9320)`
and exits 0. The value is **measured, not copied**: the new check is written
against the constant, and if it comes back red that is a finding to report, not
a constant to edit to match.

**The assertion is the deliverable, not the document.** Since #823
(`244c992b`), `--self-test` runs from the cheap tier at
`.github/scripts/agent-gates.sh:261-263`, so a pin there is a CI failure rather
than a comment — which is what makes §2b's held/unheld split a distinction with
consequences rather than a matter of taste.

## The residual: `390` and `50`

§6b's two cluster counts are genuinely unheld, and only their sum — the pinned
`440` — is. A re-deriver can cross-check the pair by subtraction, and cannot
check either half alone: `390` could move to `389` with `51` beside it, the
census would still print `440 rows`, and the cheap gate would stay green.

A `"clusters_by_program": {"main-ec": 390, "pd": 50}` key on `OWNERSHIP` would
close the pair. **It is not folded in here**, for a reason worth stating rather
than leaving implicit: adding a pin is not the same act as correcting a false
claim. `9320` was a figure the tree claimed to hold and did not; `390` is a
figure nobody ever claimed to hold, and the page now says so. Pinning it is a
new measurement with its own re-derivation story, and it is the natural next
issue rather than something to smuggle in beside a correction.

The eight §6a subset sums (`3,948` / `3,206`, `7,189` / `7,935`, `193` / `142`,
`279` / `239`) are unheld for a different reason and are not fixable the same
way: they are per-subset sums computed inline in §6a's own heredoc, and the
census they come from is the guard-off run, which is written to `/tmp` and
committed nowhere. There is no committed cell for `--check` to hold them to. The
recipe's denominator checks live in
`ec/tools/test_xdata_cluster_names.py:303` and cover §2a's seven, not these.

## What the method cannot see

**Every `unheld` is "not found by this method", never "absent"** — the caveat
`ec/annotations/registers.yaml` carries for a static scan and
`check_cluster_citations.py` for a citation check. Here it is load-bearing
rather than decorative: the verdict on `390` and `50` is *"no occurrence in the
committed tool sources and no committed cell carries it"*, which is a statement
about a search over text and not about the census. The limits worth naming, all
of them in the tool's docstring:

- **The oracle rule is "a value in an all-caps module-level dict whose key is
  read elsewhere".** A dict that is really a data table would make its values
  look pinned. The report prints the definition it resolved to, so a reader can
  see the shape rather than trust the name. The *reported line* prefers a read
  inside an asserting call, and is the whole call's span where there is one —
  `ORACLE["extmem_pd_distinct"]` is first read at the `extmem_both` sum, which is
  arithmetic, and the read that pins it is in the `check()` below. Without that
  preference the report would have cited an assignment and called it a pin,
  which is the same defect one level down. A constant read *only* by arithmetic
  would still measure `held-by-assertion`; that is the rule's weaker half and it
  is stated as such in the docstring.
- **The literal search is over every tool module.** A figure that happens to
  equal an unrelated assertion's literal reads as held. That is the safe
  direction to be wrong in — the report prints the exact `file:line`, and a
  row's own pin has to agree with it — but it is a search, not a proof that
  *this* figure is what *that* check is about.
- **The CSV source is resolved only against the line the row cites.** A 439-row
  `refs` column is full of small integers; searching it for "any cell equal to
  50" finds a `50` that is a different cluster's count and would have called the
  pd-image cluster count pinned. This was not hypothetical — the first version
  did exactly that, and the fixture caught it.
- **This tool's own two modules are excluded from the literal search.** Every
  figure the page lists has to appear in the suite that measures it, so without
  the exclusion `390` and `50` would both measure held the moment a case named
  them. Nothing mechanical can tell a test that pins a figure against the census
  from one that pins it against *this tool's verdict* about the census — they
  are the same call shape, and only the second is circular. That is the general
  limit of the literal search: a figure this tool reports unheld can be "held" by
  a test somewhere, and this tool will not have seen it.

## A `file:line` check, of a kind this tree did not have

`check_doc_links` at `.github/scripts/agent-gates.sh:286` checks that a relative
`.md` link resolves. **Nothing checked a `file:line`**, and these citations move
— the line numbers in this page's own family have already moved under a page
that cited them, which is the standing complaint in
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md) §5.

A `held` row's pin now has to hold up three ways: the file exists, the line is
one it has, and the file it names is the file the measurement resolved to. The
third is what catches a pin that has drifted onto the wrong module rather than
counting it. The shorthand `:1255` names no file and is left alone — it is the
page's own prose, and the reader that owns it does not always say which file it
means.

**This is the one thing here that another page can lean on, and #838 owns stale
pins in this file family.** `xdata-06c2-06db-timers.md` is not touched by this
change at all: its `BUCKET_TOTALS` citation prints `:668` where the constant is
at `:1212-1213`, the checklist already names it, and #838 is the open issue.

## The standing: this tool runs by hand

`check_doc_figure_pins.py` is **not** in `.github/scripts/agent-gates.sh`, and
cannot be from an agent branch: the plan stage's push token has no `workflow`
scope, so a branch touching `.github/` fails at the very end of the run. The
prepared route is a `docs/ci/agent-gates-*.patch` plus a set edit in
`tools/test_agent_gates_patches.py`, and both are a human's change and their own
issue. Until then the tool runs by hand — exactly where
`check_cluster_citations.py` stands today.

**A checker nobody runs is the shape of defect #819 was**, so this is stated in
the tool's docstring, in this file, and in a case
(`TheToolRunsByHand.test_it_is_not_in_the_cheap_gate`) that reads the gate script
and fails if the name ever appears there without the rest of this being updated
with it. The suite is `ec/tools/test_check_doc_figure_pins.py`, 44 cases, and it
is the reason the two directions are demonstrated rather than asserted: a marked
pinned figure going `unheld` is reported, and a table that stops declaring
verdicts at all is reported too, because that second one would otherwise return
the page to its pre-#849 state and report a clean run.

## Suite totals

`tools/README.md` records the runner's last line as `All 30 suite(s) passed, 882
tests` at `64dbde19` and says in the paragraph above the table that those figures
are **re-derived by running the runner, not by arithmetic on a diff**. This
change adds one suite and 44 cases, so both figures move; they are re-measured
rather than computed, because a file that tells its reader to re-derive a number
is not a file to guess one into, and #817 owns re-deriving them in general.
The set of rows in that table *is* checked —
`tools/test_readme_suite_table.py::test_every_discovered_suite_has_a_row`
discovers suites with `find` and fails on one with no row — so the new suite has
a row.

*(Merged-tree note, 2026-09-25: on the tree this change first lands in, #846's
suite sits beside this one, so the re-derived figures are **thirty-two suites and
978 tests** and `tools/README.md` says so, with a merged-tree note naming what
moved them. #846 measured 31/934 on its own tree and re-derived the same two
figures the same way, so the notes do not disagree about the method — only about
which tree each is the record of. The red set is unchanged by either: the
runner's last line reads `32 suite(s) run, 978 tests; one or more FAILED` and
the one red suite is the #822 file's `ec/tools/test_check_cluster_citations.py`,
which fails identically on a clean `origin/main` worktree.)*

*(Second merged-tree note, 2026-09-25: the tree this change lands in also carries
#801's `ec/tools/test_check_citation_lines.py` at 40 cases, so **its** figures are
**thirty-three suites and 1018 tests** — 978 + 40 — with the last line reading
`33 suite(s) run, 1018 tests; one or more FAILED` and the same one red suite,
re-checked on a clean `origin/main` worktree. `tools/README.md` carries both
figures as the records of the two trees they were measured on, and the
thirty-three / 1018 pair as its own. This change moved none of the figures
`check_doc_figure_pins.py` measures: run against the merged tree it still reports
eighteen figures, eight held, ten unheld, and agrees with the page's own
marking, because #801 added no constant and no check that any §2b figure could
resolve to.)*

*(Third merged-tree note, 2026-09-25: the tree this change lands in also carries
#851, which added `census_shape()` and `carry_advice()` to
`ec/tools/xdata_register_map.py` — 80 lines, every one of them above the `check()`
at `:2970` — while this issue added 19 from the other side. **The transcript
above is re-run on that merged tree, not carried across**: all eighteen verdicts
and the `8 held / 10 unheld` split are unchanged, and so is the
`175 literal(s) inside a check`, which #851's new suite did not move because it
contributes no *distinct* literal inside a `check()`. What did move is every
`file:line` in the transcript, and they are re-measured rather than shifted by
arithmetic: `:3406-3411` → `:3485-3490`, `:3889-3896` → `:3968-3975`,
`:3857-3861` → `:3936-3940`, `:3260-3277` → `:3339-3356`. The `ORACLE` and
`OWNERSHIP` definition lines (`:649`, `:654`, `:655`, `:1264`, `:1292`) sit
above both sides' insertions and are unchanged, which is the same reason
`xdata-06c2-06db-timers.md`'s `BUCKET_TOTALS` citation survives at `:1212-1213`.
`ec/tools/test_check_doc_figure_pins.py` pins two of these spans in its own
cases, so it was red for the duration and is green again; both are re-measured
too, and the write-up's own claim that the tree "moves under a page that cited
it" is now a thing that happened to the checker rather than only to the prose.)*
