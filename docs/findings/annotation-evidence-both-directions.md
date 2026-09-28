# The `evidence` column, read in both directions, and what the reverse one is for (issue #1004)

`ec/annotations/ghidra-functions.csv` carries the `evidence` column
`CLAUDE.md` calls mandatory and non-empty. Issue #780 taught
`ec/tools/check_testdata_index.py` to resolve an `evidence` column against the
repository root and pointed it at two **fixture** CSVs holding eleven tokens
between them; the annotation CSV, with thousands, was not among them and nothing
read it in either direction. This reads it twice — forwards, every token
answered against the disk, and backwards, every committed `.asm` the column
names or does not — and records the one decision the issue asked to be recorded
rather than discovered.

**The forward half is that check widened, and it is imported rather than
rewritten.** `evidence_pointers()` is the whole of it, so the `;`-split, the
by-name column read, the three verdicts and the calibration wording are one
implementation. A second reader of an `evidence` column would answer "does this
path exist" with its own idea of what a path is, and the two answers would
differ on the first shape neither was written for.

**Nothing here is a live test, and nothing here is a claim about the EC.** No EC
image is opened, no register is read, no machine is touched, and
`ec/annotations/ghidra-functions.csv` and `ec/decompiled/index.csv` are
measured here and not edited. Every negative this file prints is **not named by
this method**, never absent — the line `ec/annotations/registers.yaml` draws for
a static scan, and the reason it is load-bearing rather than decorative is that
a listing is a Ghidra function boundary and it is on disk. What is missing is a
human reading of it, not the file.

**The reverse direction is not gated, and never will be.** The forward direction
is a check whose `missing` fails the run — once a human lands the prepared patch
below, since nothing runs it per commit today. The reverse direction is a
census that exits 0 with findings in hand. The section headed *Forward is a
check; the reverse is a census* says why, at length, because the issue asked for
the decision to be written down and not left to be discovered.

**Until a human lands the prepared patch, no commit runs the widened check.**
The cheap-tier wiring is in `docs/ci/agent-gates-capture-claims.patch`, which is
**not landed by this** and which calls `check_testdata_index()` with no
arguments. That call still works, and it now covers the annotation CSV for
free, so the patch needs no re-cutting: its only `diff --git` is
`.github/scripts/agent-gates.sh`, so it embeds no tool source to go stale. A
branch touching `.github/` cannot land at all — the plan stage's push token has
no `workflow` scope — which is why the wiring stays a prepared patch rather than
becoming a gate in this change.

## The measured state, on this tree

Both transcripts are the tools' own output, and both commands are named beside
them so a reader can re-derive every figure rather than take this file's word
for it.

```
$ python3 ec/tools/check_testdata_index.py --check
13 testdata/ directories: 12 named in the index, 1 self-indexed, 0 gap(s)
28 table row(s), 36 path token(s): 36 resolved, 0 missing, 0 unresolved
28 Feeds cell(s), 30 tool pointer(s): 30 resolved, 0 missing, 0 unresolved
1 self-indexed README(s), 3 table(s), 19 row(s), 21 check(s): 21 resolved, 0 missing, 0 unresolved
2 fixture CSV(s), 0 with no `evidence` column, 10 evidence cell(s), 11 evidence path token(s): 11 resolved, 0 missing, 0 unresolved
ec/annotations/ghidra-functions.csv: 1957 annotation cell(s), 3973 annotation path token(s): 3973 resolved, 0 missing, 0 unresolved
```

Six lines where there were five, and the sixth is this change's. **The first
five are byte-identical to what the same command printed before it**, which is
the point: a direction added to a checker that perturbs the others is a
direction nobody can read the effect of.
`test_check_testdata_index.py` holds both halves of that — that the first five
lines do not move when the sixth does, and that a fixture defect is still a red
run over a clean annotation source.

