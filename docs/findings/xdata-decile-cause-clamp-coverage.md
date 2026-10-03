# The `deciles()` floor had a case on one of its two callers and none on the other (issue #922)

**2026-10-03, issue #922.** #889 put a floor of ten into
[`deciles()`](../../ec/tools/xdata_moved_ranks.py) and pinned it on the helper
and on `across_report`. `cause_report` is the tool's other caller, and its line
is the one the floor's own docstring gives as the reason the floor exists —
two reads on one line, read against each other cell for cell. Nothing held
either read on that line. This adds the cases, and records that the `min()`
beside the ten-cell read cannot bind and that no case can make it bind.

**The four `deciles` call sites, two callers, and the case that holds each.**
This is the census the issue asks for, written down where the next edit to the
file finds it. `grep -n 'deciles(' ec/tools/xdata_moved_ranks.py`:

| call site | caller | held by |
|---|---|---|
| `across_report`, the flipped set's distribution | `across` | #889's case, asserted on the report line |
| `across_report`, the census beside it | `across` | **this branch**, asserted on the report line |
| `cause_report`, the subject rows by size | `cause` | **this branch**, below the floor |
| `cause_report`, the committed rows at the same ranks | `cause` | **this branch**, below the floor and at the floor |

Two callers, and until this branch one caller of the two was held. That was
carried in a prose argument — that the `cause` cells are the concrete evidence
the floor was worth taking — rather than written down as a coverage claim with
an owner per line, which is the shape that goes stale quietly.

**The census row was written down here first holding nothing, and the table is
what found it.** It read "the same case", on the reasoning that #889's `across`
case covers the pair it prints beside. It does not. That case has two clauses,
and neither can see the census line: one looks for the marker on the *flipped
set's* line, and the census is on a line of its own; the other looks for a
stretched ten anywhere in the report, and over that fixture the census is five
rows, so it takes the below-floor rendering and never prints one. Two clauses
that both miss a call site hold no more of it than not checking at all. Both
ways of showing it were run on a scratch copy of the tool, leaving the working
tree untouched: replacing the census read with a raw sorted join, and cutting
it to `deciles(sorted(census_sizes)[:3])` — the first drops the marker, the
second drops the row count and most of the sizes, and **the suite was green
under both**. That is the same defect this write-up holds red on the `cause`
side, applied to the sibling call site, and the write-up's own standard
falsified its own table row.

The row's owner is now the case beside #889's, which selects the census line by
its stripped prefix rather than by a substring — `"the census:"` as a substring
matches the flipped set's line too, which is part of how the gap survived a
read. It goes red under both mutations above and under the pre-#889 body.

## Why the `cause` line is the one that mattered

`cause_report` prints one line per cell carrying **two** reads:

```
    the subject rows by size: <read>   the committed rows at the same ranks: <read>
```

That is the tool's own cell-for-cell comparison — subject sizes against
committed sizes at the same rank — and `deciles()`'s docstring gives it as the
reason the floor is there: "two of these strings are read cell for cell against
each other, which says something only if each cell is a row of its own."

The self-test fixture those cells come from is the D/E pair. Its four cells hold
**1, 2, 2 and 1 keys**, which is what the case asserts and where it asserts it
from — the `cells` the call returns, not this write-up:

```
moved -> intact: 1    moved in both: 2    intact -> moved: 2    intact in both: 1
```

so all eight reads on those four lines are below the floor and render as
`N row(s), too few to cut ten ways: ...`. Every one of them now has a case.

## The two cases, and what each goes red against

Both are asserted **on the report line**, for the reason #889's `across` case
gives: a helper that stopped stretching would still leave a caller free to
print the stretched string itself.

- **Below the floor**, over the D/E fixture: both reads carry the marker,
  counted rather than tested with `in`; the two reads name the **same** row
  count, and that count is the cell's own key count; the sizes behind each
  marker are integers in non-decreasing order; and neither `1 1 1 1 1 1 1 1 1 1`
  nor `2 2 2 2 2 2 2 2 2 2` appears on any line of the report.
