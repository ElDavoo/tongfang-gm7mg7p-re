# Testdata reason literal source-code coverage

## The gap

`check_testdata_row_claims.py` maintains a closed list of reasons that allow a
literal to pass through the checker without raising it as a disagreement:
`SHAPES` (line 455–464). To catch a reason being added to the code without
being added to the list, there are three copies of the reason list:

1. `SHAPES` — the source of truth, a tuple constant
2. The module docstring's bullets (lines 93–152) — a prose copy
3. The `reason_for()` function (lines 675–718) and `no_column_reason()` (lines 842–863) — inline return statements as string literals

Issue #987 machine-verified that copies 1 and 2 stayed in sync; the new test
`test_reason_literals_match_shapes` (in `test_check_testdata_row_claims.py`)
now does the same for copy 3, extracting all string literals from the return
statements using AST parsing. The test catches either a reason added to the
functions without being added to `SHAPES`, or a reason removed from `SHAPES`
but left in the functions.

## Reasons exercised by committed data

The committed index has one dated sentence (row 7) that names one date, so it
exercises five distinct reasons:

- `capture/window bound` — 18 instances
- `denial` — 3 instances
- `dump-command argument` — 2 instances
- `watched-set span` — 2 instances
- `firmware code address` — 2 instances

This is verified by `test_the_committed_tree_exercises_every_shape`, which
reads the actual run over the committed index and asserts that the run
exercises exactly this set (no more, no less).

## Reasons only in scratch test data

The other three reasons have no instance in the committed index:

- `two dated captures in one sentence` — a sentence naming two distinct dates
- `dated capture not found` — a date whose glob pattern resolved to nothing
- `dated capture has no addr column` — a date resolving to files with no `addr` column

The committed index's own comment (lines 479–483) explains why: "the one dated
sentence in [the committed index] names one date and resolves to a set that
has the column -- so what pins them is scratch cases rather than the run." The
test suite exercises all three via scratch cases in the `SkipsDeliberately` and
`TheDatedClaimIsHeldToTheColumn` test classes, driving the actual `reason_for()`
and `no_column_reason()` calls with temporary fixtures.

## Why both levels of verification matter

**Source-code verification** (`test_reason_literals_match_shapes`):
- Checks all reasons independently of committed data
- Catches a new reason added to the function code without being added to `SHAPES`
- Catches the opposite direction: a reason removed from `SHAPES` but left in the code

**Runtime verification** (`test_the_committed_tree_exercises_every_shape`):
- Checks that the committed data exercises the expected subset
- Cannot see the dated refusals because they have no committed instances by design
- Would fail if a reason were removed from the code but left in `SHAPES`

They answer different questions and both are necessary. The source-code test is
what would have caught issues #983 and #1370 (which added two dated reasons
without being caught), and issues #979 and #990 (which motivated them). The
runtime test ensures the committed tree still exercises what the functions
are designed to skip.

## Related issues

- **#1457** — opened the gap; this work closes it
- **#987** — machine-verified the docstring against `SHAPES`
- **#983** (issue #979) — added `two dated captures in one sentence` without a committed instance
- **#1370** (issue #990) — added `dated capture has no addr column` without a committed instance
