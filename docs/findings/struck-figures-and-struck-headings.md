# `~~` is a retraction: a struck figure declines, and a struck heading is not a section

`docs/findings.md` §4a-4d asks for a wrong conclusion to stay written with its
correction beside it. It says nothing about what a **checker** should do when it
reaches one, and the two are not the same question: leaving the figure on the
page is what the convention wants, and leaving it *in the tool's reach* is how a
reader gets handed a number the page withdrew.

This is that second question, for `~~`, in the two places
`ec/tools/check_doc_figure_pins.py` reads it.

## The two readers, and what each did

The tool reads a page in two places a `~~` can reach it.

**A struck first cell.** `MARKUP` is `re.compile(r"[`*]")` — backticks and
asterisks, not tildes — and `figures()` strips through it before any number is
read. `FIGURE` guards a digit against `[0-9A-Za-z_.]` and `~` is not in that
set, so nothing stopped the run:

```
>>> cdfp.figures("~~2~~")
([2], None)
>>> cdfp.figures("~~2~~ — **retracted, #964**")
([2], None)
>>> cdfp.figures("~~2~~ (was 2)")
([2, 2], None)
```

The third is the one that was not in the issue and is the sharper defect. It is
the same retraction written with the superseded value repeated beside it, and it
counted **twice** — a figure and its own correction, as two figures.

**A struck heading.** `HEADING` matches `^(#{2,6})\s+(.*)$`, and the strike is
inside the text, so a struck heading was still a section. Asking for one on
`testdata-third-column-claims.md` returned a body of **the heading and the
correction blockquote under it, and nothing else** — because the live `###`
heading that replaced it is at the same level and terminates it. So the run
measured a stub and then said so: it reported that the section held no verdict
table, which is true of the stub and not of what the reader asked for. That is
the failure this tool exists to prevent, one level up from where it usually
shows up — a confident run over text nobody meant to measure.

**The two halves are not equally exercised, and it is worth saying which is
which.** The struck heading is reachable today: `--section "six shapes"` on that
page reaches `section()` before any table is parsed, so the run above happens on
a committed page with no `verdict` column anywhere in sight. The struck *cell* is
not reachable today — reading one needs a verdict table, and the struck cells in
the corpus sit in tables without one, so that half is prevention and the
"not claimed" note below is what it is worth. The rule is written once because a
retraction should mean one thing; it is not evidence that the corpus is full of
them.

## What each does now

| shape | before | after |
|---|---|---|
| struck first cell | measured as a live figure | declines, with the reason printed |
| partly-struck cell | counted the figure twice | declines |
| struck heading | read as a section: the heading and its correction note, no table | refused, naming the live heading below it |

Both refusals are the *decline* direction rather than the *document it* one, and
that was the choice. The alternative — recording in the docstring that this
method reads `~~` as live — makes every future struck cell in a table a silent
trap, and it points the page at the tool rather than the tool at the page. A
decline is already this tool's answer to a shape it declines to read, it is
counted and printed with its reason, and it never fails the run: a correct page
stays green, which is the property the whole `not read by this method` verdict
exists to keep.

## The tempting implementation, and why it fails in the wrong direction

The obvious way to stop a struck figure being read is to add `~` to `MARKUP`.
**Do not.** That regex is also how `verdict_column()` reads a header and how
`marking()` reads a verdict cell, so a `~~held~~` would strip to `held` and a
**retracted verdict would become a live marking** — the correction silently
turning back into a claim, which is the exact failure §4a-4d exists to prevent,
reached from the opposite direction.

The strike is therefore detected on its own (`STRIKE`), and only where a figure
is read. `test_a_retracted_verdict_is_not_read_as_a_live_marking` is the case
that holds the trap shut.

The pair matters too: `STRIKE` matches `~~[^~]+~~`, so a lone `~` is two
characters of prose and the cell is read normally. Matching the single tilde
would decline a figure for its spelling.

## The struck-heading refusal has to compose with ambiguity

Three behaviours, and the second is the one that is easy to break while fixing
the first.

- `six shapes` names the struck heading alone → **refused as struck**, naming
  the live heading at the same level beneath it.
- `shapes` names *both* → **still refused as ambiguous**, because a filter that
  dropped struck headings from the match would make this token resolve to the
  live heading, which is the guess the ambiguity rule exists to prevent.
- `five shapes` names the live one → **reads normally**, as before.

The refusal names the replacement by *level*, not by the token. A retraction
rewrites a heading's figures as well as its title, so the live heading beside
`### ~~The six shapes, and the 26 literals~~` reads `### The five shapes, and the
24 literals` and shares no word with the token that found the struck one —
naming the token's next match would send the reader to a heading that is not
there.

## What this does not fix

**A struck row's verdict marking is still not compared.** A declined row's
marking is never compared — that is what declining means — so a verdict table
whose struck row is marked `held` passes silently, and the decline reports only
that the first cell was not read.

This is stated in the tool's docstring as a limit and deliberately not changed
here. Reporting a declined row's marking is a new failure mode rather than a
fix: whether a struck row *should* still be asserting anything is a separate
decision about what a declined row claims, and nothing in the corpus answers it
yet. The struck cells in the corpus sit in tables with no `verdict`
column, which this tool skips, so the question has not arisen on a committed
page and there is no observation to design a rule against. It is the natural
follow-up.

**The prose `~~` sites.** This tool reads first cells of table rows and
headings, and nothing else, so every struck span in running prose is outside its
reach and is unchanged by this.

## The page that carries both shapes

`testdata-third-column-claims.md` carries both — a struck first cell and a
struck heading — and its own column depends on the distinction between a
retracted figure and a live one, which is what made the two worth settling
together. **That page's figures are not restated here**, and neither are they
restated there: the per-shape counts are the checker's output
(`python3 ec/tools/check_testdata_row_claims.py --check`), and the column sums
to what that run prints. A dated note beside the table once recorded what moved
between two merges; it was removed rather than corrected, because a count of
the index's own rows is out of date at the next merge and the line carrying it
is one every other open branch edits too. The rule for the struck cell is
here; the arithmetic is the command's.

## What is not claimed here

- **That any page was mismeasured by this.** The struck cells in the corpus sit
  in tables with no `verdict` column, which this tool skips, so no figure was
  ever summed from them. What was wrong was that the tool that *would* do the
  summing could not tell a struck figure from a live one. That is the gap this
  closes, and it is a smaller claim than "the figures were wrong".
- **Any count of `~~` sites in the corpus.** The census moves on every merge and
  the rule does not, so the rule is what is written here.
- **Anything about the EC, the BIOS, the Windows stack or the driver.** Nothing
  here reads a register, opens a capture or touches a machine. This is the
  documentation-checker layer, and it moves no component of the stack.