- **At the floor**, over a fixture of its own: ten clusters whose guard-off row
  in H differs and in I does not, so all ten land in one flipped cell and its
  line carries two ten-cell reads, neither marked, each holding ten numbers in
  order.

"Both columns marked, both carrying the same row count" is read as an
**invariant**, not a marker count: at `n == 10` nothing carries the marker, so
"marked" cannot mean the marker there. The property is that the two reads are
always in the **same state**, asserted in both directions — below the floor
(both marked, same `N`) and at it (both ten-cell, neither marked, same width).
One column marked and one not is worse for a cell-for-cell reader than either
state alone, which is the issue's own reason for the case.

## The clamp, and why no case can make it bind

`min(len(ordered) - 1, ...)` on the ten-cell read **cannot bind**, and this is
arithmetic rather than a guess:

- `deciles` returns before reaching the clamp below ten rows — that is the floor.
- For `n >= 10` the unclamped cut obeys `(n * 9) // 10 <= n - 1`, because
  `9n <= 10n - 10` is `n >= 10`.

So deleting the clamp changes **no output the tool can produce**. That was
measured rather than argued: the mutation was applied to a scratch copy of the
tool and the suite run, and **every case stayed green**. The write-up records
that as the proof the clamp is inert, not as a gap.

What the two new clamp cases *do* hold is the property the docstring states,
over a range of `n` rather than at one input (at `n = 10` the clamped and
unclamped forms coincide, so one input cannot tell them apart):

- ten cells, ten **distinct** ranks — the docstring's "one whole row per cell
  with none doubled up" — in non-decreasing order, each cell equal to the value
  at rank `(n * i) // 10`, which is the assertion that the read *is* the
  unclamped formula;
- the bound itself, `max((n * i) // 10 for i in range(10)) <= n - 1` for every
  `n >= 10`, so the property is held as arithmetic over the class.

**The mutations, and which case each one turns red.** Each was applied to a
scratch copy of the tool and the suite run against it; the working tree was
never mutated.

| mutation | result |
|---|---|
| the pre-#889 body — `deciles` with no floor | **RED** — this branch's below-floor case and its census case, #889's `across` case, and the two helper cases |
| one column marked, the other not | **RED** — the below-floor case |
| the rank formula interpolated (`(n * i + 5) // 10`) | **RED** — the ten-cell case |
| the rank formula cut to `/ 9`, so cells collide | **RED** — the ten-cell case |
| **`min(len(ordered) - 1, ...)` deleted** | **GREEN** — every case, as the arithmetic above says it must be |
| `cause`'s second read stops going through `deciles` and prints the raw per-row sizes instead | **RED** — the below-floor case only |
| `cause`'s second read removed from the line | **RED** — both `cause` cases |
| `across`'s census read stops going through `deciles` and prints the raw sorted sizes instead | **RED** — the census case, and only it |
| `across`'s census read cut to a three-row set (`deciles(sorted(census_sizes)[:3])`) | **RED** — the census case, and only it |

The last two rows are what the census row's original owner could not have
caught. Both were run before the census case existed and the suite was green
under each; both were re-run after it and each turns that one case red, which
is the property a row in the table above is supposed to have.

The last row is the finding, and the two above it are where it stops. The
issue asked for a case that goes red against a deletion of the clamp; that is
not reachable, and this is the recorded reason rather than a claim that one was
built. The two clamp cases are red against the mutations that *can* move the
line's behaviour, which is what makes them cases rather than assertions of
intent.

**The second read is a weaker hold than the row above it, and the reason is the
same arithmetic.** Over exactly ten rows `deciles` returns the sorted set
itself — the existing case on `deciles(range(1, 11))` says so — so a second
read that printed the sizes directly, in order, over ten rows is not something
the at-the-floor case can tell from the real one. Only removing the read
outright reds both `cause` cases, and that is the degenerate form: an empty
column is visible without any case. The below-floor case catches the
interesting mutation, because over a cell of one or two rows a direct print
loses the marker and the row count that `deciles` supplies, and that is what
its two reads are compared on.

