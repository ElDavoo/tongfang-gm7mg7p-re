# A sentence naming two dated captures is refused whole, and not read from the first (issue #979)

The write-up for [issue
#979](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/979), which is
about the one rule in `ec/tools/check_testdata_row_claims.py` that **no case
reached**: a sentence naming two or more bare dates was read from its **first**
match, silently, and both places that said so named the limit in the same words
— the tool's own docstring and the "Not claimed" list of
[`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md).
Every *shape* had an instance in the committed index and every dropped rule had
a case; this one had neither. What this branch adds is **a decision, a seventh
entry of the closed shape list, three cases and a correction in place**: a
sentence carrying two or more bare dates is refused as a whole, counted on the
shapes line under `two dated captures in one sentence`, printed with **every**
glob it named, and read from neither of them.

**Nothing here is a live test, and no capture is opened.** It is a parser
decision over committed text, the same class of claim as both siblings: the
files under `evidence/ec-watch/` are read as text, exactly as `carried_by()`
already reads a fixture, and no EC, no firmware image and no laptop is
involved. **No row of `ec/tools/testdata/README.md` is edited, in either
column** — the index is not edited to make a tool green, and this issue's own
condition forbids it besides. The one line that did change in that file is the
prose paragraph *below* the table, which said "along with a dated capture named
in prose that resolves to nothing" and now names **both** dated refusals; it is
the index's own summary of a rule that moved, not a row and not a claim.

## The census, measured on this tree, 2026-09-26

`grep -noE '`?20[0-9]{2}-[0-9]{2}-[0-9]{2}`?' ec/tools/testdata/README.md` gives
**four** date tokens — line 7 a backticked `2026-01-01` in the preamble, line 19
a backticked `2026-09-23` (row 9), and two **bare** `2026-09-23` on lines 13
(row 3) and 17 (row 7), in two different rows and two different sentences. Row
3's bare date sits in a sentence carrying no address literal at all.

A token census is not a sentence census, so the second one is measured over the
**imported splitter** rather than over a second copy of it:

```
$ python3 -c "
import importlib.util, sys; sys.path.insert(0,'ec/tools')
spec = importlib.util.spec_from_file_location('ctrc','ec/tools/check_testdata_row_claims.py')
ctrc = importlib.util.module_from_spec(spec); spec.loader.exec_module(ctrc)
import check_testdata_index as ctdi
cells = ctdi.table_cells(open(ctdi.INDEX).read(), column=3)
n = [len(ctrc.DATED_CAPTURE.findall(s)) for c in cells for _, s in ctrc.units(c)]
print(len(cells), 'description cells,', len(n), 'sentences,', n.count(1),
      'naming one bare date,', sum(x > 1 for x in n), 'naming two or more')
"
27 description cells, 100 sentences, 2 naming one bare date, 0 naming two or more
```

**So: zero two-date sentences, and zero sentences carrying two bare dates.**
That is *not found by this method*, and it is worth being exact about what it
does and does not say: this census is the tree as it stands, and **nothing in
it proves a two-date sentence cannot appear in a later edit**. That is exactly
why the shape is a counted refusal rather than a deleted code path, and why
`test_the_committed_tree_exercises_every_shape` **stays at five** — a new shape
appearing in the committed index is a change to the docstring's claim about the
tree, not a silent widening of the check, and the test is what makes that true.

`evidence/ec-watch/` is 15 files over three dates:

```
$ ls evidence/ec-watch/ | sed -E 's/^(20[0-9]{2}-[0-9]{2}-[0-9]{2}).*/\1/' | sort | uniq -c
      3 2026-09-18
      6 2026-09-23
      6 2026-09-24
```

## The reading: refused whole, and why not the union

The issue offers two. **This branch takes the refusal**, and declines the
cross-date union on a measured reason rather than a preference:

- **The two sixes are disjoint capture families.** `2026-09-23-*` is the
  power-mode-cycle set (`0751-isolation`, `ctgp-live`, three
  `power-mode-cycle`/`snapshot` files) and `2026-09-24-*` is the `06c2-06db` /
  `06d6` / `06d9` plug-in sweeps plus `2026-09-24-host-window-page-census.txt`.
  Unioning two days hands a sentence about a power-mode-cycle capture a
  **twelve-file set that includes a plug-in sweep**. That is the same
  misattribution the date exists to prevent, along a second axis. The issue's
  observation that "unioning here does not reopen the union the rule forbade"
  is true about **the row's own fixtures** — the `or`-and-never-union rule —
  and says nothing about this one, which is between two *captures* rather than
  between a capture and a fixture.
- **It falsifies a cost the tool documents.** `check_testdata_row_claims.py`
  states the union over a date as *"one address in any of a date's files
  satisfying a claim about that date"*, and the issue's own Done condition says
  that sentence has to **stay true**. A union over two dates keeps the wording
  but not the meaning: the answer to "which files does this claim get checked
  against" stops being a date's files and becomes two dates'. A refusal does
  not touch it.
- **A third reading the issue does not offer is declined for the same reason the
  union-over-a-date is**: narrowing a two-date sentence by a word in its prose,
  to say which literal belongs to which day, is the parser guessing — the exact
  thing the `BACKTICKED`-only entry predicate exists to prevent, and the same
  argument the #794 write-up records against narrowing a *single* date.

So the rule is: **a sentence naming two or more bare dates is not read.** Its
literals come off `checked`, onto the shapes line under a pinned reason, and
`claim.files` names **every** glob the sentence carried, so a report line shows
a reader which dates were skipped rather than that a sentence was.

## What the rule has to have, and where each part is

1. **The single-date path is byte-identical.** `DATED_CAPTURE` does not change;
   only how many of its matches are read does. The six existing dated cases
   pass **unedited**, and the committed tree's run is character-for-character
   what `main` prints apart from the summary line's wording:

   ```
   27 table row(s), 17 literal-bearing: 54 literal(s), 30 resolved, 0 missing, 24 unresolved
   30 claim(s) checked, 15 claiming row(s), 24 passed over under the five shapes and the two dated refusals, each of them: not checked, not absent
   shapes: capture/window bound 16, denial 3, dump-command argument 2, watched-set span 2, firmware code address 1
   dated-capture claims, each held to the captures its date names and never to the row's own fixtures:
     2026-09-23-* (6 capture(s) under evidence/ec-watch, 2 with an addr column): row 7 0x0F58 resolved, row 7 0x0F5C resolved
   ec/tools/testdata/README.md: every address claim in the third column agrees with the fixtures its row names
   ```

   **That is measured rather than argued, and re-measured on the merged tree
   rather than carried.** Run against a clean `origin/main` at `368e9e52` and
   diffed, the two streams come back **stdout differing in that one line of
   wording, and the 24 lines of stderr byte-identical**. The six cases are
   compared method-body by method-body against the tree before either issue
   landed and are **all six byte-identical there too**, so neither this issue
   nor #975's five cases had to edit one of them; the two that did change are
   `test_the_run_reached_something` and
   `test_the_committed_tree_exercises_every_shape`, and both are this rule's
   own label and comment.

   **The `, 2 with an addr column` clause on the dated line is #975's and is
   transcribed from the merged tree's run rather than from this branch's.** The
   branch's own transcript lacked it because the branch never carried #975;
   `testdata-addr-column-claim.md` is where that clause is argued, and the two
   files describe one run rather than two.
2. **The refusal is of the whole sentence, not per literal differently.** The
   reason is checked **first** in `reason_for()`, ahead of the five per-literal
   shapes, because it is a property of the sentence rather than of one literal
   inside it. Every literal of a two-date sentence therefore reads as the same
   refusal, and `missing` stays 0.
3. **Precedence is stated and held.** What decides is the **count** of the
   matches and never what any of them resolves to, so a two-date sentence where
   one date resolves and one does not is still unread, and the empty glob is
   named beside the full one rather than swallowed by the reason that would
   have applied to it alone. One case pins it, because it is the only place the
   two dated reasons genuinely compete.
4. **Both dates reach the per-date breakdown**, each keyed by its own glob with
   its own resolved file count and the sentence's literals listed as
   `unresolved` under both — so a skipped date is visible in the block that
   says the run read dates at all, and not only on stderr.
5. **No `Result` field is new.** The shape is counted per literal in `shapes`
   and the globs travel in the existing `dated` breakdown, so the namedtuple and
   every consumer of it are untouched. `captures_for()`'s third return field
   changed from a glob *string* to a list of `(glob, files)` pairs, which is the
   one signature move, and nothing outside the file calls it.

## The three cases, and the three wrong implementations run against them

All three are in `SkipsDeliberately`, which is where the other six shapes are
pinned, and all three are on **scratch** trees: a case that asserted a
multi-date sentence over the committed index would have to edit the index to
exist, and the index is not edited.

- `test_a_two_date_sentence_is_refused_rather_than_read_from_the_first` — the
  issue's own example, with the literals in the **second** day's captures. It is
  the sentence of the case that already pins the single-date reading, with one
  date added and nothing else changed, which is what makes the *first match* the
  thing under test rather than the date. It also asserts both globs on one
  report line, separator-agnostic, and both globs in the breakdown with their
  own counts and the literals listed `unresolved` under each.
- `test_a_two_date_sentence_is_refused_with_its_literals_in_neither_day` — the
  other half, and what keeps the refusal from being a way of excusing a claim
  that is false: a first-match reading reports these two as `missing` and fails
  the run, which asserts the claim is wrong at a sentence the tool has just said
  it cannot read.
- `test_two_dates_of_which_one_resolves_to_nothing_are_refused_still` — the
  precedence case, with the **empty date written first** so a first-match
  reading would answer `dated capture not found`. The order does not settle
  anything here; the count does, and writing the empty date first is what makes
  the competing reason the one a first-match implementation would reach.

**The mutations, run.** Three wrong implementations were applied to the tool in
place and the suite run over each, so "the fix can fail" is demonstrated rather
than asserted. All three are red, and the failures are recorded because which
case catches which is the point of having three:

| wrong implementation | what it does to the three cases | suite |
|---|---|---|
| **first match** (`DATED_CAPTURE.search`, one glob, no refusal) | second-day: both literals `missing`, `report()` returns 2, the run exits 1 on a sentence the index states correctly, and the report line names `2026-09-23-*` as what the claim was checked against — the issue's own two failure directions, both real | 3 fail |
| **cross-date union** (both globs, paths unioned) | second-day: both literals `resolved` against a set of two unrelated capture families (twelve files, six and six, on the committed tree); neither-day: both `missing` and a red run, for the same reason the first match fails it | 3 fail |
| **a refusal that prints only the first glob** | the two cases that assert both globs in one report line; the neither-day case does not assert on globs and stays green, which is why it is a separate case rather than a fourth assertion | 2 fail |

**`EachRuleIsLoadBearing` has no case for the new rule, and cannot.** That
class drops rules against the **committed** tree, which has no two-date sentence
to change the answer on — the same position the sixth entry is in. The scratch
cases are the pinning, and both class docstrings now say so rather than leaving
the omission to be found.

**`test_the_committed_tree_exercises_every_shape` stays at five**, and its
comment now says that neither dated refusal is named, why neither has an
instance here by construction, and that a sixth instance would be a change to
what the tree exercises rather than a reason to widen the check. **The summary
line's label moved with it** and `test_the_run_reached_something` reads the new
one, because that string is a mechanical read of the printed text and the two
move together.

The suite is 47 cases at this merge's base `368e9e52` and on clean
`origin/main`, and is **50** on the merged tree: this issue's three, the whole
of the step. *(The `42` a first draft of this file read "at the fork", and the
"#975's five" it added to it, are figures from before #982 — which implements
#975 — landed in the base; those five cases are inside the 47 and are not this
issue's, and this merge's counterpart on `main` is **#985**.)* The **3, 3 and
2** in the table above are re-measured on the merged suite, not carried, and
all three wrong implementations are still red on it.

## A known corner, stated rather than left to be found

**The per-date breakdown is keyed per claim**, so a two-date sentence carrying
**no** address literal reaches neither the shapes line nor the breakdown: the
`shapes` and `dated` bookkeeping both hang off the literals loop. That is
deliberate and it is a limit rather than a defect — such a sentence asserts
nothing, so nothing is misattributed by it — and the census above is what says
the corner is vacuous today. Widening the breakdown to record globs for
claim-less sentences is **out of scope**: it would change the behaviour
`testdata-row-claims-dated-capture.md` documents at its "Row 3's bare date"
bullet, and it would buy nothing for a sentence that asserts nothing.

## Not claimed here, and what this does not do

- **That a two-date sentence cannot appear.** The census is *not found by this
  method* on this tree; the rule is held by the cases, which is why the shape
  is counted rather than deleted.
- **Which of a date's files a sentence meant.** Unchanged from #794: the union
  is over the date, and one address in any of a date's files satisfying a claim
  about that date is the documented cost of it.
- **That a fixture or a capture is what its row says it is.** Presence is
  textual over a **fixture**, and the narrower question — *is there a row with
  this in the `addr` column* — is `check_capture_claims.py`'s, over real
  captures, with a different owner. ~~That second sentence is what this branch
  wrote and it is no longer true of the tree.~~ **#975 gave the narrower
  question an owner that could actually reach it, and it is this tool, for a
  *dated* claim**, so the sentence above is corrected in place rather than
  deleted per `docs/findings.md` §4a: `check_capture_claims.py` resolves a
  capture out of a path a unit names and a bare date is not a path, so it never
  saw a dated claim. A claim about a capture is now columnar, a claim about a
  fixture stays textual, and the date in the sentence is what tells them apart.
  See [`testdata-addr-column-claim.md`](testdata-addr-column-claim.md). Nothing
  here is a second opinion on that change — a two-date sentence is refused
  before either reader is reached.
- **A new `Result` field, or a wider `Result`.** The breakdown's shape is
  unchanged; only the number of entries it can hold grew.
- **The gate wiring.** `docs/ci/agent-gates-testdata-row-claims.patch` keeps
  its **hunk untouched** — the CLI does not change, so
  `tools/test_agent_gates_patches.py` still applies the set in every ordered
  pair — and only its header comment is reworded, from "Six shapes are counted"
  to the five shapes and the two dated refusals. It remains a human's
  `git apply`, and no commit runs this check in CI.
- **The `tools/README.md` totals sentence**, which this branch left to the
  merge and the merge has now re-derived. §47 already says it: **a total is a
  property of the merge.** The hazard named below turned out not to apply,
  because the correction can be made *within the lines the sentence already
  had*: `1168` → **`1211`**, with `1161`, `1165` and `1168` left visible in the
  parenthetical beside it per §4a-4d, and `159 + 9 + 7 + 22 + 6 = :203` still
  holding, so the `tools/README.md:203` pin is **not** re-registered in the
  106-row table at [`test-line-pin-census.md`](test-line-pin-census.md) and
  `check_pin_table_rows.py` still reads 106 / 106 / 106 with all seven classes
  0. The **suite count** is the half that moved with the counterpart rather
  than with this issue: `thirty-eight` → **`thirty-nine`**, on #985's
  `ec/tools/test_disasm8051_oracle.py`, the first merge in that file's history
  where a merge had to move it. The merged-tree note beside the sentence is the
  one that carries the arithmetic, and it records two things this branch could
  not have measured: **the `1168` was already stale on `main`**, which measures
  `1177` on a clean `368e9e52` because #982 added nine cases without
  re-deriving it; and that the tree this merge produced is `39 suite(s) run,
  1211 tests` with `907` under `ec/tools`, against clean `origin/main`'s
  `39`/`1208`/`904` — so this issue's step is `+3` tests and no suite. Neither
  side's own figure was the merged tree's, which is the argument for deriving
  it from a run rather than by arithmetic.
- **Live hardware, Windows, or the EC/BIOS/Windows stack.** Nothing here reads
  a register, opens a capture in any sense that touches hardware, or runs a
  capture-producing tool. No `status:` moved, so
  `ec/annotations/registers.yaml` is not touched at all.
- **Anything in another repository.** No PR or issue is opened anywhere; the
  upstream work the mission eventually means is unaffected by this change.

## Follow-ups this opens, stated rather than discovered later

- The shape list is now **seven entries, two of which have no committed-tree
  instance**, so `main()`'s summary line and the docstring both carry a running
  commentary on which entries are instantiated. A seventh refusal would make
  that worse; whether the instantiated subset should be *derived* rather than
  narrated is a question this change raises and does not answer.
- The per-date breakdown is keyed per claim, so a two-date sentence carrying no
  literal reaches neither output line (the corner above). Vacuous on this tree;
  it is the thing to revisit if such a sentence ever appears.
- The union-over-two-dates reading is declined on a measured reason, not on a
  principle that settles it forever. If `evidence/ec-watch/` ever holds a date
  whose files are one family, the reason weakens and the reading is worth
  re-deciding on the evidence rather than on this page.
