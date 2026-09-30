# The measurement tool's pins, re-anchored, and one `what` that had to be re-worded (issue #762)

`ec/tools/measure_mark_provenance.py` names every site its write-up rests on
as a `(path, line, quoted text)` pin and re-reads each one on every run. On the
tree this re-anchor ran against it ran to completion and **exited 1 with 40
citation problems**: 26 pins read `DRIFT`, and the row-site join reported 14
problems in its two directions. Every one of the 26 still had its quoted text in
the tree — **not one had vanished** — so this is the arithmetic case, and the
arithmetic is the boring half.

**On the tree this lands on the figure is 43, and the difference is not this
re-anchor.** #1406 landed on `main` after it, moved the tool's own three
`grade_timer_sweep.py` pins with the code, and did not move the two findings
pages that name them — so those three pins resolve here and `check_page` reports
them instead: the same **26** `DRIFT` and the same **14** join problems, plus
**3** citations the pages cannot account for, and `main()` sums all three into
the `43 citation problem(s)` it exits with. Both trees are recorded rather
than one being quietly preferred; *A fourth move, on a different file* below
says what #1406 did and where the three pins are now.

The issue this closes reported a crash at `:601` and 37 citations. Both were
measured against a different tree, and both corrections are recorded below
rather than quietly applied, because the difference is the record of what
happened in between.

## What the issue reported, and what this tree has

| | issue #762 says | measured on this tree |
|---|---|---|
| `check_citations` at | `:601`, unpacking 3 from 2 | `:730`, and both its loops unpack 2 |
| a wrong width | `ValueError` out of a for-loop, every run | the loops agree; the *named* error is absent |
| citations | 37 | **48** |
| drifted | 29 | **26** |
| need judgement | 2 (`ec_watch.py:254`, `:280`) | **1**, and it is not either of those |

The crash was already fixed before this issue opened. #749 fixed the unpacking;
`main`'s `scan` and `check_citations`'s `named` are both 2-tuples today, and
running the tool prints sections 1 through 5 and exits with a count rather than
a traceback. Neither of `check_citations`'s two set-difference loops unpacks
three, and `grep -nE "for [a-z_]+, [a-z_]+, [a-z_]+ in"` returns eight hits of
which none walks either set: two are `os.walk` (`:217`, `:298`), one is the
`section_rows` sum over `families` (`:488`), one is `COMMENT_PHRASES` (`:794`),
and the four that do touch a scanned row are `main` printing it (`:971`,
`:974`, `:979`) and the comprehension that narrows it to pairs on the way in
(`:1014`). That narrowing is what `site_arity()`'s own error text describes
at `:726`, which rejects a site set still carrying the text because it "was
never narrowed, and unpacking it here would raise" the `ValueError` it is there
to name. What was still true when the issue was filed is the half it asked for
and the half the tree lacked: **a wrong width failed as a `ValueError` out of a
for-loop rather than as a named error.** That half is kept and is now
`site_arity()`.

**The `:730` in the table is itself a correction, and it is the same failure
this issue exists to close, one level up — twice.** This write-up first
recorded `check_citations` at `:705`, which was true of it on the tree this
re-anchor ran against and stopped being true the moment `site_arity()` was
added above it. On this tree `site_arity` begins at `:707` and `check_citations`
at `:730`, so **`:705` and `:728` are both blank lines.** Neither figure is
edited away, because the mechanism is the point twice over: a self-referential
line number in a write-up about self-referential line numbers drifts the way any
other pin does, nothing held the original, and nothing held the correction
either. The substituted `:728` is `:705` plus the **+23** that adding
`site_arity()` cost, and it dropped the **+2** a two-line comment inside
`CITATIONS` (`#1449`) had already added on `main`: the move is 25 lines, not 23.
The error is arithmetic in the correction, not in the pin.

The two pins the issue predicted would need judgement were taken long before
this issue: `CITATIONS` already reads `def warn_unchecked_marks(path,
existing_findings):` at `windows/tools/ec_watch.py:295` and
`accepted, refused, unplaceable = existing_findings(path)` at `:381`, both of
which resolve. The rename and the three-value unpack were recorded as the same
facts when they happened, so the only `ec_watch.py` re-anchors left are the two
arithmetic ones — `:368`→`:381` and `:493`→`:509`.

## The one that did need judgement: `:986`

`grade_0751_isolation.py:986` pinned
``' `addr == "MARK"` before the `int()` calls, and so does this'`` with the
claim *"the partition's docstring quoting that branch, which the scan matches
because it is the same literal spelled in prose"*. The text resolves uniquely,
to `:1190` on the tree this re-anchor ran against — but `:1190` is inside
**`refused_capture_rows`**' docstring (the `def` is at `:1161`), not the
partition's. `partition_capture_rows` is a different function, at `:1366`.

