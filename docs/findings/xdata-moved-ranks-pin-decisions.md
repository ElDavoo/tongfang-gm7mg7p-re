# The two pins into `xdata_moved_ranks.py` are decided, and both were carried by real trees (issue #961)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over this repository — a grep, a census, `git show` — and
the only inputs are committed files. Same framing as
[`test-line-pin-census.md`](test-line-pin-census.md) and
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md), both of which this is a
follow-up to and neither of which this re-opens.

**The finding is a refutation, and it is the more useful half.** The issue holds
that `:181` and `:243` are *"not 'drifted from a correct value' but values no
tree carried."* §5 walks every commit that touched the tool and puts
`write_movement` at **`:181`** and `deciles` at **`:243`**, on named commits. Both
values were correct on a tree that carries them, and both have drifted since,
which is a different record from the one the issue asked for and a stronger one:
the superseded value is now attributable to a specific commit instead of being an
orphan line number. **The two *decisions* the issue asked for are unchanged by
this** — `:181` repoints and `:243` is recorded — because both were about what is
true on the merged tree, and neither depended on the question §5 settles.

## 1. The premise that does not hold, and what replaces it

The issue asks for these two pins to be reconciled by
`ec/tools/census_test_line_pins.py --verbose` and registered in
[`test-line-pin-census.md`](test-line-pin-census.md)'s per-pin table.
**That tool cannot see either pin.** Its population is `test_*.py` only — the
regex is `(?P<path>[\w./-]*test_[a-z0-9_]+\.py)`, declared on line 113 of
`ec/tools/census_test_line_pins.py` — and a run on this tree counts 106 pins
in 28 markdown files, none of them into a non-test module. `grep -c
xdata_moved_ranks` over its `--verbose` rows returns `0`. That is the mechanical
reason three merges walked past these two: **they are not in the class the census
measures.**

**The class is a regex, and it is worth being precise about how loose it is**,
because the looseness cuts both ways. The `[\w./-]*` in front lets any directory
prefix match, so a citation of the census's *own* filename is inside the class
it measures — `census_test_line_pins.py` contains `test_line_pins.py`. Writing
that citation with a line number is therefore not free: it adds a real pin, and
`check_pin_table_rows.py` then reports a record with no table row and goes red.
This file's own first draft did exactly that, and the gate caught it, which is
the check working rather than the check being wrong. **The citation above is
phrased as "line 113 of" for that reason** — the line is still cited, and the
pin is not created.

The table cannot take a row for them either, and this is the part that would
break something. [`check_pin_table_rows.py`](../../ec/tools/check_pin_table_rows.py)
reconciles that table against `census_test_line_pins.py`'s own records and reads
**106 rows / 106 records / 106 placed** today. A row for a pin the census does not
count makes the two irreconcilable — a green check red.

**Reading taken:** the decision *vocabulary* (`carries` / `records another
line` / `does not carry`) is borrowed from
[`test-line-pin-census.md`](test-line-pin-census.md) §"The ten that record
another line", and the reconciliation is done as a **census scoped to this one
module** — §2 — written up here. The `test_*.py` census is still run, in §8, to
show this change moved **no** pin in the class it does measure.

