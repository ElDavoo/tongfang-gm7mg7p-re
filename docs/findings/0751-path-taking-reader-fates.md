# The two path-taking readers are kept, and their docstrings name their callers (issue #771)

The write-up for [issue
#771](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/771), which asks
for the fates of `refused_capture_rows` and `existing_mark_labels` to be
decided deliberately rather than settled by drift — and reports that
`refused_capture_rows`'s docstring, rewritten in #749, asserts a caller that
does not exist. **Both functions are kept.** What changed is that each
docstring now names the callers and dependants that are actually there, and
the hypothetical is gone rather than warmed over.

This is a change to what the tool's *prose* claims, not to what it can read.
No reader's verdict moved, no row's shape changed, and no executable line was
touched — four docstrings in `grade_0751_isolation.py` and one comment in its
suite, and nothing else in either file. The evidence is a search of this tree
and a suite at an unchanged count. No EC was opened, no capture was taken, no
register was read back and no hardware was involved anywhere below.

**No line numbers are restated here.** The symbols this page is about sit in
`grade_0751_isolation.py` at the positions tabulated in
[`0751-notice-two-moments.md`](0751-notice-two-moments.md) and, for the
read/write split, in
[`0751-capture-encoding.md`](0751-capture-encoding.md). A third table here
would be a third thing to re-anchor, and the first two have each needed it
already; the write-up points at them instead. Test cases are named by name
rather than by line, so that adding a case above one does not rot this page.

*(One exception, and it is forced rather than chosen, so it is recorded here
rather than left to look like an oversight. The sixteen `test_*.py:NNN` lines
the two transcripts below print are **also** cited in live prose further down,
which is the one thing this rule would otherwise forbid. The reason is
`census_test_line_pins.py`'s fence rule: a pin that appears *only* inside a
fenced block is `declined`, and
`test_every_declined_pin_is_also_cited_in_live_prose` requires every declined
pin to have a live-prose twin, because declining the tree's only citation of a
line is a quiet loss rather than a declined duplicate. This page's transcripts
were the sole citation of all sixteen, so all sixteen reddened that test, and
the choice was between citing them in prose and weakening the rule. The prose
is sixteen lines that can rot; the rule is what keeps a transcript from quietly
becoming the only record of a line. Rule kept. It also means the exception is
narrow on purpose — it covers the *test-file* lines the transcripts print, and
not one `grade_0751_isolation.py` line, which is what the rule above governs.
The two sides of that split are the tool's own: it censuses `test_*.py:NNN`
pins and nothing else.)*

---

## The reach, as the code stood

The issue's central claim is that `refused_capture_rows` has *"no caller, in
production or in the suite."* Re-measured on this tree:

```console
$ grep -rn "refused_capture_rows" --include=*.py .
./ec/tools/grade_0751_isolation.py:754:    `existing_mark_labels`, `refused_capture_rows` and `read_early_exits`.
./ec/tools/grade_0751_isolation.py:828:    `read_capture`, `existing_mark_labels` and `refused_capture_rows` -- the
./ec/tools/grade_0751_isolation.py:841:    `refused_capture_rows` -- and merging them would delete the preflight
./ec/tools/grade_0751_isolation.py:957:def refused_capture_rows(path):
./ec/tools/test_grade_0751_isolation.py:3736:            accepted, refused = grade.refused_capture_rows(path)
./ec/tools/test_grade_0751_isolation.py:3795:            accepted, refused = grade.refused_capture_rows(path)
./ec/tools/test_grade_0751_isolation.py:3916:        # `refused_capture_rows` directly, and checks the reason on the row
./ec/tools/test_grade_0751_isolation.py:3926:            accepted, refused = grade.refused_capture_rows(path)
```

The definition, three comments that name it as one of the readers — which the
decision below leaves true — and **three call sites**, all in
`ec/tools/test_grade_0751_isolation.py`. So the function is not dead code, and
the issue's "delete it or name the caller" is not a choice between a corpse
and a rescue. It is a choice between a function with three named test callers
and one with a hypothetical caller in its docstring. The three cases:

| case | how it reaches it |
|---|---|
| `test_the_shape_agrees_across_all_four_readers` | partitions a fixture carrying all three skip cases at once, against the other three readers |
| `test_on_a_file_the_strict_reader_refuses_the_partition_names_every_row` | partitions beside `existing_mark_labels` over the same path |
| `test_a_change_row_bad_in_two_hex_fields_names_the_earlier_one` | partitions **directly**, and its own comment says why |

Those three cases are the three call lines the transcript above prints:
`ec/tools/test_grade_0751_isolation.py:3736`,
`ec/tools/test_grade_0751_isolation.py:3795` and
`ec/tools/test_grade_0751_isolation.py:3926`, in the order the table gives
them. The comment that credits the last with reaching the function *directly*
rather than through the wrapper is the fourth of that transcript's lines,
`ec/tools/test_grade_0751_isolation.py:3916`, and it is the only one of the
four that is prose in the suite rather than a call. That last one is the
load-bearing case and the reason the function earns its place. `existing_mark_findings` pastes `read_capture`'s own exception over the
*first* reason, so no fixture whose only bad row is the first one can show
which check ran first. The order of the checks is therefore only observable
through a path-taking entry that does not paste that exception — which is a
property `existing_mark_findings` has and `refused_capture_rows` does not. That
is a role, not a convenience.

`existing_mark_labels` is a different shape of question. The issue asks whether
it is an API or a test fixture. Every executable reference to it is:

```console
$ grep -rn "\.existing_mark_labels" --include=*.py .
./windows/tools/test_ec_watch.py:1134:                             grader.existing_mark_labels(str(out)))
./windows/tools/ec_watch.py:275:                     grader.existing_mark_labels,
./ec/tools/test_grade_0751_isolation.py:3500:            self.assertEqual(grade.existing_mark_labels(path),
./ec/tools/test_grade_0751_isolation.py:3520:            self.assertEqual(grade.existing_mark_labels(path),
./ec/tools/test_grade_0751_isolation.py:3551:            marks = grade.existing_mark_labels(str(path))
./ec/tools/test_grade_0751_isolation.py:3580:            self.assertEqual(len(grade.existing_mark_labels(path)), 7)
./ec/tools/test_grade_0751_isolation.py:3735:            labels = grade.existing_mark_labels(path)
./ec/tools/test_grade_0751_isolation.py:3796:            labels = grade.existing_mark_labels(path)
./ec/tools/test_grade_0751_isolation.py:3858:            lenient = grade.existing_mark_labels(str(path))
./ec/tools/test_grade_0751_isolation.py:4049:                    self.assertIsInstance(grade.existing_mark_labels(path), list)
./ec/tools/test_grade_0751_isolation.py:4057:            self.assertEqual(len(grade.existing_mark_labels(str(path))), 1)
./ec/tools/test_grade_0751_isolation.py:4166:            lenient = grade.existing_mark_labels(path)
./ec/tools/test_grade_0751_isolation.py:4356:                    self.assertEqual(grade.existing_mark_labels(path), [])
./ec/tools/measure_mark_provenance.py:430:            ("existing_mark_labels", GRADER, grader.existing_mark_labels,
./ec/tools/measure_mark_provenance.py:717:        base = grader.existing_mark_labels(os.path.join(tmp, "0751-none.csv"))
./ec/tools/measure_mark_provenance.py:719:            got = grader.existing_mark_labels(
./ec/tools/measure_mark_provenance.py:730:        if grader.existing_mark_labels(empty) != [
```

Eleven of those are the grader's own suite, which is not what the question is
about — `ec/tools/test_grade_0751_isolation.py:3500`,
`ec/tools/test_grade_0751_isolation.py:3520`,
`ec/tools/test_grade_0751_isolation.py:3551`,
`ec/tools/test_grade_0751_isolation.py:3580`,
`ec/tools/test_grade_0751_isolation.py:3735`,
`ec/tools/test_grade_0751_isolation.py:3796`,
`ec/tools/test_grade_0751_isolation.py:3858`,
`ec/tools/test_grade_0751_isolation.py:4049`,
`ec/tools/test_grade_0751_isolation.py:4057`,
`ec/tools/test_grade_0751_isolation.py:4166` and
`ec/tools/test_grade_0751_isolation.py:4356`. The other **four** are three
files that do not belong to it, and they are why the answer is API rather than
fixture:

`measure_mark_provenance.py` registers it in its `families` oracle table,
which `main()` consumes on every census run and not only under
`--self-test`; that is a committed tool whose output is a return-value
comparison against this function. `ec_watch.py`'s `load_label_vocab` reads its
**name** into a liveness probe, so a staged grader copy that predates the
attribute is refused by a message naming the path, and `test_ec_watch.py`
asserts what the staged copy returns against the committed one, at
`windows/tools/test_ec_watch.py:1134`.
`windows/tools/ec_watch-marks.md` documents it as *"The reader"* and describes
its extraction as a helper `existing_mark_findings` shares.

## The two decisions, and why

**`refused_capture_rows` — kept, and the three cases named.** The docstring's
last paragraph was the actual defect: *"kept for a caller that holds a path
rather than rows"* names no one. It now names the three cases above, and then
states the bound plainly: **no program in the tree calls it**, and that is what
a search of this tree finds rather than a claim that none ever will. That is
the calibration rule applied to itself, and it is the sentence the issue was
right about.

**`existing_mark_labels` — kept, and declared a published API.** The docstring
gains a short paragraph naming those three dependants, so it no longer reads
as though the only thing waiting on it is a test.

**Two cross-references moved with them, and only two.** The rule applied to
every cross-reference, so that the ones which are already right are not
churned: *a cross-reference names the function whose body makes the claim, not
the wrapper it used to live in.* `capture_rows`'s list of the four readers and
`skippable_row`'s account of the three that agree on it are **already correct**
and were left alone — those name the *path a reader takes*, and this change
does not move the path. Two describe where a body now lives and so did move:
`take_capture_row`'s docstring said `refused_capture_rows` spells the
`Change(...)` argument order again, and that body is `partition_capture_rows`'
— the wrapper delegates into it and cannot be the source of a claim about it.
The same circularity was in `partition_capture_rows`, which credited the
lenient read to the delegate into itself; it now credits
`existing_mark_labels`'s own argument and the two-in-one decision
`capture_rows` states. The test comment on the anti-drift guard moved with
them for the same reason: it credited `refused_capture_rows` with conditions
the case reaches through `existing_mark_findings`, so it now names
`partition_capture_rows` and the wrapper it arrives by. **The test body is
untouched** — #749 left that guard green deliberately and it is the thing
holding `partition_capture_rows` to `take_capture_row`; rerouting it through
the wrapper would destroy the one property that makes it worth having.

## The rejected alternative, and what it would have cost

The issue lists deleting `refused_capture_rows` first, and on this tree that is
the more expensive option for less return. `0751-capture-encoding.md` §2 is
titled **"The sites, all thirteen"** and carries a row naming
`grade_0751_isolation.py refused_capture_rows`, its `errors=` value and its
line. Deleting the function leaves that row dangling *and* the section's own
count wrong — a retraction in place, in a shared findings file, per CLAUDE.md
§4a-4d, for a function whose three callers are real and one of which is
load-bearing. Five pages under `docs/findings/` name the function, and
`docs/findings.md` names it too; under the keep decision all six stay true, so
the keep costs zero shared-doc retractions.

Reversing this decision is a separate change and would carry the
`0751-capture-encoding.md` §2 retraction with it. That is why it is written
down here rather than settled silently.

## Two anchors that were already rotten

The issue also asks for three stale names in the test file to be fixed. One was
a comment this change retargets, above. The other two are **not recoverable**,
and the calibration rule says record that rather than reconstruct:

- the `:690` the issue names, which it says `:627` and `:3636` tighten, **is
  not on this tree at all** — `test_grade_0751_isolation.py` carries no `:690`
  reference anywhere, so there is no line to retarget and no way to tell
  whether whatever replaced it is still the symbol meant;
- the region the issue points at already names `existing_mark_findings`, which
  is what it does.

A comment whose subject is gone is not a comment to re-invent. They are
recorded as checked and found rotten, not quietly dropped.

## What this cost: the citation table moved

One consequence the issue could not have predicted, recorded here because it
is the part a later reader will meet first. `measure_mark_provenance.py` pins
exact line numbers into `grade_0751_isolation.py`, and this change is prose
*in that file* — so growing four docstrings moved twelve pins, and the full
census went from 44 `ok` rows and exit 0 to 20 problems and exit 1.

That is the tool working as designed, not a regression: its own comment says a
line that moves is a mismatch *"whether it moved because the file grew above it
or because the claim was wrong, and the two need a reader, not a guess."* Here
the cause is known and was not a wrong claim, so the pins were re-measured
rather than the table relaxed. The page
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) names every
citation and `check_page` holds it to that, so its numbers moved with them,
and so did the drift tables in `0751-notice-two-moments.md`,
`0751-capture-encoding.md` and `0751-capture-row-shape.md`, and the two
figures `docs/findings.md` quotes from them. **The reader set did not move**:
7 writers, 8 sites, 6 reader calls and 48 in-suite calls, the same as before,
and the tool exits 0 again.

