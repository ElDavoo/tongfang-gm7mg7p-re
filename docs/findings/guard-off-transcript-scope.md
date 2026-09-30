# A census-regeneration transcript is not a citation, and a fenced block is not a transcript either: what the rule scopes, and what it still checks

(2026-09-30, issue #996. Static reading and commands over committed text. No
capture opened, no EC, no hardware, no Windows. `status:` in
`ec/annotations/registers.yaml` is untouched.)

`check_cluster_citations.py` reported two citations in
`xdata-cluster-names-guard-off-recipe.md:220` and would not go green:

```
docs/findings/xdata-cluster-names-guard-off-recipe.md:220: 0x0464 is not a member of any cluster this line names (...); it is a member of `main-ec-145`
docs/findings/xdata-cluster-names-guard-off-recipe.md:220: 0x0465 is not a member of any cluster this line names (...); it is a member of `main-ec-145`
2 citation(s) disagree with ec/annotations/xdata-clusters.csv
```

The line the rule is reading is `:269`, inside the ```` ```console ```` block
that opens at `:220`:

```
mode-oem-init: kefb63d82f8c7 -> kc0f2a0be0103, 92 -> 93 addrs, joined ['0x0464', '0x0465'], left ['0x1804']
```

and `:275-282` says in as many words that the changed key is *why* the name
arrives on overlap at all. **The row is there because the membership changed**,
and the membership rule holds every unit in the corpus to the committed census
— so this unit was being held to the "before" for reporting the "after". The
arithmetic makes it structural rather than accidental: `kc0f2a0be0103` is not a
`cluster_key` in the committed census at all (`grep -c` over
`ec/annotations/xdata-clusters.csv` → 0), so the sentence's "after" is a
membership the tool cannot resolve anywhere.

## The three readings, and which one this took

The issue offers three. This takes the first and rejects the other two on
mechanics, which is the order the argument is worth in:

- **(c), editing `:269` to name `main-ec-145`**, is the one the issue rules out
  and it is right to: it would make the recipe claim that the guard-off run
  reproduces the committed membership, which is the opposite of what it
  measured, and `docs/findings.md` §4a wants that version left visible rather
  than adopted. Not done.
- **(b), pointing the run at a guard-off census**, is a single path for the
  whole run — `--clusters` takes one file for every file checked — so it would
  hold every committed sentence in the tree to the wrong generation and the
  tool would go red somewhere else rather than green. Per-unit census selection
  is not something that flag can express, and committing the 445-row derived
  census would be a hand-kept total the next regeneration invalidates. Not
  done, and the tool says so itself: `--no-eq-guard` is **refused** at the
  committed output paths for the same reason.
- **(a), scope the unit and name the reason**, is what landed. It is also the
  answer to the issue's other question, *what a citation inside a guard-off
  transcript means*: **it is not a citation at all.** A `main-ec-NNN` in such a
  block is a rank in a census the reader cannot open. That is "not found by
  this method" — the same verdict the tool already gives an unresolvable key or
  a name this generation does not carry — and not a disagreement.

## What the scope is keyed on

**A fenced block whose body invokes `ec/tools/xdata_register_map.py` under a
flag that *changes* the census** — `--no-eq-guard` or `--export-ownership`.
`xdata_register_map.py --help` is what settles which flags those are:
`--no-eq-guard` "count `==` as a store, the way the pre-#178 classifier did,
so the guard's effect stays measurable", and `--export-ownership` "read each
routine once, from the export that owns it".

`--map` and `--check` are **excluded on purpose**, and the reason is what they
take rather than what they print. `--map OLD_CSV` reports where each row of an
*older* census went in this one, so its `new_cluster` column is this
generation's committed id; `--check` diffs in memory against the committed
CSVs. Both are keyed to the committed identifiers, so a membership claim beside
either is a claim about the committed census. Scoping them would lose a real
check to save a bookkeeping one. Neither can appear with `--no-eq-guard` at
all — the tool refuses that combination precisely because both are gates. That
refusal, and the separate one on `--no-eq-guard`'s own outputs, are a string
comparison against the committed absolute defaults
(`xdata_register_map.py:5074`): run bare, `--no-eq-guard` would overwrite the
committed CSVs, and passing the same paths relatively would slip past the
comparison. The transcripts here name scratch outputs, which is the form the
guard is asking for.

At this tree that predicate matches 21 fenced blocks across 15 files
(`grep -rhoE '^\s*`{3,}'` over `ec/`, `docs/` and `evidence/` returns 2131 fence
lines, every one of them exactly three backticks, so the width is a
measurement and not an assumption). The count is what the run prints; the
predicate is what the code reads.

## The part that was not in the plan: a fence is a boundary, not a unit

The obvious implementation — make `units()` yield a fenced block as one unit,
and match the predicate against that unit — **breaks the tree.** It was tried
first and measured before anything was written down here.

`docs/findings/reset-vector-dptr-targets.md:451-456` puts a membership claim
in a fence and a second, unrelated claim in the sentence *after* it inside
that same fence, and says why: "in a fenced block rather than a blockquote so
that the split does not depend on where the line breaks fall". That is the
#605 fix. The block's two sentences are only two claims because the walk cuts
the fence into sentences; a fence read as one uncut unit puts the membership
claim and the `setb c` operand back in one sentence and reports `0x0800`, which
is the shape #605 took out.

Measured, over the whole corpus, on the same walk and against the same two
committed CSVs. Only `units()` differs between the three; the two counterfactual
walks are that one function swapped for the `units()` at `origin/main` and for
the shipped one with its in-fence sentence split removed, each loaded as its
own module so the swap is real rather than patched in place:

| walk | problems | file affected |
|---|---:|---|
| before (`units()` at `origin/main`) | 2 | — |
| fence as one uncut unit | 1 | recipe 2 → 0, **`reset-vector-dptr-targets.md:451` 0 → 1** |
| fence as a paragraph boundary, still sentence-split | 0 | recipe 2 → 0, nothing added |

**These three totals are the merged tree's, and the "before" and "fence as a
paragraph boundary" rows were 3 and 1 when this was first written.** The
difference is main, not this change: the third problem in both was the
hand-typed `main-ec-002` count discussed below, and #1438 (`7245cc0f`)
corrected that cell to 32 in the same commit that took the census to 32, so it
is no longer among them. The *deltas* the argument rests on — recipe 2 → 0
under the paragraph-boundary walk, and `reset-vector-dptr-targets.md:451` 0 → 1
under the uncut one — held then and hold now; what moved is the absolute
totals, because a defect on another axis was fixed underneath them. The shipped
walk is `python3 ec/tools/check_cluster_citations.py`, which exits 0 on this
tree.

So the fence is a **paragraph boundary** and not a unit: the walk stops at the
delimiters and at nothing inside them. The sentence split inside a fence is
load-bearing and `test_a_fence_is_still_split_into_sentences` says so against
the real page's two sentences, rather than only asserting the first one's
answer.

That is also why the skip is keyed on a **set of line numbers** rather than on
a predicate over the unit: the command is on the block's first line and the
membership it produced is lines later, and the sentence that gets skipped is
not the sentence carrying the command. `transcript_lines()` is the one place
that decides which lines those are.

## What the exemption is not

A blanket fence-drop is the failure mode, and the committed corpus is what
rules it out — `reset-vector-dptr-targets.md:451` is a real page whose fenced
membership claim is deliberately checkable. Three further boundaries are
pinned, each by a case that was watched for the red:

- a fence with no census-regenerating command is an ordinary claim, and wrong
  membership in one is **reported**;
- a `--map` or `--check` fence is an ordinary claim, and is **reported**;
- the same command named in **running prose** is an ordinary claim. The fence is
  what scopes this; otherwise every write-up that *describes* a guard-off run
  would lose its own membership claims, and there are several.

The sixth boundary is the corpus's own: **a fence still open at the end of the
file is not a fence.** `docs/findings/pd-only-status-vocabulary.md` is the one
page that reaches this — one of its seven fence lines closes a block whose
opener is not there, so every later fence in the file is off by one, and the
last opens a block running to the end. Reading that tail as block body would
join thirty lines of prose into a single unit, which is the opposite of what a
conservative walk is for. Its lines go back to the ordinary walk, where nothing
has scoped them.

A block closes on a fence of **its own width**, so an inner ```` ``` ```` cannot
close an outer ```` ```` ````. The corpus has no nested fence to exercise that,
so it is a claim about today's prose and not a guarantee, and the case that
pins it is synthetic for that reason.