**Left out on that reading:** a resolver for the general `.py:NNN` class. That is
#914's census (373 occurrences / 229 targets / 34 files), it is broader, and
building a module-scoped one here would duplicate the mechanism #914 is about to
land. So **no new tool and no new suite** in this change. The knock-on is
deliberate and worth stating: with no new suite, the census's `read N markdown
file(s)` goes `153` → `154` (this write-up) and its `38 test file(s)` stays `38`,
so **exactly one published figure moves and it is a denominator.**

## 2. The module-scoped census

The enumerator, and the reason the two pins went unseen is not that they were
missed by a sweep but that **no sweep of the class existed**:

```console
$ grep -rno 'xdata_moved_ranks\.py:[0-9-]*' --include=*.md . | grep -v '^\./vendor' | grep -v 'xdata-moved-ranks-pin-decisions.md'
./tools/README.md:372:xdata_moved_ranks.py:243
./tools/README.md:462:xdata_moved_ranks.py:243
./docs/findings/xdata-decile-small-set-contract.md:111:xdata_moved_ranks.py:487
./docs/findings/xdata-moved-ranks-collision-scope.md:39:xdata_moved_ranks.py:695-702
./docs/findings/xdata-moved-ranks-collision-scope.md:344:xdata_moved_ranks.py:243
./docs/findings/xdata-write-direction-correction.md:38:xdata_moved_ranks.py:181
./docs/findings/xdata-write-direction-correction.md:155:xdata_moved_ranks.py:181
./docs/findings.md:9692:xdata_moved_ranks.py:436
```

**Eight spellings on eight lines, and that is a floor.** The same sentences carry
**elided** pins the pattern cannot see — `tools/README.md:372`'s `:277` and
`:332`, `tools/README.md:462`'s `:436`, `:485` and `:255`, and
`xdata-write-direction-correction.md:38`'s `:270-283` and `:1215-1277`. The table
below is therefore a reading of the **citing lines whole**, with the grep as the
enumerator and the elided forms named as elided.

**This file is excluded from its own population by name**, the way
[`test-line-pin-census.md`](test-line-pin-census.md) excludes itself, so the
block above and the re-run published under it are one population: the eight are
the tree as it stood before this write-up, the twelve are the tree with it.
Drop the second `grep -v` and this file's own eleven spellings join the count —
23 rather than twelve — which is the enumerator seeing its own result, not a
discrepancy to be resolved at the next merge.

**The amendments move the count too, and in the one direction they should.** On
the merged tree the same grep returns **twelve** lines rather than eight. The
extra four are this change's own decision markers, and all four re-name the same
superseded value rather than asserting a fresh one:
`tools/README.md:470`, [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md):360
and `:416`, and
[`test-line-pin-census.md`](test-line-pin-census.md):1707. **Eight citing lines
became twelve, and not one of the four additions is a new claim about the
present tree** — which is the §4a-4d shape, so the growth is the treatment
working rather than the tree drifting further. The eight originals are all still
present at the lines this table cites.

| citing line | spelled | resolves to | what `:NNN` is now | decision |
|---|---|---|---|---|
| [`xdata-write-direction-correction.md`](xdata-write-direction-correction.md):38 | `:181` | `write_movement` at **`:257`** | prose inside `collision_line`'s docstring (`collision_line` at `:170`, `moved_ranks` at `:200`) — prose #929 added | **carries** → repointed to `:257` |
| [`xdata-write-direction-correction.md`](xdata-write-direction-correction.md):155 | `:181` | same | same | **carries** → repointed to `:257` |
| [`xdata-write-direction-correction.md`](xdata-write-direction-correction.md):38 (elided) | `:270-283` | `pair_report` at **`:306`** | prose inside `write_movement`'s docstring (closes at `:284`) | **carries** → repointed to `:306-313` |
| [`xdata-write-direction-correction.md`](xdata-write-direction-correction.md):38 (elided) | `:1215-1277` | `self_test` at **`:1220`** | the tail of `write_census` and the head of `self_test`; the four cases are `+199` lower, the `write_movement` one at `:1455` | **carries** → repointed to `:1413-1476` |
| [`../../tools/README.md`](../../tools/README.md):372 | `:243` | `deciles` at **`:487`** | prose inside `rank_of`'s docstring (`rank_of` at `:234`) | **records another line** |
| [`../../tools/README.md`](../../tools/README.md):372 (elided) | `:277`, `:332` | `deciles` at `:487` | — | **records another line**; §5 confirms both were real values, on `d62730e1` and `bdfddcfd` |
| [`../../tools/README.md`](../../tools/README.md):462 | `:243` | `deciles` at **`:487`** | same | **records another line** — but the sentence is *also* making a live claim, amended in §4 |
| [`../../tools/README.md`](../../tools/README.md):462 (elided) | `:436` → `:485`, and `:485`/`:255` | `deciles` at `:487`, `write_movement` at `:257` | — | **does not carry** — a live claim, measured wrong; corrected in §4 |
| [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md):39 | `:695-702` | commit-qualified: `31f683e5`'s own copy | **resolves there** — the hand-rolled `duplicate_keys` block `collision_line` replaced | **carries** |
| [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md):344 | `:243` | — | the deferral bullet that *names* this pin as stale | **records another line**; decision taken beside it in §4 |
| [`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md):111 | `:487` | `deciles` at **`:487`** | — | **carries** — the repoint #929 already did |
| [`../findings.md`](../findings.md):9692 | `:436` | `deciles` at `:487` | — | **records another line** — a §4a-4d record of that repoint, and true as written |

