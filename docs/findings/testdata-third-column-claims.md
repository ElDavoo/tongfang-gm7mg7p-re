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

## The measured census, on this tree, 2026-09-25

```
$ python3 ec/tools/check_testdata_row_claims.py --check
27 table row(s), 17 literal-bearing: 54 literal(s), 28 resolved, 0 missing, 26 unresolved
28 claim(s) checked, 14 claiming row(s), 26 passed over under the six shapes, each of them: not checked, not absent
shapes: capture/window bound 16, denial 3, another capture's address 2, dump-command argument 2, watched-set span 2, firmware code address 1
ec/tools/testdata/README.md: every address claim in the third column agrees with the fixtures its row names
```

Twenty-seven rows; **seventeen carry at least one `0xNNNN` literal and ten
carry none**; 54 literals in all. **28 are presence claims** over 14 distinct
addresses — `0x043E 0x044F 0x0743 0x0745 0x0746 0x0751 0x075B 0x0784 0x07C4
0x07C6 0x07D0 0x0F0A 0x0F5D 0x0F5F` — across 14 rows. **26 are not claims**,
in a closed list of six shapes.

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

### The six shapes, and the 26 literals they account for

| literals | shape | what it is |
|---|---|---|
| 16 | capture / window bound | `0x0700-0x07FF` "the capture", `0x0700` "the `0x0700` capture", `0x0700` "the whole `0x0700` page" — the swept page, not a byte in it |
| 3 | denial | "**no row at all for** `0x07D4` or `0x07D5`", "one `0x0784` row added, **not by a committed run**" |
| 2 | another capture's address | row 7's `0x0F58-0x0F5C`, tracked in *the 2026-09-23 power-mode-cycle capture* |
| 2 | dump-command argument | `` `ecrw.py dump 0x0750 0x0010` `` |
| 2 | watched-set span | row 11's ACPI half, `` (`0x07C4`-`0x07D7`) `` — a block, not a byte |
| 1 | firmware code address | row 8's `0x888D`, the §6 handler in the EC image |

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

The issue named the first five. **The sixth is the census's own** — no
`MOVEMENT`-shaped phrase marks `0x888D` at all, and nothing in the column's
prose says "code"; the only thing that separates it from a claim is that
`ec/annotations/ghidra-functions.csv` holds a row at that address and
`xdata-registers.csv` does not. Filtering against those two is the repo's own
code/data distinction, and it is also why the filter has to be the
*difference*: `0x07D0` is `FUN_CODE_07d0` in the annotation index **and** a
door byte in `registers.yaml`, and it is a claim in two rows.

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

| the rule, dropped | what the run then does |
|---|---|
| the page-boundary range rule | checks the bounds of every sweep range as bytes; 2 become `missing` |
| the `capture`/`page` word | checks four bare page-aligned addresses as bytes; 1 becomes `missing` (row 25's `0x0700`), and the two `0x0F00`s it also matches are caught by the code-address rule instead |
| the two-token span rule | checks the ends of a watched set as bytes the fixture holds |
| the denial rule | checks the addresses the index says are *not* there; row 23's `0x0784` becomes a `missing` |
| the command rule | checks `0x0750`/`0x0010` as if they were addresses in the file |
| the code-address filter | checks a handler in the EC image as a byte in a capture |
| the other-capture rule | checks the addresses the index attributes to a capture the row does not name |
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

Two more refusals are pinned as pairs, each with the near-miss that looks like
it and is still checked: a mid-page range (`0x0F5D-0x0F5F`) is a claim where a
page-aligned one is a page; a one-token range of the same two addresses as the
watched-set span is a range; a page-aligned address nobody calls a capture is
a claim; `restored 0x0751=0x0a` is a mark label and not an `ecrw.py` command;
`not a prediction` is a disclaimer and not a denial; and a **backticked**
`2026-09-23` is a file the comparison is drawn from where a **bare** one is a
capture somewhere else.

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