The claim and the line had come apart, and the line had been wrong before this
change: the same sentence was already inside `refused_capture_rows` at `:986` on
#748's tree, where `git log` puts it last at `:760`. So this is not drift that
a later edit introduced into a correct pin. Re-read, the sentence is fine and
the *name* was not: the docstring says "and so does this", meaning
`refused_capture_rows` re-applies `take_capture_row`'s `MARK` branch rather than
re-deriving it, which is exactly what that function is for. **The `what` is
re-worded to name `refused_capture_rows` and the line is re-anchored** — to
`:1190` when this ran, to `:1266` when #1409 landed, and to `:1271` on the tree
as it stands now, for the reason the next section gives. Moving the number and
leaving a claim that describes a different function is the failure
`0751-notice-two-moments.md` already records once, and it is the one this issue
exists to close.

## The 25 that were arithmetic

Nine of the 26 pinned texts appear at more than one line, so a text search alone
does not resolve them. Each is settled by the enclosing `def` matching the
pin's own `what` — which is a claim the table already made, so the tie-break
reads the pin rather than the file:

| pinned | now | candidates | settled by |
|---|---|---|---|
| `:1064` `if addr == "MARK":` | `:1268` | `take_capture_row`, `partition_capture_rows` | `what` names *take_capture_row* |
| `:1192` same text | `:1396` | same | `what` names *partition_capture_rows* |
| `:1086` `if len(row) > 1 and row[1] == "MARK":` | `:1290` | `mark_labels_of`, `existing_mark_provenance` | `what` names *mark_labels_of* |
| `:1156` same text | `:1360` | same | `what` names *existing_mark_provenance* |
| `:890` `if skippable_row(row):` | `:1094` | five functions | `what` names *read_capture* |
| `:1084` same text | `:1288` | five | `what` names *mark_labels_of* |
| `:1179` same text | `:1383` | five | `what` names *partition_capture_rows* |
| `:1061` `if len(row) < 4:` | `:1265` | `take_capture_row`, `partition_capture_rows` | the other two `if addr == "MARK"` pins put `read_capture`'s own body at `take_capture_row` |
| `:1063` `ts, addr, old, new = row[0], …` | `:1267` | same | same |

The last two are the ones a plan written against a 25-pin count would have
called unique: `if len(row) < 4:` and the explicit indexing each appear in
**both** `take_capture_row` and `partition_capture_rows`, so a text search
returns two lines for each and neither is self-evidently the pinned one. They
are settled from the pins beside them rather than from the text alone. The
remaining 17 resolve uniquely, `read_capture` `:852`→`:1049`,
`read_early_exits` `:1435`→`:1668`, `ec_watch.py:493`→`:509`,
`manual_fan_ctrl_probe.py:443`→`:450`, and the rest.

**What a re-anchor asserts, and what it does not.** It asserts that the pinned
*text* is at the line quoted. It does not assert the claim is still right —
that is what the `what` is for, and `:986` is the one case where re-reading the
line changed the claim rather than only the number. No pin whose `what` is a
statement about EC behaviour was touched; every `what` here describes a file's
structure.

## The join closed in both directions by the same move

The 14 join problems were not separate work. Each of the 7 `named - scan` lines
had its text at exactly one of the 7 `scan - named` lines, so re-anchoring onto
the lines the scan actually reports closes both directions at once:

| old | new | | old | new |
|---|---|---|---|---|
| `:986` | `:1190` | | `:1156` | `:1360` |
| `:1064` | `:1268` | | `:1192` | `:1396` |
| `:1086` | `:1290` | | `ec_watch.py:493` | `:509` |
| | | | `manual_fan_ctrl_probe.py:443` | `:450` |

`check_page` is the other half and it is not optional: it fails any `path:line`
in `CITATIONS` that the two findings pages do not name, so a re-anchor is not
done until the pages carry the new numbers. All 26 old anchors were named in
those pages before this change.

## The second move: #1409 landed on top of it, and a third on top of that

Every `now` in the two tables above is the tree **this re-anchor ran against**,
and #1409 then landed on it, so those 19 `grade_0751_isolation.py` lines are no
longer where this write-up says they are. The move is the same one, a second
time, and it is worth naming because it is what a pin table is: #1409 added
window reporting to the grader and touched **no line a pin quotes**, so every
one of the 19 went red as pure arithmetic.

