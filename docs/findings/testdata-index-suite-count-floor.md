# The testdata-index suite asserted three integers the tree happens to hold today (issue #744)

The write-up for [issue
#744](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/744), which is about
`ec/tools/test_check_testdata_index.py` pinning the committed tree's three
tallies as an exact tuple. What this branch replaces is that tuple, and pins the
replacement from both sides.

**This supersedes the case count and the measured tallies in
[`testdata-index-check.md`](testdata-index-check.md)**, which recorded what
#727's branch did — "28 cases", `(13, 27, 34)`. That file is left as it was
written: a write-up is a record of what its branch measured, and the
supersession is stated here rather than by editing a sibling's page. The suite is
33 cases now. The tallies themselves have not moved; the *assertion* about them
has.

**Nothing here opens a capture, an EC, or a laptop.** The five new cases build a
`testdata/` under a `tempfile` out of hand-written strings, exactly like every
other case in this suite, and the committed case still opens two committed
files. No fixture is added and no claim is made that any fixture is correct.

## The measured defect

Three lines above the assertion, the comment said the opposite of it. At the
time of writing, `ec/tools/test_check_testdata_index.py:413-415`:

```python
        # A run that reports 0 directories and 0 rows is green for the wrong
        # reason, and the tallies are the only way to tell. This is not a floor
        # on coverage: nothing says the numbers have to stay where they are,
        # only that a run reaching nothing fails.
```

and `:420`, three lines below it:

```python
        self.assertEqual((directories, rows, tokens), (13, 27, 34))
```

**What that costs.** The event is a new fixture directory arriving. The correct
response to it — add `ec/tools/testdata/0751-isolation-run-<case>/` and a row
naming it — takes the counts to `(14, 28, 35)` and fails the one test whose name
says it is checking that the run *reached* something, as a bare
`AssertionError: (14, 28, 35) != (13, 27, 34)`. The failure is three hand-typed
integers, not the checker disagreeing with the tree:
`test_the_committed_index_and_tree_agree` stays green through it, because the
index and the tree *do* still agree. The suite's own module docstring (`:1-19`)
names the shape: a pointer-checker's failure mode is silence, and the only thing
that notices is a reader who has already been misled.

## Three places in this repository already said so

The rule the suite broke was written down three times before the suite broke it,
and in all three it is the same sentence about the same trade:

- **`ec/tools/check_testdata_index.py:77-82`**, the tool's own docstring:
  "Both tallies print whether or not they found anything, because a run that
  checked nothing and a run that found nothing look the same from the exit code
  alone. **There is no floor on either number**, for the reason
  `docs/agent-pipeline.md` records about gates: an expected count turns every
  added fixture into a failure. **The suite asserts non-emptiness instead**, which
  is the assertion that is true of the tree rather than of the tool."
- **The issue's own quotation of that paragraph**, which is where the
  contradiction was noticed.
- **`tools/run-tests.sh:77-79`**, declining the same trade about the runner's own
  counts: "The counts are printed, never asserted — an expected count in a
  runner turns every added test into a failure, which is the wrong trade. That is
  why the total below is there to be read off a run, and not a gate."
  `tools/README.md:12-17` says the same of its own two figures, and
  `tools/test_readme_suite_table.py` compares the suite table's *set* and never
  its counts, for the same reason.

**The tool file was not the thing that was wrong, and is not edited here.** Its
docstring already stated the rule correctly; the suite contradicted it. After
this change the sentence at `:77-82` is true rather than aspirational, and that is
the whole fix on that side — the file needs no edit to become accurate.

## The replacement, and why it is one method and not three assertions

`TheReachedSomethingRule` (`:396`) holds the rule,
`assert_the_run_reached_something(root)` (`:429`) states it, and
`run_tool(root)` (`:406`) runs the tool. The committed case at `:472` is now a
call:

```python
    def test_the_run_actually_reached_both_directions(self):
        # ... unchanged ...
        self.assert_the_run_reached_something(ctti.TESTDATA)
```

**The root is a parameter because the rule has to be pointable at a tree other
than the committed one to be a rule at all.** Three assertions pasted into the
committed case would assert the same thing; one method that another class also
calls is what lets a scratch tree be held to the identical clause, so a floor
reinstated in the helper fails the scratch cases and a clause dropped in the
helper fails the committed tree only when the committed tree is the wrong size to
notice. The two halves cannot now be edited without the other noticing.

`main()` reads the committed `TESTDATA` and `INDEX` as module globals and has no
flag pointing it anywhere else, so `run_tool(root)` (`:406`) patches both and puts
them back in the same `finally` that already restored `sys.argv`. `INDEX` is
patched as well as `TESTDATA` because `report()` prints `INDEX` on its summary
line: patching only the first would have a run over a `tempfile` report a
disagreement against the committed index.

**The tallies are still parsed out of what the run printed**, with the same three
splits, rather than read off a `Result`. That is not incidental: the docstring's
claim is that the tallies *print* whether or not they found anything, and parsing
the printed line is what tests that claim. A `Result` read directly would pin the
same arithmetic and none of the output.

**The replacement is not "any tree passes."** Three tallies non-zero is a floor at
zero, and it is still a floor: `(0, 0, 0)` is refused, which is the vacuous check
this suite's whole shape is about. `test_the_committed_index_and_tree_agree`
carries the correctness half untouched, and the four refusals below say exactly
what the rule still refuses.

## The five cases, and which clause each one pins

`TheTalliesAreNotAFloor` (`:521`) mixes in `ScratchIndex`, so each case reads as a
tree and an index beside it, and each calls the method the committed case calls.

| the case | the tree it builds | the clause it pins |
|---|---|---|
| `test_a_tree_carrying_more_of_them_than_today_is_green` | fourteen directories, one row, two tokens | the assertion reads **no size** — the event this issue is about |
| `test_a_tree_carrying_fewer_of_them_than_today_is_green` | one directory, one row, two tokens | the assertion reads **no minimum** — a removed directory and a dropped row are the same edit from the other end |
| `test_an_empty_tree_reaches_nothing` | `(0, 0, 0)` | `directories > 0` |
| `test_a_tree_with_a_directory_and_a_rowless_index_reaches_no_row` | a directory, a prose mention, a header and no row | `rows > 0`, and `tokens > 0` behind it |
| `test_one_token_per_row_is_refused` | a directory and a one-token row | `tokens > rows`, **alone** — every other clause passes |

**The first two are the direct pin, and the two-token cell in each is
load-bearing.** A one-token table leaves `tokens == rows`, the helper's
`tokens > rows` refuses it, and the case would be proving the wrong thing. The
first tree is bigger than the committed one on one tally and smaller on the other
two, which is the strongest form of the pin available: any assertion reading a
size, a minimum, or an exact set refuses it.

**The last one is the sharpest.** Every other clause passes — a directory is
reached, a row is read, `rc` is 0 — so `tokens > rows` is the only thing between
that tree and a green run. That is what stops the clause being dropped as
redundant on the strength of the committed tree happening to carry multi-path
cells today.

**The three refusals assert on the reason, not only that something raised**, in
the `with ... as caught:` shape `ec/tools/test_check_site_census.py:449` already
uses — `assertIn('directories', …)`, `assertIn('rows', …)`, `assertIn('only the
first is read', …)`. A case asserting only "it raised" would pass against a
helper that raised for the wrong reason, which is the whole subject of the page.

## `:206` is not contradicted, and a reader will check

`test_an_empty_tree_and_an_empty_index_are_green` (now `:216`) says a run over an
empty tree is green, and it still is. **That is a claim about the tool**: a
checker with no fixtures to look at has nothing to be wrong about, which is a
true and useful thing for it to say. The new rule is a property of *the suite's
assertion over the committed tree* — that the one test named for reaching
something is not satisfied by a run that reached nothing — and it is enforced by
`TheTalliesAreNotAFloor.test_an_empty_tree_reaches_nothing`, which is a
different subject pointed at a different root. The empty tree is green for the
tool and is refused by the rule; both are true, they are measured by different
methods, and neither was changed here.

## The mutation check, run and recorded

Three deliberate weakenings of the replacement, applied one at a time to
`test_check_testdata_index.py`, the whole suite re-run against each. **All three
are caught**, each by the case named:

| the weakening | the case that catches it | the run |
|---|---|---|
| the exact `(13, 27, 34)` tuple reinstated in the helper | `test_a_tree_carrying_more_of_them_than_today_is_green` — and the fewer case too, since a floor refuses both | 33 tests, 5 failures |
| the `> 0` clauses dropped | `test_an_empty_tree_reaches_nothing` and `test_a_tree_with_a_directory_and_a_rowless_index_reaches_no_row` | 33 tests, 2 failures |
| `tokens > rows` dropped | `test_one_token_per_row_is_refused` | 33 tests, 1 failure |

A suite that does not fail when the rule it pins is removed is the same defect in
the test as a check that does not fail when the tree drifts, which is the shape
`docs/findings/testdata-index-check.md` records for #727's seven loosenings of
the tool. This is the same check one level up.

## The issue's Done criterion, taken literally

> green on a tree carrying one more fixture directory than `main` does, with no
> integer in the source that has to be edited to get there

Taken on a throwaway copy of `ec/tools/`: a real
`testdata/0751-isolation-run-staged-copy/` with a file in it, and a real table
row naming it added to a copy of `ec/tools/testdata/README.md`. **Not committed**,
and nothing about the fixture's content is claimed — it exists only to move a
count.

```
$ python3 check_testdata_index.py --check
14 testdata/ directories: 13 named in the index, 1 self-indexed, 0 gap(s)
28 table row(s), 35 path token(s): 35 resolved, 0 missing, 0 unresolved

$ python3 -m unittest test_check_testdata_index
Ran 33 tests in 0.033s

OK
```

`(14, 28, 35)` is the exact tuple the issue predicted would fail. It does not,
and **no integer in any source was edited to get there** — the suite goes from 28
cases to 33 and `tools/run-tests.sh`'s total from 679 to 684, both figures printed
and never asserted, which is `tools/README.md:12-17`'s rule applied one file over.

**A fourteenth fixture directory is left out on purpose.** Every directory under
`ec/tools/testdata/` today exists to construct one named grader case, and
`ec/tools/testdata/README.md` requires each row to say which. Inventing a fixture
to move a count would open a new question — a directory constructing no case —
rather than close this one. The event is prospective, and the scratch tree the
committed cases build is the form the issue's own "pin it the way the rest of the
suite is pinned" asks for.

## Nothing in another repository

No upstream patch is part of this work, and none is planned. The gate arm stays
prepared at `docs/ci/agent-gates-testdata-index.patch` for a human to `git apply`,
which is what that file's own header says and what `docs/agent-pipeline.md`
carries; this change does not touch it and the patch still applies unchanged.