## The blind spot, made countable

A skip nobody can name is the blind spot this exemption creates, so the reasons
are a closed list — `SKIPS` — and the run prints one figure per reason and
names the list in its closing line:

```
skipped: no membership claim 53, disclaims membership 15, census-regeneration transcript 1
```

**The figures are the run's, not this page's, and nothing here asserts how many
of anything there are.** An expected count turns every added transcript into a
failure, and the count belongs to `tools/run-tests.sh`'s last line. What the
suite asserts is that the reason is *exercised*, and the two-direction set
difference over `SKIPS` against what the walk really produced: a reason added to
`skip_reason()` without being written down is named by name rather than
arriving as a figure that moved, and a reason that has stopped firing is named
the same way. This is the shape of `check_testdata_row_claims.py`'s `SHAPES` /
`DATED_REFUSALS`; the reasons are this tool's own. The line above is the merged
tree's run; the corpus gained write-ups on main while this was open, which is
why the two prose figures are higher here than when the skip was first
measured.

Each new case was perturbed — the tool broken six ways, plus `SKIPS` three — and
each break turned at least one case red. The six: the transcript skip removed
from `skip_reason()`, `--map`/`--check` admitted to the predicate, the fence
read as one uncut unit, an unterminated fence allowed to swallow the tail, a
block closing on any fence width, and the predicate widened from "inside a
fence" to "anywhere in the file". A case that cannot fail has not been shown to
check anything.