The sixth line prints **whether or not it found anything**, as the other five
do, because a run that checked nothing and a run that found nothing look the
same from the exit code alone. It is read in `main()` rather than in `check()`
for a mechanical reason worth naming: `Result`'s twenty-four positions are
asserted positionally by `test_an_empty_tree_and_an_empty_index_are_green`, and
a `Result` is a statement about one testdata tree — putting a second tree's
reading on it would make every reader of it answer a different question.

```
$ python3 ec/tools/census_evidence_citations.py
census_evidence_citations.py -- the `evidence` column of ec/annotations/ghidra-functions.csv, both directions

forward, every token resolved against the repository root by check_testdata_index.evidence_pointers()
  1957 evidence cell(s), 0 empty, 3973 evidence path token(s): 3973 resolved, 0 missing, 0 unresolved
  176 of the token(s) name a document rather than a listing (1 .csv, 81 .md, 94 .yaml): counted, resolved, and
  deliberately out of the reverse direction's numerator, because a row citing a write-up has not cited a listing
  ec/decompiled/index.csv carries both bases in one file: `out_file` resolves against
  ec/decompiled/ (2720 of 2720) and `evidence` against the repository root (3973 of 3973).

reverse, every committed .asm named by no token
  2717 committed .asm under ec/decompiled/, 1895 named by an `evidence` cell,
  822 named by none
  annotation rows naming an address with no listing on disk: 0

  area    on disk   uncited  unannotated  cited elsewhere  deliberate 0xFF fill  not yet exported
  bank0       749        77        53        24         0         0
  bank1       674        85        85         0         0         0
  common      753       626       617         9         0         0
  pd          541        34         0        34         0         0
  total      2717       822       755        67         0         0
  the four classes are disjoint and sum to the uncited set, so the last column
  is the uncited count decomposed rather than the uncited count minus something. Of the
  67 `cited elsewhere`, 67 name no `.asm` at all and 0 name a different
  listing -- the two shapes the issue names separately, one class.

  every negative above is not named by this method, never absent: a listing is a Ghidra
  function boundary and it is on disk. What is missing is a human reading of it. The
  class says which rule found the listing, not why nobody has read it, and a
  classification by reason would be a guess -- see the write-up. Closing the 822 is
  its own piece of work and needs per-area reading; this sizes the population and
  stops. No EC image is opened, no register is read, and nothing here was observed
  on hardware.
```

## The two document shapes the issue asked for a rule each, and why they need none

The issue asked for "a rule each" for the 94 `.yaml`, 81 `.md` and 1 `.csv`
tokens, or an explicit `unresolved`. **Measured, they need none.**
`names_a_file()` is an extension test, so a `.md` reads as a path exactly as an
`.asm` does, and all 176 resolve against the same repository-root base the
`.asm` and `.c` tokens use — on the day the check widens, with no rule added and
no token left `unresolved`. A rule for a shape the existing rule already reads
is a rule that cannot fail, which is the "parser guessing"
`check_testdata_index.py` declines to do.

What those shapes *do* need is a distinction the forward direction never makes
and the reverse one turns on, so it is made here and nowhere else: **a row
citing `ec-0x07d0-sites.md` and no listing has not cited a listing.** Those
tokens are counted, resolved, reported on a line of their own, and
**excluded from the reverse direction's numerator**. Folding them in would
report a listing nobody named.

The reverse direction's `missing` is not a second kind of failure either. A
citation to a path that is not there is a broken promise a pull request made,
in either direction, and `check_testdata_index.py` is the tool that fails on
it. The census prints it and exits 0.

## The uncited set, and the four classes it decomposes into

**"Uncited" is not "unannotated", and the census says which it is measuring
before it counts anything.** Each class is a predicate over committed files and
each is printed even at zero — a zero that is computed is an answer and a zero
that is a subtraction is a coincidence.

- *unannotated* — no `ghidra-functions.csv` row at that listing's
  `(scope, addr)`, matched on the four-digit spelling the filename already
  carries. **A set difference over matched addresses, not a subtraction of two
  totals**, per `pd_unannotated_census.py`: subtracting would go wrong the first
  time a row named an address with no listing, and that other mismatch is
  printed on its own line (0 here) rather than allowed to cancel.