**The one row that surprises is `:695-702`**, and it is the control: it is the
only pin in the family qualified by a **commit**, and a commit-qualified pin
cannot drift, because the commit's copy of the file does not move. It resolves:

```console
$ git show 31f683e5:ec/tools/xdata_moved_ranks.py | sed -n '695,702p'
    for census, label in ((committed_a, "A"), (committed_b, "B")):
        dups = duplicate_keys(census)
        if dups:
            named = "; ".join(f"{k} on {', '.join(ranks)}" for k, ranks in dups.items())
            out.append(f"  generation {label} cluster_key COLLISION: {len(dups)} of its "
                       f"{len(census)} keys carried by more than one rank ({named}) -- "
                       f"the rows below and the counts that follow them are over the "
                       f"key, so a shared key hides a rank")
```

That is the hand-rolled collision block `collision_line` replaced, which is what
the row claims it is. **This is also already in
[`test-line-pin-census.md`](test-line-pin-census.md)'s supersession-shape table**
— *"a pin qualified by a commit — '…(`:3608` at `c9e72c1`)'"* — so the family
here is not a new shape; it is that shape, already named, sitting outside the
census that would have held it.

## 3. `:181` — **carries**, and is repointed to `:257`

[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md):155
sits under `## What the code does now`, so the citation is live prose about the
tool as it stands and wants repointing. `def write_movement(` is at
`ec/tools/xdata_moved_ranks.py:257`. `:38` names the same line and moves with it.

`:181` stays written beside the correction per §4a-4d, together with **what
`:181` turned out to be** — prose inside `collision_line`'s docstring, added by
#929 itself, so the value a reader finds at `:181` today is a sentence about a
function that is 87 lines further down.

**Two more drifted pins into the same module, in the same sentence, which the
issue's own scope clause assigns here.** `:38` also says *"the `pair_report` block
at `:270-283` and the four cases at `:1215-1277`"*, and both are drifted the same
way:

- **`:270-283` → `:306-313`.** `:270-283` is now prose inside `write_movement`'s
  docstring — its closing `"""` is at `:284`. `def pair_report(` is at `:306`, so
  the block that was named is the def and the head of its body.
- **`:1215-1277` → `:1413-1476`.** `:1215-1277` no longer contains what it names.
  `def self_test()` is at `:1220`, but the span lands on the tail of
  `write_census` and `self_test`'s first four lines; the four cases the write-up
  meant are 300 lines further down, the `write_movement` one among them the
  only mention of the function inside `self_test`. Repointed to a span
  **measured at implement time**, recording what its superseded span turned out
  to name.

**`:1215-1277` was very nearly exact when it was written, and the repoint is
therefore derived rather than chosen.** The block is `:1214-1277` at `bdfddcfd`
and `:1413-1476` on this tree — the write-up's left edge was one line tight, and
its right edge was exact. Every landmark moves by the same `+199`:

| landmark | `bdfddcfd` | this tree | Δ |
|---|---|---|---|
| block opens (`# \`pair_report\`'s §6a line, which had no case`) | `:1214` | `:1413` | +199 |
| 1st `check(` — registers, `net +5` | `:1221` | `:1420` | +199 |
| 2nd `check(` — `net +0` | `:1238` | `:1437` | +199 |
| 3rd `check(` — `movement == (3, 7, -4, …)` | `:1256` | `:1455` | +199 |
| 4th `check(` — the `closes:` line | `:1272` | `:1471` | +199 |
| block ends (blank, before the next `# ---`) | `:1277` | `:1476` | +199 |

```console
$ CASES=(-e 'check(any("references entering write 5' -e 'check(any("references entering write 4'
$ CASES+=(-e 'check(movement == (3, 7' -e 'check(any("write changes 1 of 1')
$ git show bdfddcfd:ec/tools/xdata_moved_ranks.py | grep -nF "${CASES[@]}" | cut -d: -f1
1221
1238
1256
1272
$ grep -nF "${CASES[@]}" ec/tools/xdata_moved_ranks.py | cut -d: -f1
1420
1437
1455
1471
```

The four cases are the same four cases, matched by their assertions rather than
by their offsets, so this is a measurement and not a choice of where to point.

## 4. `:243` — **records another line**, and three live values beside it

[`../../tools/README.md`](../../tools/README.md):372 is inside a merged-tree note
*quoting history* — *"which is `def deciles()` on `main`, `:277` after #891 and
`:332` on this branch beside it"*. **The stale `xdata_moved_ranks.py:243` is the
content of the sentence**; repointing it would edit a record of a past tree into
a present one. It is recorded in the shape
[`test-line-pin-census.md`](test-line-pin-census.md) already has for this class
and no third invented one: **records another line** — a correct sentence about a
line that has moved, correct *because* the superseded value stays visible.

`deciles()` is at `:487`. `:462`'s `:243` gets the same decision for the same
reason (*"neither was at `:243`/`:181` on this merge's base `31f683e5`"*): it is
history inside a live sentence.

