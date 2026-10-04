# The merged timer-sweep run took its sample interval and its byte levels from one file each, and now refuses a merge whose files disagree (issue #1377)

The write-up for [issue
#1377](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1377), which was
opened by the follow-ups pass out of #1307. It sits beside
[`grader-repeated-capture.md`](grader-repeated-capture.md), which is the same
tool and the same `load()` merge: that one closed a *repeat* (the same file
twice) and deliberately kept several distinct captures as a sanctioned command
line. This one is about what that sanctioned merge then did to three figures.

**Offline throughout.** No EC image is opened beyond the suite's existing
re-read of the `0x8001` bytes, no register is read back, no capture is real and
no laptop, Windows box or suspend was involved. Every capture below is
constructed in a `tempfile` directory by
`ec/tools/test_grade_timer_sweep.py`, carries the `2026-01-01` placeholder date
`testdata/README.md` reserves for constructed input, and says so in its first
line. Nothing here re-verifies §3's 39-countdown count, the published 0.997 s
period, or any per-byte level in
`ec/annotations/xdata-06c2-06db-timers.md`; those are the claims a merged
report is *measured against*, and a change to how the report reads two headers
cannot move them.

## What the three figures fed, and what each one cost

Established by reading `load()` and `grade()`, and confirmed by the new cases
rather than by a run against a capture.

**`interval` reached a verdict, not just a description.** It appears in the
header line, and it is what `grade()`'s resolution check is judged against:
`step < 3 * interval` prints "the step is not resolved". The median step it is
compared with is a median over **every row of every file merged**. So a run
built from two captures taken at different `--interval` values did not merely
mislabel a number — it applied one file's sampling rate to a step interval
drawn from all of them. Nothing in the format forces two captures to agree:
`ec/tools/ec_timer_capture.py` takes `--interval` per invocation, and
`docs/hardware-tests/xdata-06c2-06db-sweep.md` §2 runs the writer at `0.01`,
`0.0005` and `0.002` across its arms.

Before this change `load()` assigned the interval with an unconditional
`interval = float(...)` inside the per-file loop, so the run reported whichever
file was named last. That is last-file-wins: the figure was never
disagreement-aware, only order-dependent, and a reader had no way to tell.

**`baseline` reached every per-address line.** `load()` collected it with
`baseline.setdefault(...)`, so where two captures each carried a `# baseline`
line for the same address the second was dropped in silence, and the report
then said "held at" or "`0xNN` ->" using the *first* file's level, over a span
that includes the second file's rows. That is the "level in evidence versus
level known" gap `grader-repeated-capture.md` records as the door grader's
failure mode, in a report that did not draw it: a byte that moved across a
seam between two captures would be graded at the level it held before it.
The `0x06C5` case in §4b of the sweep procedure — a byte that went into S3 at
`0x00` and came out at `0x05` — is the shape that would need this, and the
§4b capture is a *single* file, so the behaviour it recorded is not affected by
anything here.

**`span` was a union, and the union is not the defect.** `first` and `last` are
min/max'd across files, so the merged row set genuinely has no samples outside
the reported window, and "held over 25.0 s — not reached on the paths watched"
stays **true as a claim about what was not observed**. Only the description was
wrong: the line read as a measurement when it is a window built out of the
files given rather than one any of them watched on its own.

`watched` and the row merge were already honest unions with dedup, so there is
no fourth figure here and the issue's list of three is complete.

## One note from reading `load()` that belongs in the file

The span's endpoints are not taken from rows alone. `first` is min'd over the
`# baseline` comment timestamps *and* the first row, and `last` is max'd over
the `# ended` comment timestamps *and* the last row. So a merged span can
exceed the first-to-last row, and its two ends can come from two different
files — the first end from one file's baseline comment and the last from
another file's `# ended`. That is why the single-capture header in the suite's
byte-identical case reads `span 1.100s` for ten rows ending at 0.95 s: the
`# ended` line is 1.1 s. It is existing behaviour and is not changed here; it
is recorded because "the span is the union of the captures" is a statement
about a construction, and this is the construction.

## The decision: two refusals and one label

**Refused — `interval`.** Over reconciliation, for two reasons, both
calibration rather than taste. There is no evidence-backed rule for which
interval to print when two captures disagree; printing one silently is the
defect, and printing a composite invents a claim the capture does not make.
And the refusal hands the decision back to a person: "these two captures
disagree about the sample interval; here are both values and both files" is
something an operator at the machine can act on, and this pipeline cannot.

**Refused — `baseline`.** The same two reasons, and one more. A level is not an
average, so there is no composite to reach for; and a merged run has to say one
level per address, so the only alternatives are picking one file's level and
saying nothing, or tracking levels per address across the seam and changing
the shape of every line in the report. The second is a real piece of work, is
the issue's own other option, and is recorded below as the next decision
rather than smuggled in here.

**What reaches each of them — the shape is not only a merge.** Both refusals are
one sentence, and `load()` reaches it for a disagreement between two files
*or* for one file that states the figure twice in its own header. The second
case is described under "Two shapes reach that sentence" below; what matters
here is that the reasons above are about the *figure*, not about there being a
merge, so the same sentence covers both: an interval and a level are figures a
run can take from one place only, whichever that place is.

**Labelled — `span`.** No refusal, because the union is a legitimate merged run
and #491 kept the merged run deliberately; refusing it would be a contract
change to a documented use rather than a fix. The wording changes instead, and
only when `len(paths) > 1`, so a single-capture report is byte for byte the one
this grader printed before. What the accepted merge's header now says:

```console
$ python3 ec/tools/grade_timer_sweep.py part0.csv part1.csv
capture: part0.csv, part1.csv
span 25.000s (the union of the 2 captures given, which none of them covers), 140 change rows, sample interval 0.01s (stated by 2 of 2 files), 2 addresses watched
```

`span 25.000s` itself is untouched, so
`test_two_distinct_captures_are_still_one_run` — #491's pin that the
legitimate two-file run is still accepted — still holds, and the new case
`test_an_accepted_merged_run_says_where_its_figures_came_from` holds the same
three numbers plus the two clauses.

**The half about the files is conditional, and has to be.** The example above
is a pair either side of a suspend: 0.05–5.0 s and 20.05–25.0 s, each with its
`# baseline` at its own t0 the way `ec_timer_capture.py:314` stamps it. Fifteen
seconds of the merged window is a stretch neither file watched, so
`which none of them covers` is true of them. It is not true of every merge, and
printing it unconditionally made the tool assert something its own construction
contradicts: two files can *nest*, one taken wholly inside the other's window,
and then the outer file does watch the whole span on its own. A 0–30 s capture
merged with a 10–20 s capture of the same sweep — same intervals, same levels,
so it is an accepted merge — printed `span 30.000s (the union of the 2 captures
given, which none of them covers)` while the 0–30 s file covers every second of
it. `span_clause` therefore prints the clause only when `WINDOWS` says no file's
own `[first, last]` is the merged pair, and the union half either way, and
`test_a_merged_run_says_which_none_covers_only_when_none_does` holds both
directions. The union claim does not need the conditional half: it holds
because the merged row set has no samples outside the window, which is an
absence-of-observation claim and is true whatever the files' relative windows
are.

## The refusal, and why the order is pinned

`merged_capture_refusal` (`:142`) is the one sentence, built once and quoted by
both callers, for `bom_refusal`'s reason: `load()` raises it and `main()`
prints it, and a warning an operator reads and an error the grading raises
have to be one verdict rather than two that can drift apart. It returns `None`
when the merge is clean, which is what makes "agrees" and "states nothing" the
same case rather than two.

It is **not** hoisted into `grade_0751_isolation.py` beside `bom_refusal`,
though the shape is borrowed from there. No sibling grader reads either
header: neither `grade_gpu_door.py` nor `grade_0751_isolation.py` parses
`# interval` or `# baseline`, so there is no second caller to keep in step. The
question [`grader-repeated-capture.md`](grader-repeated-capture.md) records
under "New questions this opens" — that a third `nargs="+"` capture grader
reaching into a fourth file for a seven-line helper is a sign the rule wants a
small shared module of its own — is about `distinct_captures` and its callers,
not about this one, and putting a helper in a file several branches are editing
to serve a single caller is a worse trade than a few duplicated lines would be.

**Every disagreement is named at once, in a stated order**: intervals first,
then levels by ascending address, and within one disagreement the files in the
order they were given. One run refused per disagreement discovered serially
would cost the operator a command line per disagreement, and the order between
them would be whatever the loop reached first. The order is asserted by
`test_one_refusal_names_every_disagreement_in_a_stated_order` rather than left
to be discovered by running the thing, which is
[`0751-file-refusal-order.md`](0751-file-refusal-order.md)'s finding applied
one level down: which refusal an operator reads first is part of the verdict.

Measured, on the suite's own constructed pair — an interval disagreement and
two addresses at different levels, so all three clauses in one sentence. The
levels, addresses, order and interval values are the tool's; the temporary
directory prefix on the two paths is elided, because `two_captures` writes into
the suite's `TemporaryDirectory` and the sentence the tool prints carries them
absolute:

```
2 captures disagree about a figure a merged run can only take from one file, so no run was built: the sample interval is 0.01s in 'part0.csv' and 0.05s in 'part1.csv', and one of them would have been the interval the 'the step is not resolved' check judged a median step taken over all 2 files against; the `# baseline` level of 0x0635 is 0x14 in 'part0.csv' and 0x0C in 'part1.csv', and one of them would have been reported as the level it held at, over a span that includes the other file; the `# baseline` level of 0x06D6 is 0x09 in 'part0.csv' and 0x04 in 'part1.csv', and one of them would have been reported as the level it held at, over a span that includes the other file. `load()` merges the rows of every file it is given, so there is no report of this run that can print both. Grade them one at a time, or re-take them so that they agree.
```

**It does not say nothing was read, because everything was.** The repeat
refusal in `main()` says that and it is true on that path —
`fan.distinct_captures` runs before any file is opened, so a repeated path
really does cost nothing. This sentence is reached only once every path has
been opened and parsed, and reading them all is the only way to know they
disagree: the sentence then names what it read. Carried over, `so nothing was
read` sent an operator looking for an unreadable file rather than for two
captures taken at different `--interval` values, which is the problem the
message exists to name. It says the run was not built, which is what did not
happen.

Each clause says what *this* disagreement would have cost, which is the
`grader-repeated-capture.md` rule that each refusal names its own damage rather
than sharing one message with a sibling grader. The refusal is raised from
`load()` before any row is sorted, a gap is found or a line is printed, and
`main()` catches it around `grade(paths)` — so a refused merge costs stderr and
exit 1, with no half-printed report behind it.

`main()` catches `ValueError` rather than a class of its own, which is what
`bom_refusal`'s shape asks for and what keeps this looking like the refusal it
borrows. The price is stated in the comment at the call site rather than
papered over: a capture carrying a row `int()` cannot read also raises
`ValueError`, and now prints that message and the same exit 1 instead of a
traceback. The two sibling graders validate the row shape and name the field;
this one does not, and giving it that is a separate change from this one.

## Two shapes reach that sentence, and it has to be true of both

The sentence above is a merge of files that disagree. The other shape is a
**single file that disagrees with itself** — its own `# interval` line stating
two values, or its own `# baseline` line naming one address at two. `load()`
collects both the same way: `INTERVALS` and the local `levels` list are appended
per *entry*, and nothing downstream of that knows which file an entry came from
beyond the path it is filed under. So the second shape is not hypothetical, and
the sentence was wrong on it in four places at once:

| clause | said | now says |
| --- | --- | --- |
| opening | `1 captures disagree about a figure a merged run can only take from one file` | `1 capture contradicts itself about a figure a run can only take from one file` |
| interval | `a median step taken over all 1 files` | `a median step taken over this run's rows` |
| level | `over a span that includes the other file` | `over the whole of that capture, the other value never printed` |
| closer | `Grade them one at a time, or re-take them so that they agree.` | `Grade it on its own, or re-take it so that it states one value.` |

There is no second file in that sentence, no row merge between two, and no
other file's rows for a span to include. What is the *same* in both shapes is
the damage underneath: `load()` reaches `baseline.setdefault(a, v)` and
`INTERVALS[0][1]`, so whichever value it saw second was dropped without a word
— from a second file's `# baseline` in one shape, from the same file's second
line in the other. Each clause says that in the terms its own shape has: a
merge can point at the other file, and one capture can only point at itself.

**The merge halves are untouched, so nothing above moved except the one clause
the previous section is about.** All four entries in the table's middle column
are still what the tool prints for a merge, word for word, and the transcript
carries the new opening. That is deliberate: those four sentences are what the
write-up's measurement recorded and what the two merge tests assert, so
changing one to fit the other shape would have moved a measurement to make a
sentence shorter. Each is pinned where it is used —
`over all 2 files` in `test_an_interval_disagreement_is_refused` and
`over a span that includes the other file` in
`test_a_baseline_level_disagreement_is_refused`, the latter beside
`assertNotIn('nothing was read')` so the merge half cannot take the one-file
opening either.

**Reaching the second shape needs a capture the committed writer cannot
produce.** `ec_timer_capture.py:314` takes its levels from a dict keyed by
address, and it states each `# interval` line once because `:278` takes
`--interval` per invocation. So one address at two values takes a hand-edited
or foreign capture. That is a statement about how the shape arises and not about
whether `load()` refuses it: it does, on both figures, and
`test_a_single_capture_contradicting_itself_is_refused` pins all four clauses,
the six phrases the shape cannot support, and a graded control beside them.

## The two cases that stay a merge, on purpose

Both were decisions, and a later merge needs to know they were not oversights.

- **A file with no `# interval` line contributes no interval.** The refusal
  fires only when two files that *state* one state different ones. The
  accepted-merge header then says how many state it — `stated by 1 of 2 files`
  — which closes the "where did this come from" question rather than leaving
  it half-open. (The reader's pattern needs an ` addresses: ` clause too, so a
  capture without one states no interval at all; that is the format's, not this
  change's.) **Both sides of that clause count files.** It reads
  `len({p for p, _ in INTERVALS})` of `len(paths)`, and `INTERVALS` holds one
  entry per `# interval` **line** rather than per file, so counting entries put
  the numerator above the denominator — a file stating its interval twice at one
  value, merged with a second that states one, printed `stated by 3 of 2 files`.
  A repeat at the same value is graded, not refused (`merged_capture_refusal`
  groups by value, so only a genuine conflict trips its test), so the two units
  can differ on a run that produces a report at all. Counting files is what makes
  the sentence answer its own question; it does not change which runs are
  refused, and `test_the_interval_clause_counts_files_and_not_interval_lines`
  pins both ends — a numerator above the denominator, and a `1 of 2` that would
  otherwise credit a silent file with an interval it never wrote.
- **A file with no `# baseline` line for an address contributes no level**, and
  is not a disagreement. An address that no file gave a `# baseline` for prints
  `?` where the level would go — `s0 = "?"` in `grade()` — which already says
  the level was unrecorded instead of guessing one, and is unchanged here.

## The alternative readings, recorded rather than buried

**Report a level that changed at the seam** — the issue's other option for
`baseline`. It needs per-address level tracking across files and a new report
shape for every watched address, and it still has to answer which level the
run's first step is measured from. It is a bigger invention than the refusal,
and a later merge should take it deliberately rather than inherit it. The
`0x06C5` case in §4b of the sweep procedure is the one that would need it.

**Print both intervals and decline the resolution warning** — also the issue's
option. Rejected because it leaves the operator with a header that says two
things and a step verdict that says neither: the median step is a median over
both files, so there is no third number to judge it against and the warning
would have to be simply dropped. Dropping it silently is the defect this change
closes, one level up.

**Refuse only on disagreement, rather than label the union.** Half of the third
figure would then still print a duration that is a merge presented as a
measurement, which is the one the issue calls out by name and the one a reader
of `held at 0xNN over 25.0s` has no way to see through.

## Correction: the precedent the issue cites is at a different line

The issue names `bom_refusal` as being at `ec/tools/grade_0751_isolation.py:871`.
The claim is right and the line is not. On this tree `bom_refusal` is at
**`:980`**, `starts_with_bom` — the three-byte question `bom_refusal`'s caller
asks of the bytes — is at `:952`, and the raise beside it, `read_capture`'s
`raise ValueError(bom_refusal(path))`, is at `:1172`. `:871` is none of the
three: it is a comment line inside `class Window.__init__`, with the class
opening at `:859` and `self.span = 0.0` at `:877`. The line the issue named
lands in a different class entirely, and stays there.

That is a *line* correction, and a line is a rank into a file that keeps
growing, which is
[`check_citation_lines.py`](../ec/tools/check_citation_lines.py)'s stated
principle applied to a `.py` rather than to a generated CSV — so the three
figures above are dated to this tree, and where the symbols sat on the trees
this was drafted against is `git log -p ec/tools/grade_0751_isolation.py`, not
a paragraph restating each merge. On every tree measured, `bom_refusal` has
been at some line other than `:871`; the finding is that the issue's line was
wrong, which no later commit makes right.

The claim is kept and the line corrected here rather than dropped, per the
`docs/findings.md` §4a-4d pattern.

## What did not change

- **The single-capture report.** `test_a_single_capture_report_is_byte_identical`
  asserts the whole header line verbatim and asserts that neither new clause's
  wording is present, so a clause cannot creep in a fragment at a time.
  `test_clean_capture_gives_period_ten_and_ratio_ten` and
  `test_two_distinct_captures_are_still_one_run` are untouched and still pass
  on their own assertions.
- **`load()`'s return tuple.** Still `(watched, baseline, rows, span, interval)`.
  The count of files that state the interval reaches `grade()` through the
  module-level `INTERVALS`, and each file's own window through `WINDOWS`,
  beside the `RESUMES` and `GAPS` this module already keeps for a
  fill-a-global consumer, rather than by widening a tuple every caller has to
  unpack.
- **`test_two_distinct_captures_are_still_one_run` is kept as-is.** It is #491's
  control on the legitimate two-capture run, its three assertions are its whole
  job, and the new cases each carry the matching control — the same two files
  with the field under test made to agree.
- **`grade_timer_sweep.py`'s median-step division is still unguarded.** A
  capture whose median step is 0 reaches it with no repeat and no disagreement
  in sight. That is the open follow-up `grader-repeated-capture.md` records,
  it is unrelated to which file a figure came from, and fixing it here would
  widen the diff into code this issue does not discuss.
- **No register status moves.** A report's shape is not a register finding, so
  `ec/annotations/registers.yaml` and the 39-countdown prediction in
  `ec/annotations/xdata-06c2-06db-timers.md` §3 are untouched.
- **The sweep procedure is untouched.** Every grading command
  `docs/hardware-tests/xdata-06c2-06db-sweep.md` gives is
  `python3 grade_timer_sweep.py <capture.csv>` — a single file — and its six
  committed captures are graded one each, so none of its recorded results
  moves.
- **`ec/README.md` and `tools/README.md` are untouched.** The first describes
  single-capture behaviour, which is unchanged, and is a long shared file
  several branches edit; the refusal is documented in the grader's own
  docstring and here. The second's suite table already has a row for this
  suite, its row's description is not per-case, and the check compares the
  *set* of suites rather than their descriptions.

## One consequence, and one pre-existing condition

**Three citations in `ec/tools/measure_mark_provenance.py` were re-pinned.**
That table cites three lines inside `load()`, and every line below them moved
by this change. The three are re-pinned and resolve `ok` again, because a pin
this change made wrong is this change's to repair.
[`0751-file-refusal-order.md`](0751-file-refusal-order.md) declined to re-pin
its two for the opposite reason — they were *already* wrong before that change,
and repairing two of twenty would have made a broken table look maintained. The
distinction is the whole of the difference between the two decisions, and it is
recorded here because a reader comparing them will want it.

**The re-pin is this change's to repeat, not a one-off repair.** The three pins
name lines inside `load()`, so any edit above them in that file moves them
again, and a `line moved` entry is this change's to fix rather than a debt to
leave for a later one. Two paragraphs in `merged_capture_refusal`'s docstring
and a four-clause branch in its body both sit above every line the table cites,
so the pins moved a second time with this fix — the sentences are the
deliverable, and a docstring that does not say why the one-file clauses differ
is a docstring that invites the next reader to merge them back. What does *not*
move is the count: three lines either way, and the number was never what the
re-pin is about.

**What the tool then reports, measured on both trees rather than asserted.**
It exits 1 on the base and on this branch. The count goes **40 → 43**, and the
three new entries are all the `check_page` half, for the three re-pinned
citations: `grade_timer_sweep.py:327`, `:354` and `:355`, each reported as
"cited here and not named in … `0751-mark-provenance-shapes.md` or
`0751-mark-provenance-column.md`". The base reports no entry of that kind at
all. So the re-pin trades three `line moved` entries for three
`check_page` entries, and the two kinds are the same three lines seen from
opposite ends: the table now points at where they are, and the pages still
name where they were.

Both figures are a dated reading of the two trees this was measured on, not a
total that stays true: 40 is what `origin/main` gave before this change and 43
is what this tree gives now, and the next change to a cited file moves the
number without invalidating the three named entries. The current one comes
from running `python3 ec/tools/measure_mark_provenance.py`, which prints the
entries it finds rather than a total — the figures above are its output
counted, and re-running it is what a later reader should do rather than
trusting the arithmetic here.

**The two pages are left quoting the old pins, on purpose.**
`0751-mark-provenance-shapes.md` says so itself, in the correction note closing
its §5: "**The transcripts in sections 1, 2, 3 and 5 are the measurement's as
taken, and their line numbers no longer describe the tree** … Re-run `python3
ec/tools/measure_mark_provenance.py` rather than trusting the quotations."
Those blocks are a dated record of a measurement, not a live index of the tree,
and this change is not a new measurement — it moved three lines in a file those
pages were not measuring, and then moved them again. Re-pinning them would edit
a transcript to describe a tree the transcript never saw, which is the thing the
note is warning against.
So the count is left at 43 and the three entries are named here rather than
discovered by running the tool. The tool is a census and no gate reads it; the
exit code is 1 on both trees either way.

**`gen_findings_index.py --check` was already failing on the base, and a later
commit on `main` fixed it.** Measured on the branch's base (`fe6ce6c6`): the
committed `docs/findings/INDEX.md` said 178 write-ups while the tree held 179
before this one was added — and only the *count* was stale, every row the
generator writes was already in the file. That is the same failure
[`findings-index-staleness.md`](findings-index-staleness.md) measured at
`30144f0b` (#1212), where a hand-added row left the header count behind.

`main` has since regenerated its own copy — at `origin/main` the committed count
and the tree agree — so the staleness above is a *base* condition and not
one this merge reintroduces. The conflict this branch hit was the ordinary
one the file's own docstring predicts: two branches that both add a write-up
and both regenerate produce two different counts for the same tree, and the
resolution belongs in the content rather than in the prose.

**The index is generated, and the generated count is the only one that has to
be right.** This write-up adds a row, so the fix is to run
`python3 ec/tools/gen_findings_index.py > docs/findings/INDEX.md` and let the
header fall out of the tree: `python3 ec/tools/gen_findings_index.py --check`
exits 0 here, and `gen_findings_index.py | diff - docs/findings/INDEX.md` is
empty. A total written into this paragraph would be a value every later
write-up has to come back and edit — the shape CLAUDE.md rules out — so the
tool's output stands in for it and no figure is kept here.

That is also the shape of the failure described above: a hand-added row
leaving the header count behind, the same thing
`findings-index-staleness.md` measured at #1212, and one this write-up
committed itself before the regeneration. What made it survivable is that
`--check` catches it — the count is generated, so nothing has to remember it,
and the only claim worth making about it is that the check is green.

Note for the record that the check is wired into the gate only by
`docs/ci/agent-gates-findings-frozen.patch`, which is prepared and not applied
on `main`, so regenerating the index is required by the convention rather than
by a red CI job today.

## How to re-check this

```console
python3 ec/tools/test_grade_timer_sweep.py
python3 -m unittest ec.tools.test_census_test_line_pins
python3 ec/tools/gen_findings_index.py --check
bash tools/run-tests.sh
```

**The evidence is the behaviour, not the pass count.** The refusals each exit
1 with their file names, values and address in stderr and an empty stdout; the
accepted merge still prints `span 25.000s`, `median 100.0 ms` and
`period / step = 10.00`; the nested pair prints the union half and *not* the
`which none of them covers` half; and the single-capture header is asserted as
a whole line. Nothing here needs Ghidra, the Windows stack, or anything
`.github/actions/project-setup` installs beyond Python.

## What this leaves open

- **A level that changed across a seam between two captures is still
  unreportable.** The refusal is the honest answer for now; the per-address
  seam reporting above is the real fix, and it is a separate change.
- **The median-step division is still unguarded**, named above and unchanged.
- **Whether the span should ever be a union of comment timestamps as well as
  rows** is a question about the format rather than about this merge, and it is
  recorded here because the merged header now draws attention to the span.
- **The third `nargs="+"` grader question is still open.** If one appears that
  *does* read `# interval` or `# baseline`, `merged_capture_refusal` is the
  thing to share, and a small shared module rather than either grader is the
  shape `grader-repeated-capture.md` already argued for.
- ~~**Nothing here has been run against a committed capture.** The two-file
  case is for an operator who took two captures of the *same* sweep either side
  of a suspend — not for the sweep procedure's §4a and §4b arms, which are two
  different runs and would be a merge of the wrong thing. Whether
  `evidence/ec-watch/2026-09-24-06c2-06db-suspend-linux.csv` and a second
  capture merge cleanly is one command a person at the machine can run, and no
  result of it is claimed here.~~ **Corrected by
  [`merged-capture-against-committed-pair.md`](merged-capture-against-committed-pair.md)
  (issue #1452):** that run has now been done, and two of the three claims
  above are wrong. It is **not** a command for a person at the machine — the
  grader is offline and both captures are committed, so it runs anywhere.
  And the two-file case is still not §4a and §4b: those remain two different
  runs and this pair is still a merge of the wrong thing, which is why the
  refusal is correct rather than a defect. What is measured is exit 1 with an
  empty stdout and one disagreement, `0x06D6`'s `# baseline` level at `0x04` in
  the suspend capture and `0x03` in the perturb capture; the interval clause
  does not fire, because both state `0.01s`; and a control in which that one
  token is made equal grades and exits 0.