- *cited elsewhere* — a row exists at the address and the column does not cite
  *this* listing from it. The issue warns this class is non-empty and it is:
  **67**, in two shapes. 34 are `pd` rows, 24 `bank0` and 9 `common`, and all
  67 name **no `.asm` at all** — a document, not another listing. The other
  shape, a row whose `evidence` names a *different* `.asm`, is **0** here, and
  the tool counts the two apart so a reader can tell which one they are looking
  at. The 34 `pd` rows are the ones `test_pd_unannotated_census.py` already
  records as citing a document and no listing (`pd 0x10BC` names only
  `ec/annotations/ec-0x07d0-sites.md`).
- *deliberate `0xFF` fill* — read through `citation_callers.is_fill`,
  **imported rather than reimplemented**, for the reason
  `census_ff_fill.py` gives: so this tool and the `call_graph.py` veto cannot
  come to disagree about the population. All 30 fill listings on disk are cited,
  which is why this is 0 in the uncited set rather than a coincidence.
- *not yet exported* — the listing's `.c` sibling is absent from `index.csv`'s
  `out_file`. 0 here, and the resolution base is the other one (below).

The four are **disjoint and sum to the uncited set**, which is the claim the
suite asserts on the committed tree rather than the numeral: `822` is a value
every annotation moves, and asserting it is the trap `CLAUDE.md` names four
times. What is asserted is the partition, the per-area arithmetic, the
`resolved = tokens - missing - unresolved` relation, and that the uncited set is
what is left of the listings once the named ones are removed.

## The limit, stated rather than met

The census splits the 822 by **kind of file** and by **which rule found it**.
It does not split them by **reason**, and every one of the 755 unannotated
listings prints as "not named by this method". A reason — nobody has read it
yet, versus it is a one-instruction trampoline that will never be worth a row —
is a **reading**, and a tool that guessed one would produce a figure nobody
here can check. That is the same line `ec/annotations/registers.yaml` draws for
a static scan, and the same line `census_test_line_pins.py` prints.

**So the coverage figure this issue was reaching for is a lower bound with a
named shape, not a list.** It sizes the work: 755 listings with no row at all,
by area, is what closing the reverse direction means. It does not say how much
of that is worth a row.

## `ec/decompiled/index.csv`: two columns, two bases

Its `out_file` resolves against **`ec/decompiled/`** (2,720 of 2,720) and its
`evidence` against the **repository root** (3,973 of 3,973). One file, two
bases, and a reader of one column has to say which it used. The census reads
`index.csv` only for the *not yet exported* class, prints both bases in the
forward direction's block, and its own reader resolves `out_file` at
`ec/decompiled/` — resolving it at the root would call all 2,720 rows absent and
would then put every listing in the tree into "not yet exported", which is a
coverage figure, printed.

This is not a new observation.
`ec/tools/check_fixture_pointer_cells.py`'s docstring already writes the fact up
— *"the fixture's two pointer columns are rooted at different places —
`evidence` at the repository root, `out_file` at `ec/decompiled/` — so
answering needs a per-column base"* — and the suite's `TheTwoBasesInOneFile`
holds the census to it rather than restating it here.

## Forward is a check; the reverse is a census

**Forward = a check, exit 1 on a `missing`.** A cell naming a path nothing holds
is a defect in the file that has to be fixed, exactly as in the fixture
direction, and it is the same defect with a different file attached: a broken
citation in `ec/annotations/ghidra-functions.csv` is a promise a pull request
made about the real tree. The forward direction's 0 missing is the value, not a
null result — it is a fact about committed files, stated as such, and it is
what the next row added with a path nothing holds would turn red. The suite
demonstrates that with a deliberately-broken control: one cell naming a path
that is not on disk turns `check_testdata_index.py` red **and** prints as a
`missing` in the census, from the same scratch tree.

**Reverse = a census the tools print and no gate holds**, the shape
[`test-line-pin-census.md`](test-line-pin-census.md) already is, named here
because naming it is better than discovering it. Three reasons, and they are
independent:

1. **A gated reverse direction fails for a reason that is not a defect.** The
   next time a decompile export lands a listing nobody has read yet — the
   ordinary state of an unfinished reconstruction, and the state this
   repository is in for 822 listings — the gate goes red. A red gate is a
   report of a problem, and a report that fires on the normal state trains
   everyone to read past it.
2. **The count is a value every merge has to edit.** `CLAUDE.md` names this
   shape four times, and a gate holding it would be a floor on the tree: the
   fourteenth fixture-style addition turns it red for no reason a reader could
   act on. This is the same reason `docs/agent-pipeline.md` records about
   gates, and the reason the suite asserts the partition rather than `822`.
3. **The judgement half is a reading and it lives here.** Whether a listing is
   worth a row is a per-area human decision; no predicate over committed files
   answers it, and a gate cannot hold a reading.

The census therefore **exits 0 with findings in hand** and non-zero only when
it **located nothing** — no `evidence` token read at all, or no committed
listing under `ec/decompiled/`. That is
`census_test_line_pins.py`'s convention and the reason for it: a run that found
822 uncited listings and one that read nothing at all both print, and only the
second may claim the tool was broken. "Found nothing wrong" must not be
reachable from the exit code.

## The figures, and the tree each belongs to

The issue's numbers are **its** tip and are left standing beside this tree's,
per `docs/findings.md` §4a-4d rather than edited into. Neither column is
hand-copied into a place no tool regenerates: both are re-derived by the two
commands named above.

| | issue #1004's tip | this tip |
|---|---:|---:|
| annotation rows | 1,914 | **1,957** |
| `evidence` tokens | 3,886 | **3,973** |
| empty `evidence` cells | 0 | **0** |
| tokens that resolve | 3,886 | **3,973** |
| committed `.asm` under `ec/decompiled/` | 2,711 | **2,717** |
| distinct `.asm` named by a cell | 1,852 | **1,895** |
| **named by no token** | **859** | **822** |
| — `common/` (753 on disk) | 626 | **626** |
| — `bank1/` (674) | 85 | **85** |
| — `bank0/` (749) | 77 | **77** |
| — `pd/` (535 on disk) | 71 | **34** |

Three of the four areas are identical between the two tips and only `pd/` moved.
The `common/` figure the issue leans on — 626 uncited of 753, where `0x07D0`'s
callers, the `0x018C`/`0x029B` pair and `0x0CE1` live — **reproduces exactly**.
`pd/` is 34 of the 822, every one of them `cited elsewhere` rather than
unannotated: the 34 `pd` rows that cite a document and no listing, which is the
figure `test_pd_unannotated_census.py` already records.

## What this is not

- **Not a claim about what the uncited listings do.** No EC image is opened, no
  register is read, no hardware or Windows is touched. This is a count of
  committed files.
- **Not a licence to close the 822 by machine.** Adding citations is a
  different piece of work and it needs per-area reading; this sizes the
  population and stops.
- **Not a second `evidence` reader.** There is one reader, in
  `check_testdata_index.py`, and the census imports it. A private copy of the
  token-splitting rules inside the census is the failure the issue is naming.
- **Not an edit to either CSV.** `ec/annotations/ghidra-functions.csv` and
  `ec/decompiled/index.csv` are measured here, unchanged.
- **Not gated, on either half.** The forward check reaches a gate when a human
  lands `docs/ci/agent-gates-capture-claims.patch`; the census runs by hand,
  which is where `census_test_line_pins.py` and `census_ff_fill.py` stand today.
  A checker nobody runs is the shape of defect issue #819 was, so that standing
  is stated in the tool's own docstring rather than left for a reader to assume a
  gate exists.

## Closing the uncited set is its own issue, and it wants one per area

The population is now sized and classified by a tool that re-derives it. What is
left is the part no tool can do: reading 755 listings and deciding which are
worth a row. `common/` is the largest and the one the mission's end state cares
most about — it is where the reachable code a C reconstruction has to cover
function for function lives. Each area is a batch sized by the table above.