## What proves it

`bash tools/run-tests.sh` and `python3 ec/tools/measure_mark_provenance.py` —
the last of which is the check that actually moves when this kind of change
moves something, and which `agent-gates.sh` does not run. All seven gates pass.

The suite is **35 suites, 1076 tests, on both this tree and a clean worktree at
`HEAD`**, with the same single failure in both:
`test_check_cluster_citations.py`'s
`test_committed_prose_matches_committed_census`, on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220`. That is **#822's**
write-up — `docs/findings.md` §6a records it as reproducing on a clean
`origin/main` — and this change touches nothing it reads;
`test_grade_0751_isolation.py` is 111 tests, passed, on both trees.

> **Correction, 2026-09-26, at the merge: "the same single failure in both" was
> wrong, and the suite was not green on this page's own tree.** There was a
> second failing suite here and the page did not record it:
> `ec/tools/test_census_test_line_pins.py`, **17 failures**, every one of them
> the fence rule above — the sixteen transcript-only pins, plus this page's own
> count pin. It reproduces identically on a clean worktree at this branch's tip
> and is **not** a merge artefact: `origin/main` alone is 41 tests, **OK**, and
> so is this page's tree with the sixteen prose citations added. The two
> assertions above are left as written and the correction put beside them rather
> than into them, per §4a-4d. What went wrong is worth naming, because it is the
> failure mode this repository keeps recording: the figure *"35 suites, 1076
> tests, the same single failure in both"* was a measurement reported as taken,
> and the suite it was measured on says otherwise. Nothing about the *decision*
> this page records moves — both functions are still kept, the three call sites
> are still the three the table names, and `measure_mark_provenance.py` still
> exits 0 on 44 `ok` rows. What was red was this page's own housekeeping.

*(The plan this page was written against recorded **two** pre-existing
failures, the second being `test_walk_budget_census.py` on a baseline ref
`e198fd9` this squashed checkout does not carry. Measured on this checkout
that suite is 52 tests, **passed**, on the clean tree as well as this one — so
the second failure is not reproducible here and one is. Recorded per §4a-4d
rather than quietly dropped: the claim was reasonable and the tree it was taken
on is not this one.)*

**And the count the fence rule forced is recorded where the tool keeps it.**
`ec/tools/test_census_test_line_pins.py` pins this census's totals, and the
sixteen prose citations move every one of them: occurrences 73 → 105, `resolves`
57 → 73, `declined` 16 → 32, targets 42 → 58, files 26 → 27, and `spellings`
46 → 78 — by 32 and not 16, because `spellings` counts the *matched* spelling
and `grep -rn` prints a `./` prefix that prose does not, so each of the sixteen
is two spellings of one pin. That test's own comment carries the derivation and
names which change moved each figure. There were **three** places that needed it
and this page said two, which was the count of the two it knew about: the tool's
`ec/tools/test_census_test_line_pins.py` is the first, this page is the second,
and the third is [`test-line-pin-census.md`](test-line-pin-census.md) — the page
that *publishes* this census's figures, so a correction paragraph beside its
transcript, its verdict table, its shape split and its 32 new per-pin rows went
in with it. None of the three numbers is derived here.

Nothing in this change needs hardware. The whole of it is offline behaviour of
a text search, a line-number census and a test suite.
