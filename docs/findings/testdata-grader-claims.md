# What the testdata index's claims about the grader's own output grade to (issue #1007)

The write-up for [issue
#1007](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1007), which asked
for the join `testdata-row-claims-repair-measurement.md` left open by name.

## The gap this closes, in the words of the thing that left it open

[`testdata-row-claims-repair-measurement.md`](testdata-row-claims-repair-measurement.md)
measured that `check_testdata_row_claims.py` reported 0 `missing` over the
pre-repair tree at each of the index's hand-repairs, and gave the reason: the
rows those repairs rewrote spell **zero** backticked `0xNNNN` literals, because
both rewrote prose about mark labels, block membership and which grader branch
a run reaches. It then names the follow-up under **Left open, for the follow-up
pass**:

> A checker that reads marks, not addresses. The rows #502 and #720 repaired are
> about mark labels, block membership and where a count is taken. Whether a
> fixture carries the mark its row describes is a real question with a different
> owner, and `test_grade_0751_isolation.py` already grades the *run* — the gap
> is between the index's prose and that grader, and this measurement does not
> close it.

**This closes it.** `ec/tools/check_testdata_grader_claims.py` reads the same
column for the kind of claim the address reader cannot reach and decides it by
running the grader over the set the row's first column resolves to.

**Nothing here is a live test.** The fixtures are committed text, the grader is
committed code, and the index is a committed document. No capture is opened, no
EC is read, no firmware image is loaded, and no laptop or Windows machine is
involved. The issue correctly takes no `needs-hardware-test` label.

## What it decides, and with what

The index's third column names note constants rather than their prose —
`` `UNPLACED_GRADED_NOTE` ``, `` `UNREAD_MARK_NOTE` `` — so the right-hand side is
the grader's own module-level string, formatted with the numbers the row states.
`grade.UNPLACED_GRADED_NOTE.format(unplaced=2, graded=8)` appearing in what the
run printed is the claim; nothing re-spells the note. The same holds for the
withheld banner, located by the counts in front of `grade.WITHHELD_REASON`, and
for the block verdicts, read off the tool's own `block K/M: VERDICT` line.

The `N of the M` stem is printed in three grammatical places and a bare substring
test would be wrong on two of them, so **the context is the closed entry and not
the number**. Row 30 writes two counts in one sentence — "the withheld banner's
`1 of the 8` against the count line's `1 of the 7`" — and **the two
denominators differ**, which is the property the index says makes that run the
one that can tell where a count is taken. A rule reading one stem for both would
find the same pair in both claims and pass the sentence it was written to make
disqualifiable.

The claim's own clause is what says what it is about. Row 30's sentence is about
`unplaced-window/` and about its own set in the same breath: the `exits 0` sits
*after* a reference to the other set and the `exits 1` two clauses earlier sits
before one, and a whole-sentence reading would decline both or neither.

**Which run a claim is read at is carried forward within its sentence, not taken
from the claim's own clause.** A sentence names its run once and the claims
behind it inherit that, and reading the clause alone loses it: row 29 states "a
`--block 0xA0` run over it is what shows why: the per-block sentence prints, the
count line and `UNREAD_MARK_NOTE` do not, exit 0", where the `:` cuts the clause
and the `--block 0xA0` behind it is not in scope where the note and the exit code
are read. Under that reading both were decided against the **whole-capture** run
instead — where `UNREAD_MARK_NOTE` is absent for an unrelated reason, that run
reaching the `graded_unplaced` branch — and the `--block 0xA0` run the sentence
names was never made at all. A green no run earned, and the same class of blind
spot the join was built to close. The scope is resolved once per claim and handed
to both the decline and the decision, so the two cannot answer "is this claim
about a scoped run?" differently.

## What the first run of this measurement got wrong

Recorded because the correction is the point, not because the first version was
worth keeping for its own sake. Two classes of claim this checker was written to
hold were being decided against the wrong run or not read at all, and both were
green — the run below reports every claim agreeing:

  * **A `--block` claim read unscoped.** As above: four claims that are actually
    read — row 29's `UNREAD_MARK_NOTE` and `exit 0`, row 30's `intact` and
    `exits 1` — were decided against a whole-capture run the sentence had
    already named a scope for. Mutating that run's output, making the
    `--block 0xA0` run over `unplaced-window/` print `UNREAD_MARK_NOTE`, left
    the claim `resolved` and the missing count at zero, because the run was never
    graded. Row 30's `exits 0` sits behind the same scope but is declined as
    another row's claim before the scope is used, so it is not counted here.
  * **A claim dropped without being counted.** The rule that stops a
    `N of the M` written against a note constant from being read twice dropped
    *whatever* followed a note, which took the `exit 0` out of row 29's own
    sentence. A decidable claim reached neither the claim list nor the decline
    list, so the census gave a reader no way to know it had never been looked at
    — the silent cap this tool's own reasoning argues against. The rule is now
    narrowed to the count it was written for.

Both are now caught by cases in `test_check_testdata_grader_claims.py` that
mutate the **run** rather than the rule, and both mutations fail that suite.

## The measurement

`python3 ec/tools/check_testdata_grader_claims.py --check`, over the tree as it
stands:

```
37 row(s) read, 5 carrying at least one claim: 13 claim(s) checked, 0 disagreeing
37 sentence(s) carried a trailing 'not a prediction' clause, stripped before any claim was read
  declined row 24 movement restatement: ...
  declined row 30 another row's fixture (unplaced-window): ...
  declined row 30 another row's fixture (unplaced-window): ...
shapes: note printed 1, note withheld 1, exit code 2, block verdict 4, withheld banner count 3, unplaced note count 1, window count 1
declines: another row's fixture 2, not this grader's row 0, no capture in the row's file set 0, withheld count not in whole-capture spelling 0, movement restatement 1, no closed shape 0
```

**Every claim agrees.** The rows carrying a claim are the ones the issue named —
`3blocks-moved/`, `unplaced-window/` and `unread-window/` — plus two it did not:
`unplaced-window-failures/`, whose "the 2 withheld of 8 are the strays" reads as
the banner count, and `redone-block/`, whose `block 2 of 4` (void) against
`block 4 of 4` (intact) is the index's own claim that one value can be the value
under test of two blocks. **No description cell was edited and no fixture was
touched**, which is the outcome the measurement licenses and not a coincidence
worth much on its own — the index's sentences are true today.

Both closed lists are printed whole, **entries with no instance included**. That
is the half that matters: a list of only what a run reached cannot be told from
a shorter list, and the difference between "this shape has no instance in the
committed index" and "this shape does not exist" is the whole of what the lists
are for.

### The two figures on the second line are not one figure

The census prints the row count and the stripped-clause count beside each other
and they happen to agree here. **That is a coincidence of this tree and not a
property of the index**, so nothing in the tool reads them as one number.
Measured by `refusal_count()` over each description cell:

```
python3 - <<'EOF'
import importlib.util, sys; sys.path.insert(0, 'ec/tools')
spec = importlib.util.spec_from_file_location('m', 'ec/tools/check_testdata_grader_claims.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cells = m.table_cells(open('ec/tools/testdata/README.md', encoding='utf-8').read(), column=3)
per_row = [m.refusal_count(c) for c in cells]
print('rows carrying none:', [i + 1 for i, n in enumerate(per_row) if n == 0])
print('rows carrying more than one:', [(i + 1, n) for i, n in enumerate(per_row) if n > 1])
EOF
```

Most rows carry one refusal clause, **one row carries none and one carries two**,
so the "a rule that reached one of these clauses would turn the run red by
construction" argument holds for the rows that carry a clause and **not
row-wide** — for a row carrying none there is nothing for a rule to reach. Which
rows those are is a property of this tree and is recorded here rather than
asserted anywhere in the tool or its suite, both of which hold only the
properties that survive a reword: a clause that is there is never read, and a row
carrying none is not an error. The issue this answers said the clauses were
"present on all 27 rows"; that was the issue's own figure and it does not hold
for the tree as it stands.

## The decline list, one bullet per entry

Each opens with the string the tool's `DECLINES` gives it, so the two can be
joined by name rather than by a reader lining prose up against a constant. None
of them fails the run.

  * `another row's fixture` -- the clause a claim sits in names a fixture set
    this row does not. Row 30's `exits 0`, which is about
    `unplaced-window/`. Grading this row's set against it would check nothing.
  * `not this grader's row` -- the `Feeds` cell names another tool. The
    `gpu-door-*` and `sweep-summary-*` rows feed `grade_gpu_door.py` and
    `grade_sweep_summary.py`; one grader is this tool's scope, and the rest are
    named declines rather than silent skips.
  * `no capture in the row's file set` -- the first column resolves to no
    `.csv`. The `--dump-pair` rows are `ecrw.py dump` output, which is a pair of
    flags rather than a capture.
  * `withheld count not in whole-capture spelling` -- a withheld count stated
    against a `--block` run. That spelling carries three numbers and is a
    different question; no row claims against it.
  * `movement restatement` -- a claim about the movement line's own "That is
    the N window(s) that were graded", which row 24 writes as "one of the 6
    that were graded moved". No module constant identifies that line, so
    deciding it would mean re-deriving the grader's prose here. The `2 withheld
    of 8` in the same sentence is still read, which is why the phrase is its own
    claim rather than a clause rule that would take the other one with it.
  * `no closed shape` -- a count whose clause names neither counted line. This
    entry is what makes the list closed; without it such a count would be
    reported under a token name that is not a decline.

## What it does not check, which is as much of the point

  * **That a fixture is what its row says it is.** This compares the index's
    sentence to the grader's output. It does not ask whether the fixture
    constructs the shape described, and a green run is not a claim that it does.
    That line is `check_testdata_row_claims.py`'s own, drawn for addresses and
    drawn again here for the same reason: **this tool is one step further from
    the hardware still**, because the grader's output is itself a claim about a
    capture no live run has produced since the fixture was written.
  * **The mark set the fixture's own bytes hold.** Rows about two marks where
    the other two have three, a console's write mark spelled `0x10` where the
    other two say `0xA0`, and no restore mark in any capture are claims about
    `ec_watch.py`'s output rather than about the grader's report. They are
    decidable today through `grade.existing_mark_labels()`, and they are **not
    read here**: this tool drives one grader's *report*, and the mark-set
    questions are a different oracle over the same fixtures. The measurement
    calls them out because leaving them out is a choice and not an oversight —
    they are the remaining half of what #978 named, and a follow-up that reads
    them is a new file beside this one rather than a mode here.
  * **The `gpu-door-*` and `sweep-summary-*` rows.** A row fed to another
    grader is a named decline (`not this grader's row`), and the census prints
    the count.
  * **Row 18's timestamp-and-window claim** — the `0x0F0A` row *at* 12:00:08.500
    landing before the first mark of the set. `check_testdata_row_claims.py`'s
    docstring defers it by name as "a different invariant with a different
    owner", and re-deciding it here would give a question the sibling
    consciously left open a second owner.
  * **Whether a fixture demonstrates anything about the EC.** A grader run over
    a hand-written capture is a statement about the capture.

## The gate wiring is a fold, and why

The wiring is prepared in `docs/ci/agent-gates-testdata-row-claims.patch` rather
than in a file of its own. `tools/test_agent_gates_patches.py` applies the whole
set in every ordered pair, and **the seven-line `gate` list has no line left a
new hunk can be cut against**: `agent-gates-pin-table-rows.patch` holds the one
at the front, `agent-gates-capture-claims.patch` the one at `register counts`,
and the row-claims patch the one at the end. A separate file would apply cleanly
*alone* and fail in half the pairs — which is the failure that is silent in the
way that matters, because nothing reports a patch that was never tried.

The new function hunk is at `check_shellcheck()`, the one anchor in the script
no patch in the set writes into. `FoldTests` reads that file for both tools'
strings, so a re-cut that keeps one half and drops the other still applies,
still composes, and passes every other case in that suite.

**Until a human lands it, no commit runs this.** The suite needs no wiring to be
run at all: `tools/run-tests.sh` discovers every `test_*.py` in the repository.