**But `:462` is not only quoting history — it is also making a live claim that
is now wrong.** It reads *"`deciles()` is at `:485` and `write_movement()` at
`:255` here"*, and those are `:487` and `:257` on this tree. The same sentence
also says the [`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md)
pin *"moves from **`:436`** to **`:485`**"*, and the repoint actually landed on
`:487` (that write-up's `:111` and
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md) §5
both say `:487`). All three are amended in place, with `:485` and `:255` left
written — each true of the tree it was measured on.

The distinction the row in §2 draws is the one that matters: **the same sentence
carries one pin that records history and two that assert the present tree**, and
they take different verdicts because they make different kinds of claim. Deciding
the sentence as a unit would have meant either editing a true record or leaving a
false claim standing.

## 5. The history walk: both values were carried by real trees

The issue's point is that `:181` and `:243` are *"values no tree carried"* rather
than drifted values, and that the distinction must stay visible. **Settle it by
measurement, not by assertion.** `agent-implement.yml` checks out with
`fetch-depth: 0` (`.github/workflows/agent-implement.yml:118`), so the full
history is here; *this plan* was written against a depth-1 checkout, which is
exactly the case CLAUDE.md's "your runner is not the one the change gets built
on" warns about.

Every commit that touched the tool, oldest first, with both definitions located
in that commit's own copy:

```console
$ git log --format=%H -- ec/tools/xdata_moved_ranks.py | wc -l
8
$ for c in $(git log --format=%H -- ec/tools/xdata_moved_ranks.py | tac); do
>   wm=$(git show $c:ec/tools/xdata_moved_ranks.py | grep -n '^def write_movement' | cut -d: -f1)
>   de=$(git show $c:ec/tools/xdata_moved_ranks.py | grep -n '^def deciles' | cut -d: -f1)
>   printf '%s  %-6s %s\n' "$(git show -s --format=%h $c)" "${wm:-absent}" "$de"
> done
f7d77a2c  absent  218
32218840  absent  218
a01e5c49  absent  243
92ce6938  absent  243
d62730e1  absent  277
bdfddcfd  181     332
31f683e5  227     436
f271c1c2  257     487
```

**Both questions the issue asks are answered "yes", and that is the finding:**

| | asked | measured |
|---|---|---|
| did `:181` ever name `write_movement`? | "values no tree carried" | **yes** — at `bdfddcfd`, and only there |
| did `:243` ever name `deciles`? | "values no tree carried" | **yes** — at `a01e5c49` and `92ce6938` |

`bdfddcfd` carries `def write_movement(on, off):` at exactly `:181`, and `a01e5c49`
carries `def deciles(sizes):` at exactly `:243`. **Both values were correct on
the trees that carry them**, which is all this establishes: it does not follow
that the write-ups were measured on those two commits, and `a4f967ed` being
unreachable means the write-up's own account of which commit it cited cannot be
checked at all. What can be said is that §"The values to cite" in
[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md):38
names values that some commit in this history really did carry, and that the
sentence is right about that tree and wrong about this one.

**The three figures the write-ups report, confirmed on the same walk.**
`31f683e5` is reached and agrees: `deciles()` at `:436`, `write_movement()` at
`:227`. `d62730e1` is reached and agrees: `write_movement` **absent** from that
commit altogether, which is what the write-up says and what makes `bdfddcfd` the
first commit in which the function exists at all. **`a4f967ed` is unreached** —
`git cat-file -t a4f967ed` reports `fatal: Not a valid object name`, so it is
not a commit in this repository and is reported as **unreached rather than as
agreeing**. It is named in
[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md):34
as a commit `a4f967ed` "adds `write_movement()` ... on top of" `d62730e1`; the
function's first appearance this walk found is `bdfddcfd`, and nothing here
settles whether the two names are the same change recorded twice, the alias of a
commit that was rewritten, or two different commits of which one is not reachable
from this branch. **That is a separate open question, not a finding**, and it is
recorded here so the next pass does not re-derive it.

## 6. The §4a-4d treatment, file by file

Per [`../findings.md`](../findings.md) §4a-4d the superseded text stays visible
and is corrected beside it rather than edited down. Every superseded value this
change produces — `:181`, `:243`, `:270-283`, `:1215-1277`, `:485`, `:255` — stays
written beside its correction, **and each is true of the tree it was measured
on**, which §5 now shows for `:181` and `:243` by commit.

- **[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md)**
  — in place, because the decision has to live next to the citation. `:38`'s
  three values repointed, `:155` repointed with `:38`, superseded values visible,
  one short pointer here. **Line-count neutral above `:155`**, which sits 117
  lines below `:38`: house precedent for exactly this is
  [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md)'s
  "the repoint was line-count-neutral above the second of them". Kept neutral so
  `:155` stays `:155` and §2's citing-line column is not self-invalidating.
- **[`../../tools/README.md`](../../tools/README.md)** — in place, because the
  citations are there. `:372` gets the records-another-line marker; `:462` gets
  the amendment and the `:436` → `:487` correction; one pointer, after `:462` so
  it can grow. **Line-count neutral above `:462`**, which sits 90 lines below
  `:372` — both stay exactly where §2 cites them. No suite is added, so
  [`test_readme_suite_table.py`](../../tools/test_readme_suite_table.py) — which
  requires every discovered suite to have a row and every row to name a
  discovered suite — is untouched and stays green.
- **[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)**
  — in place, small. §5's deferral bullet keeps the sentence it wrote and takes
  the decision beside it; §6 gains the supersessions.
- **[`test-line-pin-census.md`](test-line-pin-census.md)** — **one short pointer
  only**, appended in "What is left, as follow-ups": this class is `test_*.py`
  only, so a pin into a non-test `.py` is outside it and outside the table, and
  these two were decided here. Without it the next merge reads that file's own
  follow-up list and re-raises. Its transcript's `read 153 markdown file(s)` is
  deliberately **not** edited — that is its own re-derivation at its next merge,
  and touching a 2500-line shared file for a denominator this change caused is
  the conflict CLAUDE.md warns about.

**Deliberately not touched, named so the choice is on the record:**
`ec/tools/xdata_moved_ranks.py` (no code change — the pins were wrong, not the
tool); [`../findings.md`](../findings.md) (a 9,000-line shared file, and its
`xdata_moved_ranks.py:436` at `:9692` is a §4a-4d record of the repoint and stays
true); [`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md)
(`:487` already carries); `ec/annotations/registers.yaml` and the annotation CSVs
(no register status moves).