## The other half of the red suite, which was not this issue's

The issue's "done when" is `run-tests.sh` reporting this suite green, and
**the scoping fix alone does not reach it.** The same run reported a third
problem, from the tool's *other* rule — the hand-typed count one, with nothing
to do with `--no-eq-guard`:

```
ec/annotations/xdata-register-map.md:2212: census count disagrees for `main-ec-002`: 32 named addresses in the census, 27 in the row
```

So the count correction is carried here too. It was not taken on faith: the
committed tool re-run reproduces `ec/annotations/xdata-clusters.csv` **byte for
byte** (`--out-clusters /tmp/…`, then `diff`), and
`ec/annotations/xdata-registers.csv` independently carries exactly 32 named rows
for `main-ec-002`. 32 is what the census derives; 27 was stale.

**There is a three-way discrepancy around that cell, not a two-way one.** The
row said 27, the census said 31, and the §1 merge note at `:478` said the cell
"is 33 for the same reason — 29 was the figure … and issue #272 settled the row
at the census's 33". The note was stale too, so it is corrected in place with
its own dated correction rather than edited out. Both corrections are in the
§4a form with the superseded figure left visible, and the sequence is 19 → 43 →
27 → 31 → 32, with the commits that moved it: `6bf9c234` (#683) set the cell and
the census to 27 *in the same commit*, so the row was right when written;
`31147ccc` (#1059, 2026-09-27) named four addresses inside `main-ec-002` —
`0x074C` `PDIN`, `0x0788` `CTWA`, `0x07A4` `GC6S`, `0x07C5` `WHMS` — taking the
census to 31 without the table following; and `7245cc0f` (#1438, 2026-09-30)
added `XDATA_086C` at `0x086C`, which is a member of `main-ec-002`, taking it
to 32 **and correcting the row to 32 in the same commit**. The thing that
noticed the 27 was the count rule, in a suite that had been red for an
unrelated reason and so had not been run to green.

**The 31 in this section is a superseded figure and is kept deliberately.** The
correction written alongside the branch's fix settled the cell at 31, which was
right against the census as it stood on 2026-09-27; #1438 then moved the census
once more and corrected the row itself. Both are recorded rather than one
replacing the other, because the intermediate 31 is a real reading of the
census and a drift record that erases the step between two surviving figures is
not a drift record. The two corrections do not disagree about anything: they
disagree about which census was current when each was written, and the merged
tree's answer is the one #1438 committed.

Neither correction is a transcription slip. Both times the census moved and the
hand-typed prose did not, which is what the count rule catches for a row and
what nothing catches for a sentence in a note.

## The census question, recorded as not settled

**Is `main-ec-145` a unit of its own, or the tail of the OEM-init fan path? Not
settled here, and not settled by this branch.** What is on the record, from the
committed `ec/annotations/xdata-clusters.csv` row and no further:

- `main-ec-145` is `size 2`, `refs 7`, `addr_range 0x0464-0x0465`,
  `co_reading 1` with `co_reading_refs 3`, and carries **no** `cluster_name`.
- Its `shared_functions` name three routines: `bank0:0x8749=mode_tick_084c_07a5_09ee`,
  `bank0:0xBD5D=be16_0464_0465_minus_100`, `bank0:0xDFDF=gate_06e6_then_store_0464`.
- `0x0464`/`0x0465` is the CPU fan RPM pair, and `registers.yaml` already
  records that the page's label does not cover what is on it, with "what the
  page is" left open.

A `be16 … minus 100` helper over the pair reads as consistently with a shared
two-byte read inside a larger routine as with a standalone unit, so **the tree
does not settle it either way.** That question is a candidate follow-up issue
and is deliberately not closed here — this branch is the red case and the
checker-scoping half, and the issue is right that the two halves should not be
closed by one PR.

## What this is not

- **Not a behavioural claim.** Nothing here says the EC does anything. Every
  figure is a command over committed text with scratch under `/tmp`, and no
  `status:` in `ec/annotations/registers.yaml` moved.
- **Not a new tool.** This is one more reason on an existing tool and one more
  boundary in an existing walk. A separate `--transcripts` mode would be the
  growth `CLAUDE.md` warns against.
- **Not a fence exemption.** It is a skip *inside* the fence boundary, and the
  boundary itself is the thing the new cases hold.
- **Not a new gate, and not a CI change.** Wiring `run-tests.sh` into CI is #162
  and an `agent-pipeline` change; `.github/workflows/` is untouched, and the
  push token has no `workflow` scope.
- **Not a fix for the other red suites.** Each is a separate defect with its own
  owner, and this write-up does not claim to have moved any of them. **The red
  set was measured, not inherited** — on a clean clone of `edf0f4f2` before any
  of this, `tools/run-tests.sh` reported six red suites, and four after this
  branch's base landed:

  | suite | at `edf0f4f2` | after this |
  |---|---|---|
  | `ec/tools/test_check_cluster_citations.py` | FAILED | **green — this issue** |
  | `ec/tools/test_check_eq_guard_citations.py` | FAILED | FAILED |
  | `ec/tools/test_check_doc_figure_pins.py` | FAILED | FAILED |
  | `ec/tools/test_check_pin_table_rows.py` | FAILED | FAILED |
  | `ec/tools/test_check_site_resolution.py` | FAILED | green — see below |
  | `windows/tools/test_gpu_block_watch.py` | FAILED | FAILED |

  **`test_check_site_resolution.py` is the sixth row because it was red when
  this was written, and it is green on this tree for a reason that is not this
  branch's.** It reads `ec/annotations/site-resolution.csv`, which nothing here
  touches (`git log 7245cc0f..HEAD -- ec/annotations/site-resolution.csv` is
  empty); `7245cc0f` (#1438), the base this branch was merged onto, is what last
  changed that CSV and what turned the suite green. The after-column is
  therefore **four** red, and the after-column as first written said five
  because it counted this one — a base-merge effect, not something this branch
  inherited or fixed.

  `test_check_eq_guard_citations.py` is the one a reader might assume is close to
  this issue's subject, and it is not: `xdata_register_map.py` has grown and
  every prose pin of it is now roughly seventy-eight lines short, which is a
  re-pin sweep against a moved source and has nothing to do with how a
  transcript is read. The other three are unrelated tools.

  **The plan this implements listed eight red suites, and two of the eight are
  green at `edf0f4f2`.** `test_census_index_third_column_edits` and
  `test_walk_budget_census` were named in it and are not red; neither reads a
  file this change touches, and `test_walk_budget_census` shells out to
  `git show` and so needs a real clone to be measured at all. The table above is
  what a clean clone reports, and it is why this branch fixes one suite and not
  the eight the plan expected.
