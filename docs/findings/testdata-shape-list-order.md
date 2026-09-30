# One order named once, and the printed line that carries none (issue #987)

The write-up for [issue
#987](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/987), which is
about the *order* of the closed shape list in
`ec/tools/check_testdata_row_claims.py` where the *count* had already been
settled: #977 corrected the figures in the write-up's shape table and left
three lists describing the same reasons in three orders. What this branch adds
is **one order named once, in `reason_for()`, where it was already
load-bearing**, the two lists that can follow it brought into line with it, an
explicit statement that the third cannot, two suite cases relating them **as
relations rather than counts**, and one correction in place.

**Nothing here is a live test, and no capture is opened.** It is a docstring, a
comment and two cases over committed text — the same class of claim as
[`testdata-row-claims-multi-date-sentence.md`](testdata-row-claims-multi-date-sentence.md).
No EC, no firmware image, no laptop, and no row of
`ec/tools/testdata/README.md` is edited in either column.

## What the issue says, and what this tree has

The issue was filed against an older tree, and **five of its measurements have
moved since**. They are recorded here rather than restated silently, because a
reader comparing the issue to the shipped run needs to know why the figures do
not match; the wrong ones stay written in the issue, which is not this
repository's file to edit.

| the issue says | this tree has |
|---|---|
| six reason strings | **eight** — `SHAPES`; #973 and #979 added `dated capture has no addr column` and `two dated captures in one sentence` |
| `reason_for()` reads `denial` before `watched-set span` | **already the other way round** — `reason_for()` reads `watched-set span` first, and so does the docstring. One of the issue's two order complaints was already fixed when it was filed |
| `by_shape` is a `Counter`, so the printed line keeps first-seen order, which is a property of the index's row order | **already changed** — `main()` sorts by `(-count, name)`, so the printed order is a function of the counts and the names |
| `--check` prints `16, 3, 2, 2, 1` | prints **`17, 3, 2, 2, 1`** — `capture/window bound` grew by one |
| the 42-case suite | see `bash tools/run-tests.sh`'s last line for the count; the figure is not written down here, per the rule in `CLAUDE.md` about a total every merge has to edit |
| the table at `:145-153`, the correction at `:205-209` | the table is at `:173-181`, the correction at `:233-243` — the write-up has been edited under it since |

So **the defect option (a) wanted removed is already gone**: the printed order
is no longer a function of the index's row order, which was the part of the
issue that mattered for reproducibility. This branch does not re-do it.

## The three orders, as they stood

Measured on the tree this branch starts from, with the code that decides each.

**One, the precedence order.** `reason_for()`'s return order, and it is
load-bearing: first match wins, so the order *is* the rule rather than a
presentational choice. Its multi-date-first position is argued in the
function's own docstring — a sentence naming two dates is a property of the
sentence as a whole, and it genuinely competes with the one reason that reads
the file set. `SHAPES` copies this order, and said so.

**Two, the docstring's bullets.** These restate each reason in prose. They
diverged from the precedence order at exactly one position:
`two dated captures in one sentence` was **first** in `reason_for()` and
**last** in the bullets. The other seven of eight agreed. This is the
disagreement the issue found, and it is real.

**Three, the printed `shapes:` line.** Sorted by count descending, then by
name. It is a *transcript of one run's output*, which is what the write-up's
table at `:173-181` is, and why the two belong in the same order.

And a fourth, which the issue did not name and which is the reason the
correction went where it did: the table at `:173-181` is a **transcript of the
printed line**, not a rendering of the precedence order. It is count-descending
because that is what the run printed.

## The decision

**The two lists that can follow the precedence order now do; the printed line
is explicitly marked as carrying no ordinal, and is not re-sorted.**

- The docstring's bullets were put into `reason_for()`'s order, and the
  sentence that said the two copies were "checked by the eye rather than by a
  comparison" — load-bearing prose about the status quo — now says they are
  compared.
- `SHAPES`' comment deferred the reconciliation to this issue by name
  ("reconciling them is issue #987's ground, not this constant's"). That
  deferral is what this discharges, so it is gone rather than left pointing at
  an open issue.
- The `shapes:` print is annotated: count-descending then alphabetical,
  deterministic, **not** the precedence order, and carrying no ordinal.

**Why the printed line and the table were left alone.** Reordering the table
into precedence order would break the correspondence with the line it
transcribes, which is the thing that makes it checkable at all. Re-sorting the
printed line would churn every transcribed `shapes:` line under `docs/findings/`
for no gain, and count-descending is the more readable order in a report.

**The residual is one sentence: the printed line carries no ordinal, and no
write-up may cite it as a list.** That is now in the tool's docstring, at the
print, and in the correction below.

## The specific sentence, corrected in place

`testdata-third-column-claims.md:236` reads "the entry ahead of it in the list
was `another capture's address`". In the table it cites, the row ahead of
`firmware code address` (`:180`) is `watched-set span` (`:179`);
`another capture's address` is at `:177`, two rows up, with
`dump-command argument` (`:178`) between them. The issue's reading of the table
is exact.

**The issue's own explanation of the sentence does not hold, and this is
checkable rather than asserted.** It says the sentence "is true of the tool's
pre-#964 docstring ordering, where the struck other-capture bullet sat after
the `0x888D` bullet". The pre-`#964` docstring *is* readable in this checkout
(`git show 26e970d5^:ec/tools/check_testdata_row_claims.py`), and its six
bullets ran `a capture or window bound`, `a watched-set span`, `a denial`,
`a dump-command argument`, `a firmware code address`,
`a another capture's address` — so the struck bullet sat **last**, and the
entry ahead of `a firmware code address` was `a dump-command argument`, not
the other-capture bullet. Under that ordering the sentence is wrong in the
other direction: it names a neighbour that was behind, not ahead. So the
sentence is not true of the table it sits beside **or** of the pre-`#964
docstring it is excused by, and the correction says only what the table shows.

The pre-`#964` reading is a measurement over a reachable revision rather than
a report, and it is recorded as one: `26e970d5` is in this history and
`git show 26e970d5^:ec/tools/check_testdata_row_claims.py` reproduces it. Had
the revision not been reachable, the correction would have named the table and
said the pre-`#964` ordering was unverified — the same rule as everywhere else
here, that not found by this method is not absent.

The correction is **in place**, beside the sentence, per `docs/findings.md`
§4a-4d: the wrong version stays written and the correction is dated beside it.
The *ordinal* it supports is untouched — `firmware code address` is fifth
among the live rows either way, and `another capture's address` is retracted
either way.

## Two cases, and why they are relations

Both are in `ec/tools/test_check_testdata_row_claims.py`, and both assert a
**relation** rather than a count of the tree. A count here is a value every
merge has to edit — the trap `CLAUDE.md` records and
`check_pin_table_by_cited_file.py` fell into — so an added fixture row or a
new shape must break these by *name*, or not at all.

1. **`test_the_docstring_bullets_are_shapes_in_order`** parses the module
   docstring for the ``  * `reason` -- `` bullets and asserts the *sequence*
   equals `list(SHAPES)`. The pattern is anchored on the opener rather than the
   backticked name, because the docstring's other bullet list opens
   ``  * *italic* `` and a looser pattern would read prose that is not
   claiming to be a shape. A set comparison could not see a reordering at all,
   which is why this is a sequence.
2. **`test_the_printed_shapes_line_carries_no_ordinal`** reads the names off
   `main()`'s own stdout — not off a rebuilt copy of the sort beside it, which
   would agree with the print for as long as nobody changed the print — driven
   from a scratch `Result` holding one instance of every reason.

**The direction deliberately not asserted in the second case is equality.** A
reason with no instance is absent from the line rather than printed as a zero,
so the bullets are a *superset* of what a run can print, and asserting equality
would fail on the first shape nothing exercises. The case asserts the subset
and states the superset, which is the direction the issue asked for.

Both were checked by mutation, in both directions: reordering one bullet fails
the first and names the two that disagree, and dropping a bullet from the
docstring fails both and names the reason no bullet has.

## The two count collisions the issue also listed, and did not fix

`check_testdata_row_claims.py` carried two phrases naming a figure of six —
"a **sixth** shape appearing in the tree is a change to this docstring" and
"The **six** in a fixed order" in `reason_for()`'s docstring. **Both are gone
from this tree**, removed by #983 when the tree reached seven; the phrases are
recorded here as **already fixed rather than open**, and no edit in this branch
makes either true or false.

That is a change from the plan this branch was written against, which listed
them as open. It was written against a reading of the issue's line numbers
rather than of the file, and the file is what settles it.

## Not done, deliberately

- **No `verdict` column on either table.** `check_doc_figure_pins.py` declines
  both today precisely because neither has one, and its own docstring gives the
  reason: a columnless table "lets a correction block quote a superseded
  classification verbatim without the tool auditing the wrong version." Both
  tables carry struck rows, so adding the column would pull a retracted row
  into a figure-pinning audit — separate work, and it would likely go red.
- **No change to the rules, the counts, `DATED_REFUSALS`, `SHAPE_LABEL`, or
  `no_column_reason()`'s position.** This is an ordering-and-correction change.
  `reason_for()`'s own return order is *kept*, not reordered: it is
  load-bearing and its multi-date-first position is argued in its docstring.
- **No live run, and nothing deferred to one.** Nothing here needs the
  machine, so there is no hardware step to hand to a human.
- **Nothing opened in another repository.** This is repo-internal: a
  docstring, a comment, two cases, a correction and this file.