It is not one shift. `:1190`→`:1266`, `:1268`→`:1344`, `:1290`→`:1366`,
`:1360`→`:1436`, `:1396`→`:1472` and everything from `read_capture` through
`existing_mark_labels` all moved by the same **+76**; `read_early_exits`
`:1668`→`:1744` and the census line `:3418`→`:3741` moved further, because the
reporting went in above them. The seven pins naming `ec_watch.py`,
`manual_fan_ctrl_probe.py`, `grade_gpu_door.py` and `check_capture_claims.py`
did not move at all — #1409 did not touch those files — which is the useful
half: **a uniform shift is evidence the merge took both sides rather than
picking one.**

> **Correction to the paragraph above (2026-09-30, issue #762), leaving it as it
> was written.** `read_early_exits` did **not** move further. `def
> read_early_exits(path):` is at `:1668` in `126a67c8^` and at `:1744` in
> `126a67c8` — the same **+76** as `read_capture` `:1049`→`:1125` and
> `take_capture_row` `:1268`→`:1344`, measured in both trees rather than read
> off the diff. Locating all 19 `grade_0751_isolation.py` pins' quoted text in
> both trees and settling the nine ambiguous ones by their enclosing `def`
> gives **three** shifts where the paragraph gives two: **17 pins at +76**,
> `read_early_exits`' two (`:1668`→`:1744` and `:1710`→`:1786`) among them; the
> module-level `EARLY_EXIT_TAG` `:453`→`:516` at **+63**, because the reporting
> went in *below* it; and the census line `:3418`→`:3741` at **+323**, the one
> pin that moved further and the only one that did. The `+63` is named because
> the paragraph's "it is not one shift" is right and its list did not exhaust
> the 19: the single pin above the insertion point moved *less*, which the
> paragraph did not claim either way. The `+323` and its cause are unchanged.
> The same three shifts are visible in the re-anchored table on
> [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md), whose own
> sentence — "a larger one past `read_early_exits`" — describes the census line
> below `read_early_exits` and so was never this error.

**And then #1437 moved them a third time, which is the smallest of the three.**
Five lines went into the grader's module docstring, above every pin, so
`take_capture_row` `:1344`→`:1349`, `refused_capture_rows`' docstring
`:1266`→`:1271`, and the census line `:3741`→`:3746` — a uniform **+5** over the
same 19, and the other seven rows unmoved again. It is the third time the same
arithmetic has run on these pins, and the third time it has been pure
arithmetic: #1437's own change is the movement-path sentence, which is
`main()` and below every pin.

Nothing about any pin's *claim* changed on any of these moves either. The
re-worded `what` for `:986`→`:1271` still describes `refused_capture_rows`,
because neither #1409 nor #1437 moved the sentence into another docstring. The
current pins are what `0751-mark-provenance-shapes.md`'s live table carries, and
`check_page` is green against them.

**What this is not.** It is not a second finding, and no issue follows from it.
It is the same arithmetic, and the reason it appears here rather than nowhere is
that a reader of the tables above would otherwise take `:1349` for a line
`take_capture_row` does not have.

## A fourth move, on a different file, and the pages that have to follow it

The three moves above are all one file's, and none of them is what the merged
tree needed last. #1406 changed `grade_timer_sweep.py` — the merged run now
names where its interval, its levels and its span came from, and refuses a
capture or a merge that disagrees, which is
[`grader-merged-capture-sources.md`](grader-merged-capture-sources.md)'s subject
— and grew it by four hunks, **+197** above the `#`-skip and **+201** above the
mark branch, without touching a line any of the tool's three timer pins quotes.
So the arithmetic ran a fourth time, on three pins this write-up had not
mentioned: `if line.startswith("#")` `:130`→`:327`, `if r[1] == "MARK":`
`:153`→`:354`, and `if "resumed" in r[3]` `:154`→`:355`. No `what` needed
re-wording, and none was: all three describe `grade_timer_sweep.load`'s own
shape, and #1406 added reporting rather than moving a branch between functions.

**These three are the ones that needed the pages, and they are worth separating
from the other 26 for what they say about `check_page`.** #1406 moved the
*tool's* pins with the code, so on `main` the three resolve and `check_page`
reports them: cited at `:354` and named by neither findings page. That is the
failure this whole write-up exists to stop, arriving from the opposite
direction — not a line that moved under a pin that stayed, but a pin that moved
correctly and left its write-up behind. **It is also the one figure neither
side's tree could have shown on its own:** on the tree this re-anchor ran
against the three sat at `:153`/`:130`/`:154` and needed no move, and on `main`
after #1406 they sat at `:354`/`:327`/`:355` and needed no move either — what
neither tree has is the two together, and a re-anchor that took the branch's
`now` would have handed back three pins pointing at nothing. The three rows are
now the last three of `0751-mark-provenance-shapes.md`'s live table, with
`:130`/`:153`/`:154` as their `before` values, and the tool exits 0 on the merged
tree.

## A fifth move, one pin of nineteen, and the lesson in the other eighteen

**The merge this write-up landed on re-ran the arithmetic once more, and this
time on one pin rather than on a file.** #1450 landed on `main` after this
branch's base and made the grader's census count a capture the way its
per-action line already did — one file under two spellings is one file, which
is [`0751-census-capture-identity.md`](0751-census-capture-identity.md)'s
subject — and it put nine hunks into `grade_0751_isolation.py`, the running
shift **+27** by the second and a **+38** past the last, every one of them at
or below old `:1826`. **Eighteen of the 19 `grade_0751_isolation.py` pins sit
above that line and did not move at all.** Only the per-capture census line did:
`:3746`→`:3784`, in `CITATIONS` and in the shapes page's live table, its
`what` still describing the same line and no row's `before` disturbed.

**It is worth naming because the other four moves were all whole-file and this
one is not.** Re-anchoring these tables by "this file moved, so add the file's
line delta" would have moved eighteen pins onto lines that had not moved, and
`check_page` — which asks only whether the page names the line the tool cites,
not whether the page is right about it — would have stayed **green** on all
nineteen. That is the gap this re-anchor's own new suite closes on the other
side of the join: the tool's line check is what makes a wrong anchor red, and
it is only as good as the shift arithmetic that fed it. The measurement is per
hunk, from the diff, not per file, and the eighteen unmoved rows are the
evidence for that rather than a detail left out.

## What the pages do about it, and what they deliberately do not

`0751-mark-provenance-shapes.md` carries a #739 correction stating that its
transcripts in sections 1, 2, 3 and 5 are **the measurement's as taken** and
that a reader is to re-run the tool rather than trust the quotations. Its
section-5 transcript is therefore **left as it was written**, and the current
run's section 5 is added beside it as a second block. Rewriting a quotation
that a page explicitly freezes would destroy the record the correction is
there to keep; adding the live half is what `check_page` actually needs.

Its live `:NNN` shorthand is left alone for the same reason, and that is stated
in the page rather than left for a reader to infer: `:845`, `:890`, `:1061`,
`:1063`, `:852`, `:896`, `:1087` and `:1084` name the same functions the new
table names at `:1123`, `:1175`, `:1346`, `:1348`, `:1130`, `:1181`, `:1372`
and `:1369`.

`0751-mark-provenance-column.md` is different: its **live prose** makes
present-tense claims ("`ec_watch.py:509` now writes"), so those anchors are
re-anchored (`:493`→`:509`, `:438`→`:454`, `:562`→`:578`, `:573`→`:589`,
`:443`→`:450`, `:845`→`:1123`, `:576`→`:607`), each verified against the file
first. **Four more on the same page were found by the review of this branch and
are re-anchored with them** — `grade_timer_sweep.py:153`→`:354` and `:154`→`:355`
in §3, `grade_timer_sweep.py:151`→`:352` under *The header*, and
`manual_fan_ctrl_probe.py:382`→`:389` in §4 — so the list above is eleven and
the page is not left half-corrected in the way
[`prose-line-citations-held.md`](prose-line-citations-held.md) records. Each was
read in its file before it was written down, and the two causes are distinct
and worth separating: the three `grade_timer_sweep.py` lines moved because
**#1406** grew that file by +201 below its `#`-skip, and `arm_labels` moved
because **#1315** grew `manual_fan_ctrl_probe.py` by +7 above it. That is the
one measurement neither tree could show alone — the seven above were all
#739-era drift, and these four arrived with the two merges that landed after
this branch's base, so a re-anchor that had swept the page by grep for "stale"
would have had no way to tell the two populations apart without re-reading
each line. Its **after/before table** is #739's record of that change and is
left exactly as written, with the re-anchor noted beside it.

**The shapes page's own live prose is a third population, and it is left as
taken.** Its *Five sites the issue does not name* list and two rows of *What
each shape costs each reader* name `grade_gpu_door.py:479`, `ec_timer_capture.py`'s
four sites at `:169`/`:204`/`:210`/`:232`, `grade_timer_sweep.py:153` and
`check_capture_claims.py:514`, none of which carry their claim on this tree —
the figures are `:520`, `:177`/`:212`/`:218`/`:240`, `:354` and `:607`,
measured the same way. They are left alone deliberately rather than overlooked,
and the reason is the page's own stated convention rather than this branch's
preference: that page's #739 correction freezes its transcripts as taken and
tells a reader to re-run the tool rather than trust the quotations, and the
note under its evidence index already says which half is live ("the table is
the live half and the shorthand is the frozen one"). Re-anchoring seven more
prose anchors on a page that instructs readers not to trust its prose would
make the page's stated rule and its contents disagree, which is a worse fault
than the one it fixes. **These seven are pre-existing rather than introduced
here, and nothing in the tree holds them**: `check_page` reads that page's live
table, not this prose, and `census_test_line_pins.py` covers only `test_*.py`
pins, so this is the class
[`prose-line-citations-held.md`](prose-line-citations-held.md) records as having
no checker. They are named here so a reader knows which half of that page is
live, and a prose → source-line checker is that page's follow-up rather than
this re-anchor's.

## Two claims elsewhere that were false, corrected in place

- `0751-notice-two-moments.md:327` said "that tool exits 0 on this tree". It
  was true on the tree that change landed on and was **false on every tree
  since `368e9e52`** (#982) — 26 DRIFT and exit 1. Corrected in place, wrong
  version visible. **The "every tree" in that correction is itself withdrawn,
  by the sweep below** — the correction overclaimed in the same shape it was
  correcting, which is why the wrong version stays visible here too.
- `0751-capture-encoding.md` §7's 37/6/29/23 figures and its `ValueError` at
  `:601` describe #748's merge. The crash half was wrong (already fixed), the
  figures are a different tree's, and §9's "its own issue" bullet names an issue
  that has now landed. Both corrected in place per the `docs/findings.md` §4a-4d
  pattern, with the original text kept above the correction.

### The sixth move: #1208 re-anchored the pins rather than breaking them

Every claim of "false since" above is measured rather than reasoned, and the
measurement is a sweep: `python3 ec/tools/measure_mark_provenance.py` run at
each of the **130 first-parent commits** in `368e9e52^..origin/main`, one
worktree checkout per commit. **113 red, 17 green**, and the 17 are contiguous:

| from | to | commits | |
|---|---|---|---|
| `368e9e52` (#982, 2026-09-26) | `4f0bcc2f` (#1220) | 65 | red |
| `00836c06` (#1208, 2026-09-28) | `55ded4c1` (#1300) | 17 | **green** |
| `5ad88d8d` (#1292, 2026-09-28) | `ab594a22` (#1450, 2026-09-30) | 48 | red — 28 problems at `5ad88d8d`, 43 at `ab594a22` |

So the sentence was false on **two separate stretches**, not one unbroken run,
and that is this page's own mechanism running the other way: `00836c06` widened
the mark row, moved every line the pins quoted, and re-anchored all 48 of them
in the same change — the tool prints `48 citations resolve at the line quoted,
the row-site join closes both ways` at `00836c06` and again at `55ded4c1`, the
same figure and the same closure this change arrives at. It is the one merge in
the range that fixed the pins instead of breaking them, which is why the green
stretch is the best evidence the rest of this page has rather than a hole in
it: a re-anchor that worked is exactly what the 113 red trees were missing, and
why "false on every tree since" is the one phrasing the sweep rules out. The
two non-universal halves of the withdrawn claim survive re-measurement: the
eleven commits from `84a89d9a` (#771) to `9a3b78d3` all exit 0 and `368e9e52`
is the first red after them.

This is the sixth move in the sequence above and the only one with the sign
flipped, which is what makes it worth naming: the five that moved these pins
were merges that took the code and left the tables behind, and this one took
both. The follow-up is unchanged by it — the thing that would have caught all
six is a gate that runs the tool on the merged tree, not a sharper sentence in
the page.

## Not done, and why

- **`docs/findings.md`.** The issue asks for a pointer there. `CLAUDE.md`
  forbids exactly that edit and `check_findings_frozen.py` is the backstop;
  `docs/findings/INDEX.md` is the index and is regenerated.
- **#741** (`check_page` holding the pages to the tool's output rather than the
  §16a summary) stays open and untouched. `check_page` was already reachable —
  #749's fix to the crash is what made it so, and on `main` it ran and printed
  its three `grade_timer_sweep.py` problems, the 43 above — and this change
  makes it green. It does not answer #741, which is a different question
  about a different claim. Nothing is blocked on it.
- **No live run.** No EC was opened, no capture taken, no register read, no mark
  typed, no Windows box. `windows/tools/` is touched only in line numbers a pin
  table quotes, and `grade_0751_isolation.py` is not edited at all — the drift
  is that other issues moved its lines, and this re-anchors *to* that code.
  **A pin that stopped resolving after this change would mean the claim was
  wrong, not that the reader should be edited to fit the pin.**