## 7. What this does not check

- **Whether a cited line still carries its claim** is a reading, not a
  measurement, and every "resolves to" in §2 is one. §2's `decision` column is
  the same kind of reading as
  [`test-line-pin-census.md`](test-line-pin-census.md)'s verdict column, and is
  not derived by any command in §8.
- **The general `.py:NNN` class** — 373 occurrences, 229 targets, 34 files — is
  #914's, and is neither measured nor decided here. The six `> 300` pins into
  `test_xdata_cluster_names.py` are #920's, and are a different module; they stay
  there, and nothing above registers or re-derives them.
- **Whether the family has no others.** This scope is *pins into
  `xdata_moved_ranks.py`*, which is what
  [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
  §5 says of the deferral this closes: *"Those two are the ones this change can
  see; it is not a claim that the family has no others."* A pin into any other
  file is out of scope, and the eight citing lines §2 enumerates are the whole
  population **of this module** as it stood before this change, not of the class —
  the four the amendments add are the decision markers, and they name the same
  superseded values rather than reaching further.
- **The `/tmp` scratch-directory leak** `--self-test` opens and never removes is
  untouched, on purpose:
  [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
  §"What this opens" already files it as a separate defect, and fixing it is not
  this change's to do.
- **`a4f967ed`**, per §5, is unreached and its relationship to `bdfddcfd` is not
  settled here.

## 8. The test that proves it

**1. The `test_*.py` census is unmoved by this change** — the check that would go
red if the two decisions had been registered as rows in the class it does not
measure:

```console
$ python3 ec/tools/census_test_line_pins.py
106 pin(s) in 28 markdown file(s): 79 distinct spelling(s), 58 distinct resolved target(s)
  74 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 32 declined
  5 def test_, 19 assertion, 10 comment, 6 blank, 34 other (of the pins that resolve)
  read 154 markdown file(s) under the tree, excluding .git/vendor/ and docs/findings/test-line-pin-census.md; resolved against 38 test file(s) in it
  no claim is measured here: whether a cited line still carries the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
```

Identical to the pre-change run but for `153` → `154` markdown files, the `+1`
being this write-up. **Exactly one published figure moves and it is a
denominator.**

**2. The per-pin table is still reconcilable** — 106 rows against 106 records, so
the two stayed consistent and the two decided pins were not registered in it:

```console
$ python3 ec/tools/check_pin_table_rows.py
106 table row(s) against 106 census record(s) under …: 106 placed
  0 unparsed-row, 0 unplaced-row, 0 row-without-record, 0 duplicate-key, 0 read-differs, 0 shape-differs, 0 path-differs
  no verdict cell was read: whether a cited line still carries the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
```

**3. The module-scoped census itself** is the §2 enumerator, and every row of
§2's table is re-derivable from it plus `grep -n '^def '` on the tool.

**4. The history walk** is §5's transcript, printed per commit.

**5. The tool is untouched** — 53, which is what proves the doc edits moved no
code line and no published figure:

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test | grep -c '^  ok'
53
```

That is also the figure
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md) §7
publishes, and §5 of that file's `:487`/`:257` re-measures correctly; both are
re-derived here rather than assumed, and neither is amended.

**6.** `python3 tools/test_readme_suite_table.py` green, and
`.github/scripts/agent-gates.sh` for the mechanical half — including
`check_doc_links` over this file's relative links.

**None of this is a hardware, firmware or Windows observation**, and the PR says
so.
