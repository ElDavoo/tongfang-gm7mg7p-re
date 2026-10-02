# The refusal-contract page's third red-suite claim was corrected in place and never joined the inventory that exists to stop a fourth copy (issue #828)

The write-up for [issue
#828](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/828), which is
about `xdata-green-set.md`'s **Superseded claims** table stopping one claim
short of the claims the refusal-contract page names side by side. What this
branch changes is a dated paragraph inside that page's existing `#816`
blockquote, a row in that table for each of the two claims it was missing, and
this file. **No tool, no CSV, no YAML, no suite and no gate script is edited.**

**Nothing here is a hardware claim.** No register was read back, no capture was
opened, no image was parsed, and no laptop, EC or Windows machine is involved.
Every figure below is the output of a command over committed text, and no
`status:` in `ec/annotations/registers.yaml` moved.

## The gap, which is a gap in the inventory and not in the page

`docs/findings/xdata-no-eq-guard-refusal-contract.md` states its red-suite
claims in the present tense a few lines apart. The inventory's table carried
some of them and not all:

| the page's claim | a row for it? |
|---|---|
| `test_xdata_cluster_names.py::TheGuardOffRegeneration` — "6 tests, none of which run" | no — it is `#753`'s subject, and the table's `xdata-register-map.md` and timers rows cover that page instead |
| `test_check_site_census.py` — "45 tests, 1 failure" | **yes** |
| "the only working scripted route to a guard-off census" | **yes** |
| `test_check_cluster_citations.py` — "46 tests, 1 failure" | **no, and this is the one this issue is about** |

Every row here is the same shape of claim — a suite named, a count and a verdict,
on a page that is a record — and **each of them carries a dated `#816`
correction in place on the page**, so an in-place correction is not what the
missing row is evidence of. The two existing rows were added in one commit
(`d87d877e`, issue #819), whose subject is a sweep over "four sentences that
said otherwise" — a scope that file has since had to reconcile against its own
list, under **The five sentences corrected in place, and where**. This claim was
not in that scope. **Why is not recorded in the tree, and is not guessed at
here**: the commit names what it swept and not what it left.

So the page was not wrong and its correction was not missing. **The row was**,
and a claim with a dated correction and no owner
is the state that lets the next reader re-derive it a fourth time.

## The measurement, which is not the one the issue was filed on

The issue recorded both of its commands re-deriving green. **They still do**,
and that is the least interesting part of this write-up — the case the claim
names has since stopped being red, and the count under it is not the one either
the claim or the issue recorded:

```console
$ cd ec/tools && python3 -m unittest test_check_cluster_citations
Ran 63 tests in 1.475s

OK

$ python3 ec/tools/check_cluster_citations.py; echo "rc=$?"
…: every checked cluster citation (`main-ec-NNN`, `cluster_key` or `cluster_name`)
resolves to the membership it names, and every hand-typed census count agrees with
ec/annotations/xdata-clusters.csv
rc=0
```

The tool's leading `files / lines` count and its trailing count of passed-over
units are both elided above, and both on purpose. **Each is a property of the
corpus rather than of the rule**: they move every time a page is added — this
one included — and a reader who wants either has the command. What the run
establishes is the verdict, the exit code, and that the pass-over reasons are
named per reason rather than summed, which is what makes "not checked, not
absent" checkable.

`TheCommittedTree::test_committed_prose_matches_committed_census` — the case the
`#816` entry names as the suite's one failure — **passes**, and the tool exits
0. Neither the disagreement list nor the failing case reproduces. `bash tools/run-tests.sh`
agrees: every suite passes, and the totals line it prints is deliberately not
quoted here, for `runner-red-suite-set.md`'s reason.

**What cleared it is not a prose fix, and that is the part worth recording.**
[`guard-off-transcript-scope.md`](guard-off-transcript-scope.md) (issue #996)
scoped the rule instead of the sentence: `check_cluster_citations.py` now passes
over any unit inside a fenced block whose body runs `xdata_register_map.py`
under a flag that *changes* the census, and names the reason
`census-regeneration transcript`. The `0x0464`/`0x0465` line in #822's write-up
is inside such a block, so it is a rank in a census the reader cannot open
rather than a claim about the committed census. **The sentence #822 wrote is
unchanged and the check that used to fail on it is gone** — which is a
different answer from the one that write-up asked for, and worth being explicit
about, because "the line moved" and "the line is now out of scope" are not the
same claim.

The claim's halves are therefore now false for different reasons, and the
page's own block is where a reader meets both: the count moved `46 → 48` under
`#816` and again since, and the redness went from *one file's line* to *no line
at all*.

## Why the finding this re-derivation was supposed to turn up is not reported here

The issue's own re-derivation records `check_cluster_citations.py` as **red on
three citations** rather than the one every write-up names, and treats the third
— a `main-ec-002` "named inside" cell reading 27 against the census's 31 — as
new and unrecorded. **On this tree that is not the case, and the reason is worth
more than the finding would have been.**

`git log` says the redness and the stale count were cleared together, in
`395ef26d` (issue #996), by scoping the rule and correcting the cell in the same
change. That cell now carries a `CORRECTION (2026-09-30, issue #996)`
blockquote naming each step of its own history — the figure moving between the
census's reading and the hand-typed one every time the census was re-derived,
never a transcription slip — and the row agrees with the committed CSV today.
**So the third disagreement is neither present nor unrecorded**, and writing it
up as a new finding would put a false claim into the tree to fix a gap that has
since been closed. It is named here instead, as the reason the measurement
differs.

The limit that correction names is the durable part, and it is a limit rather
than a defect: `check_cluster_citations.py`'s count rule holds a census *row* to
the CSV, and nothing holds a *sentence in a note* to it. The cell moved more than
once that way, and the tool saw the row each time and the prose never. **A green
run is therefore not evidence that the prose agrees with the census everywhere**
— only that it agrees where the rule reads.

## What is not established

A green `check_cluster_citations.py` says the committed prose and
`ec/annotations/xdata-clusters.csv` agree. **It says nothing about the
clusters, the `0xD96C` routine, or `main-ec-086`'s membership**, and no
`status:` in `ec/annotations/registers.yaml` moves. #564's correction is not
owed, and this is now the second independent measurement saying so: the claim
in §26 is true, and the suite has no opinion about it either way.

The count is a property of the merge rather than of any suite, so the `46 → 48`
move the `#816` entry records is **not** explained here and need not be. Nor is
the jump from there to the count this branch measured.

## Left out on purpose

- **The red-suite claims' own sentences.** Each is on a page that is a record,
  and each already carries a dated correction. Editing one would delete a record
  rather than add one; this branch adds a paragraph and rows, and edits no
  claim.
- **`docs/findings.md` §29.** Its "§26 above pairs `0x0800` with
  `main-ec-086`" sentence is named in an inventory row and marked **left as the
  record**. §29 is a dated section that already carries an
  `**Updated 2026-09-25, issue #816**` addendum answering the same question, and
  `check_findings_frozen.py` fails an edit to that file's structure. The row
  says which reading was taken, as the issue asks.
- **Re-deriving why the suite's count moved, or re-deriving the runner's
  totals.** Both are properties of the merge, and quoting either would be a
  figure every merge has to edit.
- **The `#996` write-up's own claims.** Whether the transcript scope is the
  right rule is that write-up's argument, already made and already merged; this
  branch records that its rule is what cleared the suite and does not re-open
  it.
- **A new test.** No gate in this repository reads prose, so a check asserting
  that a correction stays true is a new tool for a two-row change, and
  `check_cluster_citations.py` already reads the page this branch edited — the
  run above is the test, and it is the one that would catch this branch turning
  the page red.
- **Hardware, Windows, the firmware image, and any live run.** No register is
  read back and no capture opened. No `needs-hardware-test` work is involved:
  both commands are runs over committed text.
- **Anything upstream, and any issue closure.** Nothing here ends at a
  `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers` pull request, so there is no
  prepared patch to hand over; #10 stays where it is. #564, #816, #822 and #826
  are named and left open — whether a superseded issue should be closed is a
  human's call.

## The test that proves it works

The record stays a record, and the new paragraph is the next dated entry in the
same block rather than a block under it:

```console
$ git grep -n "46 tests, 1 failure" -- docs/findings/xdata-no-eq-guard-refusal-contract.md
$ git grep -n "Corrected 2026-10-02, issue #828" -- docs/findings/xdata-no-eq-guard-refusal-contract.md
```

Both the original claim and the sibling above it are still present as quoted
text, and neither is reworded.

The inventory is now exhaustive for the claims the page names, which is the
property rather than a count of rows:

```console
$ grep -c "^| \`xdata-no-eq-guard-refusal-contract.md\`" docs/findings/xdata-green-set.md
$ grep -c "^| \`docs/findings.md\` §29" docs/findings/xdata-green-set.md
```

Both rows are present, and the `docs/findings.md` rows the table already carried
are untouched — the diff is an append.

**The self-referential check is the one that matters here**, because this file
and the page it corrects are both inside the corpus `check_cluster_citations.py`
walks, and this write-up quotes sentences naming addresses and cluster ids:

```console
$ python3 ec/tools/check_cluster_citations.py; echo "rc=$?"   # must still be rc=0
$ cd ec/tools && python3 -m unittest test_check_cluster_citations   # must still be OK
```

The page's own `#816` block records that quoting §26's sentence is enough to
turn the suite red, which is how that write-up's first draft failed. If either
command above stops being what it is here, **this file is rewritten, not the
tool.**
