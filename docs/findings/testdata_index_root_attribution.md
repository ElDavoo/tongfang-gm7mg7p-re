# Testdata Index Root Attribution in check_testdata_index.py

## The defect

`check_testdata_index.py` has an internal inconsistency in how it attributes disagreements to the index being checked:

- Every individual disagreement finding (missing files, unresolved tokens, feeds misses) correctly names the tree they were found under, reading `root` from the parameter passed to `check()` at line 681
- The summary line at line 846, however, hardcodes the module constant `repo_path(INDEX)`, which always names the committed index regardless of which tree was actually checked

When `report()` is called with findings from a scratch tree, the individual lines say "disagreement in `testdata/README.md` under the scratch tree" while the summary line says "disagreement(s) between the committed testdata/README.md and the tree under it" — a contradiction.

**Why it matters.** `check_testdata_index.py` is the gate for `ec/tools/testdata/README.md` — the table mapping every EC evidence fixture to the tool that produces it. A summary line that names a file the run did not read is a sentence with no citation in the one place the repository states how many disagreements the index and the tree have.

## Not wrong today

`measure_index_repair_visibility.measure()` calls `check(root)` against an extracted scratch tree and does **not** call `report()`, so nothing this tool prints has been wrong in practice. The defect is latent: all printed output has been correct even though the `report()` function's internal state contradicts its inputs.

## The fix

Carry `root` through the `Result` namedtuple the way #1022 did for the sibling tool (`ec/tools/check_row_claims.py`):

1. Add `root` field to `Result` at line 245, appended last with no default — a construction that hasn't learned the parameter raises on arity
2. Pass `root` when constructing `Result` in `check()` at line 764
3. Update `report()` to accept `root` as an eighth positional parameter at line 798
4. Build the summary line label from `os.path.join(root, "README.md")` instead of the constant `INDEX` at line 846
5. Add a test case verifying `report()` correctly attributes results to a scratch root, not the committed index

## Before and after

Before the fix, a run over a scratch tree would print:
```
testdata/some-fixture/: no index names it, and it has no README.md of its own
1 disagreement(s) between ec/tools/testdata/README.md and the tree under it
```

After the fix, the summary line is built from the actual `root` and says:
```
testdata/some-fixture/: no index names it, and it has no README.md of its own
1 disagreement(s) between /tmp/scratch-abc123/testdata/README.md and the tree under it
```

## Test workaround

The test file at line 84-90 documents a workaround where `run_tool()` patches `ctti.TESTDATA`, `ctti.INDEX`, and `ctti.REPO` on every scratch case. The workaround is orthogonal to this fix: the patching ensures the committed constants point to scratch paths, and the `Result.root` field ensures the function receives the actual path it checked. The workaround continues to work after this fix and can be simplified if desired, though it remains necessary for any path the tool imports at module level.