## The re-run, and that no published figure moved

`cause` re-run on the committed pair rather than inheriting #889's
measurement. The guard-off regeneration is `xdata_register_map.py
--no-eq-guard` over the committed tree and over `e169a0e4` (which was taken
with `git archive`, writing only to `/tmp`), and `cause` is then run over both
pairs. The four `the subject rows by size:` lines, as printed:

```
the subject rows by size: 1 1 1 1 4 4 4 4 5 7   the committed rows at the same ranks: 1 1 1 1 4 4 4 4 5 6
the subject rows by size: 1 1 1 1 1 1 1 1 2 3   the committed rows at the same ranks: 1 1 1 1 1 1 1 1 2 3
the subject rows by size: 1 1 2 2 2 2 2 2 2 2   the committed rows at the same ranks: 1 1 2 2 2 2 2 2 2 2
the subject rows by size: 1 1 2 2 3 3 3 4 6 9   the committed rows at the same ranks: 1 1 2 2 3 3 3 4 6 9
```

over cells of **71, 266, 23 and 40 keys**. Every read is over ten rows, so
every one is a ten-cell read, and **no published figure moves**: each line is
byte-identical to what #889 recorded, which is what "the published figures did
not move" means here.

## The pins, and one that was already stale

The markdown line-pins into this tool, from
`grep -rno 'xdata_moved_ranks\.py:[0-9-]*' --include=*.md .`. Each row names
the citing file and **what it claims**, rather than repeating the numeral it
carries — a numeral written here is a pin this branch would be adding, which is
the thing the next paragraph says it does not do:

| citing file | what it claims | state before this branch |
|---|---|---|
| [`xdata-write-direction-correction.md`](xdata-write-direction-correction.md) §"What the code does now" | the `write_movement()` helper, the `pair_report` block, and the span of the four `write_movement` cases | **all three already stale**, see below |
| [`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md) | the `deciles` definition | **already stale**, see below |
| [`xdata-moved-ranks-pin-decisions.md`](xdata-moved-ranks-pin-decisions.md) | the same targets, plus ones this branch does not touch | quoted history and §4a-4d records; see that file's own decisions |
| [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md) | the same targets, plus `swept_report`'s | quoted history and a §4a-4d record; see that file's own decisions |

**The pins that were already stale are recorded here and left where they are.**
`deciles` and `write_movement()` have both moved since the pins naming them
were written, so those two pins — and the four-cases span in
`xdata-write-direction-correction.md`, which was already stale before this
branch — no longer name the line they are cited for. `f271c1c2` is the commit
on which each of those three was correct; that is the tree to read them against
rather than this one.

**This branch widens that gap rather than opening it, and does not close it
either.** Its insertion regions are inside `self_test()`, above the §6a block
and below it, so the block moves down by the length of what was added above it.
Repointing the span here would mean asserting a new value that is true only
until the next merge — which is the same defect the stale pin already has, and
it would be an edit to another issue's file for a drift this change did not
originate. The pins are named here so the next edit to this file finds them;
re-deriving all of them together is its own change.

**No new pin is added by this branch**, and that is now true of the prose above
as well as of the tool: `deciles` and `write_movement()` are named, the new
cases name the report lines' own strings, and the one figure this write-up does
carry — the rank the ten-cell formula names — is arithmetic rather than a line
into a file.

## What this is not

**No hardware, and nothing deferred to a human at the machine.** No firmware
image is opened, no register is read back, and no laptop, EC or Windows machine
is involved. Both censuses the re-run reads are committed files plus a
regeneration into `/tmp`, and every figure above is either the output of a
command printed beside it or a value read out of the `cells` the tool returns.

**No change to the tool's behaviour.** `deciles`, `across_report` and
`cause_report` are byte-identical; the diff is cases inside `self_test()`.
Nothing here moves a register status, and no gate was edited or relaxed —
`--self-test` is still run by hand, which is the same gap
[`disasm8051-self-test-gate.md`](disasm8051-self-test-gate.md) documents for
`disasm8051.py` and is not this issue's to close.