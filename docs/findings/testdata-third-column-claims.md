# The third column of the testdata index is now held to the fixtures it names (issue #747)

The write-up for [issue
#747](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/747), which is
about `ec/tools/testdata/README.md`'s **third** column — the description — being
free prose that nothing reads. What this branch adds is **a census, a checker
and a prepared patch**: `ec/tools/check_testdata_row_claims.py` holds an
address a row attributes to its fixture to that fixture, and the two lines
that would put it in the cheap gate are prepared at
`docs/ci/agent-gates-testdata-row-claims.patch` rather than landed, for the
reason that patch's own header gives.

**Until a human lands that patch, no commit runs the check.** What runs today
is `ec/tools/test_check_testdata_row_claims.py`, which `tools/run-tests.sh`
discovers by `find` the moment its file is committed, and which holds the
checker's own refusals.

**None of this is a live test, and none of it is a claim that the fixtures are
right.** It is index/tree agreement over committed files, as
[`testdata-index-check.md`](testdata-index-check.md) is. No capture is opened,
no EC, no firmware image, no laptop.

**Not claimed: that this would have caught #502 or #720.** Both repairs were
to a row's third column, so every check that was green through them is
consistent with this one being green through them too. What those two
repairs changed is in the issues, not in the tree, and neither has been read
back as a diff this tool could have been run over.

> **Correction, 2026-09-26, at the `#964` merge: this page is #747's write-up
> as it was measured on 2026-09-25, and it carries corrections in place since.**
> The rule the corrections below are about — the `another capture's address`
> exemption — was retracted in the tool's own docstring by that merge
> (`ec/tools/check_testdata_row_claims.py:119-127` strikes its own bullet and
> says why) and replaced by a **resolution**: a bare date in a third-column
> sentence is resolved against `evidence/ec-watch/<date>-*` and the sentence's
> literals are held to the files it resolves to, so row 7's two are `checked`
> rather than passed over. That write-up is
> [`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md).
> **Nothing below is edited out of silence**: every superseded figure stays as
> it was measured and the correction sits beside it, per
> [`../findings.md`](../findings.md) §4a-4d. Two of the places below are marked
> as *false now* rather than drifted, because a rule that no longer exists is
> not a figure that moved, and a reader met by the second would otherwise be
> told the `another capture's address` shape was always a live shape.

## The measured census, on this tree, 2026-09-25

```
$ python3 ec/tools/check_testdata_row_claims.py --check
27 table row(s), 17 literal-bearing: 54 literal(s), 28 resolved, 0 missing, 26 unresolved
28 claim(s) checked, 14 claiming row(s), 26 passed over under the six shapes, each of them: not checked, not absent
shapes: capture/window bound 16, denial 3, another capture's address 2, dump-command argument 2, watched-set span 2, firmware code address 1
ec/tools/testdata/README.md: every address claim in the third column agrees with the fixtures its row names
```

> **Correction, 2026-09-26, at the `#964` merge: the block above is a 2026-09-25
> measurement and the merged tree reads this.** The run is unchanged and every
> figure published from it below is re-transcribed from this one; the
> `28 resolved / 26 unresolved`, the `28 claim(s) checked, 14 claiming row(s)`,
> the `26 passed over` and the `another capture's address 2` line all stay
> written above rather than edited out of silence, per §4a-4d.
>
> ```
> $ python3 ec/tools/check_testdata_row_claims.py --check
> 27 table row(s), 17 literal-bearing: 54 literal(s), 30 resolved, 0 missing, 24 unresolved
> 30 claim(s) checked, 15 claiming row(s), 24 passed over under the five shapes and a dated capture that resolves to nothing, each of them: not checked, not absent
> shapes: capture/window bound 16, denial 3, dump-command argument 2, watched-set span 2, firmware code address 1
> dated-capture claims, each held to the captures its date names and never to the row's own fixtures:
>   2026-09-23-* (6 capture(s) under evidence/ec-watch): row 7 0x0F58 resolved, row 7 0x0F5C resolved
> ec/tools/testdata/README.md: every address claim in the third column agrees with the fixtures its row names
> ```
>
> **The five surviving shapes' counts are byte-identical to the block above —
> `16, 3, 2, 2, 1` — and that is the check that the change moved what it was
> supposed to move and nothing else.** What moved is the shape count, six → five,
> and the two claims: `28 resolved / 26 unresolved` → **`30 / 24`**, `28 claim(s)
> checked, 14 claiming row(s)` → **`30, 15`**, `26 passed over` → **24**. The
> dated block is new and is the report line the resolution added; it is where
> `0x0F58`/`0x0F5C` read now.

Twenty-seven rows; **seventeen carry at least one `0xNNNN` literal and ten
carry none**; 54 literals in all. **28 are presence claims** over 14 distinct
addresses — `0x043E 0x044F 0x0743 0x0745 0x0746 0x0751 0x075B 0x0784 0x07C4
0x07C6 0x07D0 0x0F0A 0x0F5D 0x0F5F` — across 14 rows. **26 are not claims**,
in a closed list of six shapes.

> **Correction, 2026-09-26, at the `#964` merge: the two figures this paragraph
> is built on are 30 and 24, over 16 distinct addresses and 15 rows.** The
> paragraph stays as it was measured on 2026-09-25 per §4a-4d. Re-derived off
> `Result.claims` on the merged tree, the 30 presence claims are over **16**
> distinct addresses — the fourteen above plus **`0x0F58` and `0x0F5C`**, row 7's
> two, which the other-capture shape used to pass over and the dated-capture
> resolution now checks — across **15** rows, row 7 being the one that joined.
> **24 are not claims, in a closed list of five shapes and a dated capture that
> resolves to nothing.** `another capture's address` is not among the five; it
> is the retraction two sections down, and the dated capture is the entry that
> replaced it.

**The decisive measurement is that all 28 claims are present in the fixture
their row names today.** The tree is green under the correct rule, and a naive
one is not: with the six shapes removed the run is **red on 4 rows** — five
literals, `0x0700` and `0x07FF` in row 3, `0x07FF` in row 6, `0x0784` in row
23 and `0x0700` in row 25 — and calls **54 of the 54 literals claims where 28
are**. Ten rows carry at least one shape; all ten change verdict when the shape
goes, and four of them go red, the other six being miscounted rather than
failed, because the literals those shapes exempt really are in the files those
rows name. That gap is the tool's whole value, and running the census before
writing the tool is what makes the rule writable rather than guessed.

> **Correction, 2026-09-26, at the `#964` merge: the `red on 4 rows` above is
> unchanged, re-measured rather than carried, and only the shape count in it
> moved.** The mutation is re-run on the merged tree with the **five** shapes
> neutralised — `page_bounds`, `PAGE_WORD`, `span_bounds`, `DENIAL_OBJECT`,
> `DENIAL_ADJUNCT`, `COMMAND` and `code_addresses`, patched one per test in the
> suite's own `test_the_page_range_rule` through
> `test_the_firmware_code_address_rule` — and it is the same verdict: **red on
> 4 rows, five literals**, `0x0700` and `0x07FF` in row 3,
> `0x07FF` in row 6, `0x0784` in row 23 and `0x0700` in row 25, calling **54 of
> the 54 literals claims where 30 are**. The `28` this paragraph counts them
> against is the figure that moved; the four rows and the five literals did not,
> and saying so is the point — a rule removed from one end of the column does
> not change what a naive rule still gets wrong about the rest of it. This is
> the `docs/agent-pipeline.md` item-6 caveat `call_graph.py` records, applied to
> a figure that a shipped run cannot produce.
>
> **One thing did move, and it is the label rather than the verdict: with the
> dated resolution *also* pointed at a capture root with nothing in it, the run
> checks 52 rather than 54**, row 7's two coming back as
> `dated capture not found`, with the same 4 rows and the same 5 missing
> literals either way. So `54 of the 54` is the five-shapes-off figure with the
> dated rule left live, which is what "the six shapes removed" meant on
> 2026-09-25: the shape that used to swallow row 7's two is now the rule that
> produces them.

### ~~The six shapes, and the 26 literals they account for~~

> **Correction, 2026-09-26, at the `#964` merge: this heading is superseded, and
> it is struck rather than edited because a heading is one of the few places
> §4a-4d cannot be satisfied by a trailing blockquote alone — a reader scanning
> the contents sees the title and nothing else.** The `six` and the `26` are
> 2026-09-25's. The section carries the heading beneath this note.

### The five shapes, and the 24 literals they account for

| literals | shape | what it is |
|---|---|---|
| 16 | capture / window bound | `0x0700-0x07FF` "the capture", `0x0700` "the `0x0700` capture", `0x0700` "the whole `0x0700` page" — the swept page, not a byte in it |
| 3 | denial | "**no row at all for** `0x07D4` or `0x07D5`", "one `0x0784` row added, **not by a committed run**" |
| ~~2~~ | ~~another capture's address~~ — **retracted, #964** | row 7's `0x0F58-0x0F5C`, tracked in *the 2026-09-23 power-mode-cycle capture* |
| 2 | dump-command argument | `` `ecrw.py dump 0x0750 0x0010` `` |
| 2 | watched-set span | row 11's ACPI half, `` (`0x07C4`-`0x07D7`) `` — a block, not a byte |
| 1 | firmware code address | row 8's `0x888D`, the §6 handler in the EC image |
| 0 | dated capture not found | a bare date whose `<date>-*` glob is empty: the sentence's literals have no file set to be held to, so they are `unresolved` with the glob in the report line, `not absent`, and not `missing` |

> **Correction, 2026-09-26, at the `#964` merge: the third row is a retraction
> and not a drift, which is why it is struck while the rows around it are
> corrected in prose.** The shape it names no longer exists:
> `ec/tools/check_testdata_row_claims.py:119-127` strikes the same rule out of
> the tool's own docstring, and this table is what a reader arriving from
> `docs/findings.md` §47 lands on. **Those two literals are the ones the
> dated-capture resolution moved onto `checked`** — not "the rule's count
> changed", which is how a drifted row would read. The last row is the entry
> that replaced it and has **0 instances on this tree**, because the one dated
> sentence in the index resolves; it is pinned on a scratch tree instead, by
> `test_a_bare_date_resolving_to_nothing_is_unresolved_and_not_absent`. The
> column as corrected adds up: `16 + 3 + 2 + 2 + 1 = 24`, which is what the run
> prints, plus the dated variant's zero.

**The six overlap, so those six numbers are not six disjoint buckets.** Four
literals are caught by two rules at once: row 3's `0x0700` by both spellings of
the first shape, and `0x0F00` in rows 7, 18 and 25 by a `capture`/`page` bound
— the range spelling in row 7, the page word in rows 18 and 25 — *and* by the
firmware-code filter. So the per-shape counts above do not sum to a measurement
you can get by dropping one rule at a time — dropping the page-boundary range
rule calls 36 of the 54 and dropping the `capture`/`page` word calls 32, while
dropping the whole capture/window shape calls **41**, not the 44 that 28 plus
its 16 would suggest. Only the all-six-off run is the figure quoted above, and
that is the one to re-derive.

> **Correction, 2026-09-26, at the `#964` merge: the three drop figures are 38,
> 34 and 43, and the comparison is 46 rather than 44.** Each was re-measured on
> the merged tree by neutralising one predicate at a time the way the suite
> does, so the `36`, the `32`, the `41` and the `28` stay written above per
> §4a-4d. Dropping the page-boundary range rule alone calls **38** of the 54;
> dropping the `capture`/`page` word alone calls **34**; dropping the whole
> capture/window shape calls **43, not the 46** that 30 plus its 16 would
> suggest. All three moved by exactly the two literals the resolution added, and
> the gap the last figure shows is still three — the same three `0x0F00`s this
> paragraph already names, caught by the code filter as well. **The conclusion
> the paragraph draws is not corrected**: a single shape's drop is not additive,
> and it is still the reason the all-shapes-off run is the one worth quoting.
> Only its name changes, from the all-six-off to the all-shapes-off, and on the
> merged tree that is the five shapes with the dated resolution left live — the
> equivalent of what "all six off" meant here.

The issue named the first five. **The sixth is the census's own** — no
`MOVEMENT`-shaped phrase marks `0x888D` at all, and nothing in the column's
prose says "code"; the only thing that separates it from a claim is that
`ec/annotations/ghidra-functions.csv` holds a row at that address and
`xdata-registers.csv` does not. Filtering against those two is the repo's own
code/data distinction, and it is also why the filter has to be the
*difference*: `0x07D0` is `FUN_CODE_07d0` in the annotation index **and** a
door byte in `registers.yaml`, and it is a claim in two rows.

> **Correction, 2026-09-26, at the `#964` merge: the census's own shape is the
> fifth now, not the sixth, and the sixth entry is the dated capture.** The
> filter did not change shape, it changed ordinal: the entry ahead of it in the
> list was `another capture's address`, and that entry is retracted. So the five
> shapes with instances on this tree are the five the table above now lists, and
> the sixth entry of the shape list is a dated capture that resolves to nothing —
> which has 0 instances in the committed index and so no row in that table. The
> argument this paragraph makes is untouched by the merge: `0x888D` is separated
> from a claim only by `ec/annotations/ghidra-functions.csv` holding a row at
> that address and `xdata-registers.csv` not, and the filter has to be the
> *difference* because `0x07D0` is in both.

### The three rules that took a measurement to write

Each of these was the obvious reading until it was measured against the
committed column, and each is the reason the rule is a rule and not a guess.

**The union, not the file.** The search is across the files a row's first
column resolves to, never per file. `0x075B` occurs **16 times in one** of
`0751-isolation-run-staged/`'s three CSVs and in neither of the other two,
while the row names `0751-isolation-run-staged/*.csv`. A per-file reading
fails a row that is true today. The issue's own second example is the same
discrimination from the other side — `3blocks/` has zero `0x0784` rows and
`3blocks-moved/` has them, which is precisely the difference those two rows
claim.

**No `MOVEMENT` predicate.** `check_capture_claims.py`'s gate does not
transfer: **18 of the 54 literals sit in a sentence carrying none of its
verbs**, and most of those are genuine claims. Row 3's `0x043E`/`0x044F` are
claimed in a sentence whose only movement word ("PWM moves") is in a
*different sentence of the same cell*. The predicate here is a backticked
four-hex-digit literal plus the six shapes — and the *width* is part of it,
because `0x50 -> 0x28`, `0xFD`/`0xC9` and `0xA0`/`0x10` are the values the
dumps and the mark labels carry, and reading them would make the tree red on
the day the tool landed.

> **Correction, 2026-09-26, at the `#964` merge: the predicate is a backticked
> four-hex-digit literal plus the five shapes and the dated-capture
> resolution.** The `six shapes` above is 2026-09-25's and stays written per
> §4a-4d; what changed is not the count of exemptions but what the sixth entry
> *is*, because a sentence naming a dated capture in running prose is now
> **checked** against the files that date resolves to rather than passed over.
> `test_a_bare_date_resolves_and_its_literals_are_the_captures` is the case
> that holds it: a row whose fixture carries neither of the two literals, so an
> implementation that ignored the date and used the row's own files would report
> two misses. The rest of the paragraph is unmoved and is not restated here —
> the width, `0x50 -> 0x28`, `0xFD`/`0xC9` and `0xA0`/`0x10` are why the
> predicate is four hex digits and not a token shape, and the merge touched
> none of that.

**Sentence granularity, and a denial that reads in two directions.** Row 9
carries a claim and a denial in one cell and row 22 carries command arguments
and claims in one, so the cell is split with `units()` — which is imported
from `check_cluster_citations`, so a fix to the splitting logic (issue #273)
lands once for all three tools. The two committed denials are written in
opposite orders: `no row at all for 0x07D4` takes the literals as its object,
and `not by a committed run` denies the clause in front of it. A proximity
window wide enough to reach the second would also reach *forward* over
row 9's `0x0746` — the last address of the inventory the denial follows — and
drop a claim that is true today, so the direction is read off which of the two
spellings matched.

## The refusals, and how they were checked

38 cases. The ones that matter are the **refusals themselves**, which is the
half a check that has quietly started accepting everything would otherwise
hide. Every one of the tool's nine rules is dropped in turn and the committed
tree re-run: each makes the run **check more** — literals it was passing over
become claims, or a claim becomes a `missing` — and each is asserted *against
the run as shipped* rather than against a figure, so a fixture row added to
the index later breaks none of them.

> **Correction, 2026-09-26, at the `#964` merge: the suite is 42 cases, and "each
> makes the run check more" holds for eight of the nine rules rather than for
> all nine.** The `38` stays written above per §4a-4d; the four cases are the
> whole of the difference, three of them rewrites of cases this page already
> had, and
> [`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md)
> §"What the refusals now hold" names which is which.
> `python3 -m unittest discover -s ec/tools -p
> 'test_check_testdata_row_claims.py'` reads `Ran 42 tests` and `OK` on the
> merged tree.
>
> **The ninth rule's direction inverted, and that is the clause the table below
> leans on.** It was the `another capture's address` exemption, whose loosening
> made the run check *more*; it is now the dated-capture resolution, whose
> loosening — pointing the run at a capture root with nothing in it — takes row
> 7's two claims back out, so the run checks two *fewer*.
> `test_the_dated_capture_rule`, in
> `ec/tools/test_check_testdata_row_claims.py`, is the evidence rather than a
> claim made here: it goes through
> `assert_the_rule_costs_less_without` and reads `assertLess`, and that helper is
> kept apart from its `assertGreater` sibling precisely so the sign is legible
> instead of being a special case inside a general assertion. A rule that stops
> changing the answer has stopped mattering whichever way the answer moves.

| the rule, dropped | what the run then does |
|---|---|
| the page-boundary range rule | checks the bounds of every sweep range as bytes; 2 become `missing` |
| the `capture`/`page` word | checks four bare page-aligned addresses as bytes; 1 becomes `missing` (row 25's `0x0700`), and the two `0x0F00`s it also matches are caught by the code-address rule instead |
| the two-token span rule | checks the ends of a watched set as bytes the fixture holds |
| the denial rule | checks the addresses the index says are *not* there; row 23's `0x0784` becomes a `missing` |
| the command rule | checks `0x0750`/`0x0010` as if they were addresses in the file |
| the code-address filter | checks a handler in the EC image as a byte in a capture |
| ~~the other-capture rule~~ — **retracted, #964** | ~~checks the addresses the index attributes to a capture the row does not name~~ |
| the dated-capture resolution | **takes row 7's two claims back out — the run checks two fewer.** Loosening it means pointing the run at a capture root with nothing in it, so the date resolves to nothing and its literals have no file set to be held to |
| the four-hex-digit width | reads the dumps' values and the marks' values as addresses |
| the backticked-only predicate | checks mentions in running prose the index never claimed anything about |

**All nine are caught**, and the table is where the two halves of the suite
meet: only three of them can turn the run *red*, because the literals the
other six exempt genuinely are in the files their rows name — `0x07C4` and
`0x07D7` are in the file row 11 names, `0x0750`/`0x0010` in the dumps row 22
names, `0x888D` in the fixture header row 8 names, and `0x0F58`/`0x0F5C` in
the page row 7's after-dump covers. What dropping those rules does is
*under-report*, which is the property the suite pins, and the suite says so in
the class docstring rather than leaving it to be discovered.

> **Correction, 2026-09-26, at the `#964` merge: "all nine are caught" still
> holds, and two clauses of the reasoning beside it do not.** Three of the rules
> can still turn the run *red* — but out of the **five shapes**, not "the other
> six" of nine, which is what the class docstring of
> `ec/tools/test_check_testdata_row_claims.py` says. What the helper assertions
> enforce is the weaker half of the sentence above, that all nine are caught;
> the three-of-five is the docstring's claim, and the red rows are what a
> mutation demonstrates rather than what a count pins. The `0x0F58`/`0x0F5C`
> clause is **neither drift nor a property of the current suite**: it is the
> justification for the exemption #964 removed, restated as though the
> exemption were still there, which is why it is left
> visible above and struck in meaning here rather than re-worded. Those two
> literals are not excused by the after-dump that used to cover them — they are
> `resolved` against the six files `2026-09-23-*` matches, and
> `test_a_bare_date_resolves_and_its_literals_are_the_captures` builds a case
> whose row's fixture carries neither, so an implementation that went back to
> the row's own files would report two misses.
>
> **What replaced the clause is that the dated capture is now the run's *only*
> red verdict.** `test_a_dated_claim_is_not_also_the_rows_own` is a `missing`
> and `ctrc.report` returns 1 on it, because a dated sentence's literals are
> held to the capture *instead of* the row's own fixtures and never to both —
> which is the one disagreement the tool can raise, and it is the one the
> exemption used to be able to prevent by construction.

Two more refusals are pinned as pairs, each with the near-miss that looks like
it and is still checked: a mid-page range (`0x0F5D-0x0F5F`) is a claim where a
page-aligned one is a page; a one-token range of the same two addresses as the
watched-set span is a range; a page-aligned address nobody calls a capture is
a claim; `restored 0x0751=0x0a` is a mark label and not an `ecrw.py` command;
`not a prediction` is a disclaimer and not a denial; and a **backticked**
`2026-09-23` is a file the comparison is drawn from where a **bare** one is a
capture somewhere else.

> **Correction, 2026-09-26, at the `#964` merge: the pair above is still true,
> and the reason it is true changed from an exemption to a resolution — so the
> clause reads as though the bare case were unchecked when it is resolved and
> checked.** A bare `2026-09-23` is now **resolved** against
> `evidence/ec-watch/<date>-*` and its sentence's literals are held to the six
> files that glob matches: row 7's `0x0F58`/`0x0F5C` are two `resolved` claims in
> the run's dated block, not literals passed over. A backticked date still
> leaves its sentence about the row's own fixture, which is the half of the
> discrimination that has not moved.
> [`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md)
> §"The two near-misses, and why each stays" carries both, and the reason the
> rule is spelled as a regex with lookarounds is the same one it was on
> 2026-09-25: the index writes a *file* in backticks and a *capture* in running
> prose, and only the second is somewhere else.
>
> **The backticked near-miss is load-bearing now in a way it was not.** A
> capture of 2026-09-23 exists beside that case's fixture and does **not** carry
> `0x07C4`/`0x07C6`, so an implementation that read the backticked date as a
> bare one would make both misses instead of passing the sentence over. That is
> why `test_a_backticked_date_is_a_file_the_comparison_is_drawn_from` stayed
> rather than being folded into its sibling, and it is the concrete sense in
> which the #794 correction made this pair harder to get wrong.

The check itself measures **0.05 s** over three runs here, against
`check_testdata_index.py`'s 0.03 s and a cheap tier
`docs/agent-pipeline.md` records at 5.9 s. That is one runner's figure and the
ratio is the point, the caveat `docs/agent-pipeline.md` item 6 records for
`call_graph.py`'s own.

## What is not claimed here, and what the check does not do

- **Row counts, timestamps and mark values.** Row 18's `0x0F0A` row *at*
  12:00:08.500 is a count-and-timestamp claim — decidable in principle, a
  different invariant with a different owner, and not what the issue asks for.
- **That a fixture constructs what its row says.** This asks whether an
  address the row names occurs in a file the row names. Presence is
  **textual** — does the file carry `0xNNNN` anywhere, in any case — so a mark
  label (`restored 0x0751=0x0a`), a dump line (`0780:`) and a change row are
  all how a fixture carries an address, and a fixture that mentions one in a
  comment satisfies the rule. The narrower question, "is there a row with this
  in the `addr` column", is `check_capture_claims.py`'s, over real captures,
  with a different owner. The cost is written down rather than left implied.
- **The rest of the third column.** It is free prose, and the issue says so.
  This is the decidable slice and no more; the tool's docstring lists what is
  not read, the way both sibling tools do.
- **The `0x888D` filter's blind side.** It reads the committed function
  census, so a code address with no annotation row is not filtered by it. Every
  such literal is reported with its reason rather than passed over in silence.
- **Repairing any fixture or row.** Nothing is wrong today. The issue is that
  nothing checked it.
- **Rewriting the third column to be more machine-readable.** That is a design
  call, and it is the route by which a checker starts inventing the thing it
  checks.
- **Live hardware, Windows, or the EC/BIOS/Windows stack.** Nothing here reads
  a register, opens a capture, or touches a machine. No `status:` moves, so
  `ec/annotations/registers.yaml` is not touched at all.
- **Anything in another repository.** The upstream work the mission eventually
  means is a prepared patch and a description committed *here*, for a human to
  submit. This branch opens nothing anywhere.

## Two of the issue's examples are not committed-tree cases

`3blocks/` vs `3blocks-moved/` (0 vs 3 `0x0784` rows) and
`gpu-door-example-quiet.csv` (0 `0x07C4`/`0x07D0` rows) are both real, and
both verified — in the suite, over the fixtures, because **rows 17 and 14 carry
no address literal at all** and the checker reaches neither. They belong in the
suite as fixture assertions rather than as checks over the committed index.
That changes where they are tested, not whether the rule holds.
