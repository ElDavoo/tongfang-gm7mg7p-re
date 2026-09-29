# The closing line named the committed index for a run that read a scratch one, and the argument that excused it was a caller count (issue #1022)

The write-up for [issue
#1022](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1022), which
is about `ec/tools/check_testdata_row_claims.py` naming a file it did not
read. #974 put the capture root on `Result` because `dated_report()` printed
`repo_path(CAPTURES)`, the module constant, while `check()` takes
`captures=` as a parameter; the closing line kept the same asymmetry one root
over and labelled the index with `repo_path(INDEX)`. This branch carries the
index root the same way #974 carried the capture root, and corrects the
docstring paragraph that argued the asymmetry away.

**Nothing here is a live test.** No capture is opened, no EC is read, no
laptop is involved. The CSVs and `.txt` files under `evidence/ec-watch/` are
read as text, exactly as `carried_by()` reads a fixture, and the only claim
is about which path a report line prints. This is the same class of claim as
[`testdata-row-claims-report-naming.md`](testdata-row-claims-report-naming.md),
whose §(b) is the capture-root half of this one.

## The defect, reproduced on this tree

`closing_line()` ended its f-string with `repo_path(INDEX)` where `INDEX` is
`check_testdata_index.py`'s module constant — the committed
`ec/tools/testdata/README.md` — while `check()` takes `root=` as a parameter
(`check_testdata_row_claims.py:794`) and passes it to `row_files()` and to
`files_for()`. `Result` carried `captures` and not `root`
(`:400`), so nothing on the object held the tree the run had actually read.

Pointing the check at a scratch tree printed the committed path for it:

```
$ python3 -c '...; r = ctrc.check(root="/tmp/repro/testdata", captures="/tmp/repro/ec-watch"); print(ctrc.closing_line(r))'
ec/tools/testdata/README.md: every address claim in the third column agrees with the files it was held to -- 0 with the fixtures their row names, 0 with the captures a bare date in their sentence names
```

`main()`'s output is **unchanged and was measured, not asserted**: the tool's
full stdout and stderr were captured before the edit and after it and diffed,
and the diff is empty. That is not a coincidence to be proud of — it is the
whole of what is claimed about shipped output. `main()` passes the default root
every time, and the default root is the committed one, so the label it prints
is the same string before and after.

The suite, on the other hand, points `check()` at a scratch root on every
case (`ScratchIndex.check()` hands in `self.testdata`), so the committed
label is what a scratch-root run used to print too. The sentence at the head
of the closing line was therefore wrong for exactly the runs the suite makes
and right for the one it does not, which is the worst of both: a defect no
green run can show and no reader of the output can see.

## What the fix is, and what it is not

`Result` gains `root` as its **last** field, after `captures`
(`check_testdata_row_claims.py:400`), and `check()` passes the `root` it was
handed (`:883`). `closing_line()` builds the label from it (`:1080`). The file
name itself is now the module constant `INDEX_NAME` (`:282`) rather than a
second literal in `check()` and a third in the f-string, so the reader that
opens the index and the reader that names it build the same path from one
spelling.

Appending rather than inserting is #974's shape and the safe direction: the
fields are a `collections.namedtuple` with no defaults, so a construction that
has not learned the new field raises on the arity instead of quietly reading a
path that was never there.

The label is still rendered through `repo_path()`, so a scratch root comes out
as a chain of `..` out of the repository — `../../../../../tmp/tmpXXXX/testdata/README.md`
— rather than as an absolute path. That is `repo_path()`'s existing and
documented behaviour, and `dated_report()` has been doing it for a scratch
capture root since #974; the committed run is unchanged because the committed
root is inside the repository. It is worth saying plainly because a reader who
meets the new scratch output for the first time will read the `..` chain as a
second defect, and it is not one.

## What the retracted paragraph actually claimed

`closing_line()`'s docstring argued the asymmetry away rather than leaving it
alone:

> `main()` still labels the index with `repo_path(INDEX)`, which is the same
> class of constant, and that is left alone on purpose: it is the only caller
> of `check()` and it always passes the default root, so no run that prints
> this line ever searched another tree.

The conclusion was true — nothing else renders the line — and the premise was
false. `measure_index_repair_visibility.measure()` calls
`ctrc.check(root=root)` in-process against whatever tree it is handed
(`ec/tools/measure_index_repair_visibility.py:302`), and that tool's own
docstring says the in-process call is the *only* way to point either check at a
tree. So the sentence's own conclusion and its own stated reason for it cannot
both be right: if there is a second caller that takes a root, there is a run
that searched another tree, whatever renders this line.

Per `docs/findings.md` §4a the wrong sentence stays visible in the docstring
with the correction beside it, in the `~~…~~ **…**` shape `carried_by()`'s
docstring already uses in the same file. **The replacement does not restate the
argument with a better one** — it drops the caller count and says what the
label now names: the file `check()` read, whatever the caller. A claim about
who calls a function is a static property of a tree, and this tree is exactly
where that kind of claim has already gone wrong twice, from the other side.

## What holds it

Two cases, and they are complements rather than duplicates.

**A scratch-root run's closing line names the scratch index** and does not
contain the committed one. It sits directly beside the case from #974 that
holds the same property for the capture root, so the two "this surface names
the root the run was handed" cases read together. Under the pre-fix label this
case is red: the mutation is to build the path from the committed root rather
than `result.root`, and the committed label then appears where the scratch one
belongs.

**The committed run's closing line still starts with the committed index**,
and the `Result` it came from names the committed root. That is the assertion
that the change moved no output, and it is a relation between two values the
code derives — a label and a path — rather than a count of the tree, so a row
added to the index next month does not redden it.

Neither case pins a number. The suite's existing case that the two readings of
the committed tree cannot be told apart compares the text before `"-- "` across
two runs, so it fails if the label moves either way; and the case that the two
per-set counts sum to `checked` reads the counts half only, so it is untouched.

## What is left open

- **`closing_line()`'s docstring is now the only prose in this file that was a
  caller count**, and it is corrected in place rather than deleted so a reader
  can see what changed. `measure_index_repair_visibility.measure()` is a second
  in-process caller of `check()` that no docstring names, which is the
  strongest argument anyone has for the field this branch adds.
- **A root per field is how this class of bug recurs.** `Result` now carries
  two roots, and both exist because two parameters exist. If a third
  root-shaped parameter ever appears, the shape to reach for is a small
  `RunPaths` namedtuple rather than a fourteenth positional field — and
  `measure_index_repair_visibility.Measure`, which builds its own record from a
  `Result` attribute by attribute, is the reader that would have to change.
- **Not claimed: that the second caller is affected today.**
  `measure_index_repair_visibility` calls `check()` and does not call
  `closing_line()`, so nothing it prints is wrong today. What is claimed is
  that the docstring's reason for leaving the label alone does not hold, and
  that the day a second caller renders the line over a scratch tree, the field
  is already there and a case already holds it.
