# Frames the export nests inside its own functions (issue #622)

`docs/findings/named-without-a-row.md` §8 item 2 counted, by hand, the frames
that sit inside functions the export had already framed, and found two. It was
right about one of them and wrong about the other, and two was not the
population. This is the tool that measures the population instead:

```
python3 ec/tools/nested_frame_census.py --check
python3 ec/tools/nested_frame_census.py --self-test
```

Every input is a committed file — `ec/decompiled/index.csv`, the `.asm` listings
under it, `ec/annotations/ghidra-functions.csv` and
`ec/firmware/GMxMGxx_11.800` (SHA-256 `158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`).
No Ghidra run, no scratch project, no hardware, no Windows: no register was read
and no machine was observed. The tool writes nothing.

**There is no standing figure in this file.** Every number below is a
transcript of one run of the command above, taken on this branch over `2e7e29a8`
and the files this change adds, and quoted rather than transcribed. The
population is whatever that command prints on the tree you run it on. That is
deliberate and it is the repository's rule, not a hedge: a count written here as
a fact of the export is a value every merge that adds a row has to come back and
correct, and the last one this issue counted by hand is a figure that has already
moved once between the issue text and the measurement. `--self-test` pins
**claims** — these named addresses, nested in these containers, with these spans
— and never a count of the tree.

## 1. The predicate, and the one it is not

"Contained" is ambiguous over this export, and the two readings do not agree: a
reader who assumed the other one is wrong about the four rows the next paragraph
is about, and right about the rest. Both are measured and neither is presented
as *the* number:

- **address-inside-a-listing** — this row's own **address** falls inside another
  row's committed listing span, in the **same program**. This is the reading
  §8's own worked examples take (`common 0x65A6` "holds" `0x6209`), and it is
  the population the report leads with.
- **span-inside-a-listing** — this row's own **span** sits wholly inside
  another's. That is what the phrase "contained" literally says, and it is a
  smaller set.

The two differ, and the difference is not a rounding: four rows are in the first
and not the second, and each of the four is a shape the second reading cannot
represent. Two of them have **a listing that runs past the container's end**, so
the two overlap without one holding the other — and two **nest in each other**,
which §3 is about. A
container's span reaching an address is what "contains" has to mean for the
first reading to be a question at all; a reader told a row is "contained" and
not told which of the two was meant cannot tell an overlap from a nest.

Per program and per `seed_basis`, from the run below:

```
  program  rows      edges     same-addr opens-below
  bank0    21        21        18        3
  bank1    17        17        17        0
  common   27        34        20        14
  pd       4         4         0         4

  seed_basis   rows      edges     backed
  annotation   37        37        37
  auto         15        21        0
  call-target  17        18        1
```

The `rows` column is rows; the `edges` column is larger than it because "the
container" is not always a single row (§3). `backed` is
`second_copy_census.is_backed()` — whether a `ghidra-functions.csv` row stands
behind the index row — and it is **not** `seed_basis`. A `call-target` row can
be backed and an `annotation` row need not be one, and the drop-or-keep question
below is a question about the CSV rather than about how the export found the
frame.

## 2. The two causes, and the line between them

A row's address being inside another row's listing is one measurement and two
different causes, and the tool names them for what was measured:

- **`same-address`** — the container's listing opens exactly at its own address,
  so the container really does frame the bytes it is reported as containing.
  `bank0 0x8FDB` `state_0817_fallthrough` (listed `0x8FDB`-`0x903F`) is the
  clearest case: nine rows sit inside it, from `0x9000 ljmp_703d` to
  `0x902A write_2_to_0817`, and its own entry point is the first byte of its own
  listing.
- **`listing-opens-below-address`** — `span[0] < container_addr`. The container's
  listing reaches *backwards* past its own entry point, so part of the
  "containment" is a property of how far the listing extends rather than of
  nesting. `common 0x65A6` `FUN_CODE_65a6` is listed `0x60ED`-`0x65A8` and holds
  five; `pd 0x4D6F` `dispatch_case_06` is listed `0x4A12`-`0x4E59` and holds
  four, and every row in `pd` comes through this bucket.

The second bucket exists because `row_span()` returns a listing's **first
instruction** and not the row's own address — which is why `listing_bytes()` in
`second_copy_census.py` already has to guard for a listing that "opens
somewhere else", returning nothing rather than the bytes at the row's address.
That guard is what this bucket measures. It does **not** claim the container
fails to frame those bytes: `common 0x65A6` is a real Ghidra function, its
listing is a real listing, and what the bucket records is that the listing's left
edge is not the function's entry point.

The two are a **closed** vocabulary. A third shape — a container whose listing
opens *above* its own address — is reported by `failures()` rather than filed
under one of the two. On the walk as it stands that shape cannot arise (a span
covering an address cannot start above it), and the guard is there so a change to
the walk which made it reachable would be named rather than silently mislabelled.

## 3. "The container" is not always a single row

`common 0x6A02` `FUN_CODE_6a02` is listed `0x6A02`-`0x6F5D`, and `common 0x6D46`
`FUN_CODE_6d46` is listed `0x67EC`-`0x6D69`. Each address falls inside the
other's span, neither span contains the other, one listing opens at its own
entry point and the other reaches back below it. **Each address is therefore
held by a container that is itself held**, and the report is an **edge set**
rather than a row-to-container map for exactly this reason.

Seven rows in the run above carry two containers each: five that sit inside two
*different* Ghidra frames — `common 0x6A02` and `common 0x6D46` together hold
`0x6B94`, `0x6BAE`, `0x6BFF`, `0x6C70` and `0x6C97` — and two more that `common
0x60C2` and `common 0x65A6` hold between them, `0x6100` and `0x6116`. The
mutually nested pair above is **not** among the seven: each of `0x6A02` and
`0x6D46` has exactly one container, and it is the other one, so neither can be
named the outer frame. In **every one of the seven the two containers fall in
different buckets**, which is what makes the split a partition of the *edges*
and not of the rows: a row-level bucket would have to pick one and be wrong
about the other. A fixture in `--self-test` pins the mutual pair without
depending on the committed tree keeping it.

## 4. `pd 0x9C4D`, corrected

§8 item 2 said `pd 0x9C4D` sat inside `read_xdata_to_r6_set_dptr_069a`. It does
not. `pd 0x9C45 read_xdata_to_r6_set_dptr_069a` is listed `0x9C45`-`0x9C4C` — it
**ends** the byte before `0x9C4D`, and the frame at `0x9C4D` begins the next
statement. The tool's verdict is `after-a-function`, the shape §5 of
[`named-without-a-row.md`](named-without-a-row.md) already uses for
`common 0x1207`, and the row is **not** nested in anything.

That row is `seed_basis=annotation` — it carries a name `call_10bc` and a
`ghidra-functions.csv` row from issue #489 — and it is in neither this tool's
population nor `second_copy_census.py`'s, so nothing else on the tree prints
its verdict. That is why a hand count missed it, and why §5's own table has no
`0x9C4D` row to correct: the sentence named a verdict the table never carried.
The correction is in place in
[`named-without-a-row.md`](named-without-a-row.md) §8 item 2 and cites this tool,
not §5.

## 5. `unframed`, and what "not nested" is called

Two more verdicts name the rows that are **not** nested, so the word has two
alternatives rather than being an absence:

- **`after-a-function`** — some committed listing in the same program ends the
  byte immediately before, so the frame begins the next statement rather than
  splitting one. This is the ordinary case for two exported functions sitting
  end to end, and it is the shape §5 above is about.
- **`unframed`** — nothing committed covers the address and nothing ends
  immediately before it. It is a class with **no instance among the nested
  rows**, which is what makes the three verdicts a partition rather than a list
  of the cases that have come up. Its one instance in
  `second_copy_census.py`'s own boundary partition is `bank1 0x9AD2`, a switch
  entry, and that row is in this tool's `unframed` set too.

Both say the row is not nested **by this read over the committed listings**.
Neither says the frame is wrong at that address.

## 6. The drop-or-keep answer

§8's closing question was "whether the exporter should drop a nested function
whose parent covers it". As posed that is the wrong question, and the split the
tool prints is what answers it.

**Keep the rows a `ghidra-functions.csv` row backs.** The evidence is in the
annotations themselves rather than in any count, and two of them say it in their
own words. `ec/annotations/ghidra-functions.csv:82` (`bank0`, `0x9000`
`ljmp_703d`): *"0x9000 lies inside the range this repo lists for FUN_CODE_8FDB
(0x8FDB-0x903F), so it is a byte-aligned entry inside that routine rather than
a separate function."* Line 87 (`bank0`, `0x9016` `load_constant_14`): *"It
writes nothing itself and lies inside FUN_CODE_8FDB's listed range
(0x8FDB-0x903F), so it is a byte-aligned entry inside that routine's write
sequence rather than a routine of its own."* Both are hand-decoded, both carry
`evidence` paths to committed `.asm` and `.c` files, and both are enumerated as
functions by a downstream table: `ec/annotations/function-groups.csv:80`
(`bank0,0x9000`) and `:85` (`bank0,0x9016`) each carry a row for them, and both
rows read `ungrouped` — so what that file shows is that the two addresses are
rows a per-function table carries, and nothing about which group they belong
to. A separate instance of a nested row this repository backs being consumed
downstream is `ec/annotations/xdata-registers.csv:132`, the `0x036C` row, which
reads `functions_touched 6` and names `bank1:0xE322` and `bank1:0xE332` among
the six — two of the rows the tool reports as nested in `bank1 0xE2D3`.
Dropping the rows would delete cited hand-decoding of real sites and silently
change what a generated table means.

Note what those two comments also say, because it cuts the other way and is
part of the answer rather than an objection to it: **"rather than a separate
function"** and **"rather than a routine of its own"** are what the annotation
claims about the *address*. The row still exists, is hand-decoded, is cited, and
is consumed as a function. Whether the exporter should draw a frame at an
address this repository's own annotation calls a byte-aligned entry inside
another routine is a real question — and it is a different one from §8's, which
was about dropping the function. That is the whole of the reframe: the two
decisions are separable, and only one of them is a question about the CSV.

So the question is not **"should `ExportListing.java` drop a nested function"**.
It is **"should it drop a nested function that a `ghidra-functions.csv` row
backs"**, and that is a statement about the exporter's contract, not a code
change. It is answered here and the exporter question itself is left alone.

**Four things this changes about how the population reads**, all of them
measurements rather than restatements of the issue's list:

- **`bank1 0xE322` `FUN_CODE_e322` is not an annotation row.** The issue lists
  it among the rows this repository committed deliberately. It is
  `seed_basis=auto`, `annotated=no`, and no `ghidra-functions.csv` row stands
  behind it — so it is a Ghidra frame inside a hand-decoded one, and it is on
  the other side of the line the question draws. Its neighbour `bank1 0xE332`
  `set_036c_to_4_jump_e490` is a row, and is kept.
- **The `xdata-registers.csv` overlap is `0xE322` and `0xE332`, not `0x703F` and
  `0xE322`.** Of the six functions that row names, the tool reports the two
  above as nested, the container `bank1 0xE2D3` and `bank1 0xE501` as
  `after-a-function`, and `bank1 0x703F forwarder_to_e322` and `bank1 0xE490` as
  `unframed`. This paragraph used to end "so both readings are given and neither
  is ruled on", because `xdata-registers.csv` does not define the column. **It
  is now ruled on**: `functions_touched` counts one committed `index.csv` row
  per `out_file`, stated in the block at the end of
  `ec/tools/xdata_register_map.py`, and
  both readings are derived by `ec/tools/xdata_frame_credit.py`. Counted as six
  distinct function rows, each named once, the six is six and no row is counted
  twice; counted as frames that do not hold one another, `0xE322` and `0xE332`
  sit inside `0xE2D3`'s listing and the six names cover four such frames
  (`0x703F`, `0xE2D3`, `0xE490`, `0xE501` — none of the four has an edge in the
  tool's output). The ruling keeps the six and says what it counts; the frame
  reading of this row is in
  [`xdata-frame-credit-column.md`](xdata-frame-credit-column.md), which is also
  where the "four such frames" sentence above is measured rather than counted by
  hand.
- **The remaining rows are a separate population, and this change rules on
  neither.** The `auto`- and `call-target`-seeded remainder is Ghidra's own
  frames. `common 0x6A02` and `common 0x6D46` are the mutually nested pair §3 is
  about; `common 0x65A6` is the other frame whose listing reaches back below its
  own entry point, and it holds two rows that `common 0x60C2` holds as well.
  What Ghidra's own frames should be is a question about the export, and this is
  a measurement of it — a named follow-up, not a verdict.
- **`bank0 0xF002` `FUN_CODE_f002`** (listed `0xEF96`-`0xF011`, holding
  `0xEFDC` and `0xEFF0`, both annotation rows) is **#577**. The tool reports it
  as a row like any other; it is read, cited and not relitigated here.

## 7. What `--check` refuses, and what it only reports

Two conditions fail, and both are defects this method can decide: a committed
listing whose opening bytes are **not the firmware's**, which would leave every
verdict above a reading of a tree that is no longer there; and an edge whose
bucket is outside the two above.

Two are **reported and never fail**, because this method cannot decide them and
saying otherwise would be a claim it has not earned:

- a row with **no committed listing** — the committed tree carries three, which
  `ec/decompiled/listing-index.csv` records as `(no-instructions)` with a `.c`
  and no `.asm`. That is a recorded state of the export, not a gap in it.
- a listing that **opens somewhere other than** the row's own address, so its
  opening bytes cannot be compared at that address. The committed tree carries
  fourteen of these, and six of them go on to hold a nested row — every
  container in §2's second bucket is one of them, and none of the first bucket's
  is.

A row in either class is **not found by this method**. It is never read as "not
nested", and `--check` failing on it would be red on the tree the export itself
produces, which is how a gate stops gating.

## 8. What is not addressed here

- **Editing `ExportListing.java`, or any Ghidra script, and any
  `--mode rebuild-project`.** The question is answered in §6, which is what the
  issue asked for. Changing the exporter is a different change: it writes a
  project database, which two concurrent branches cannot merge, and it would
  need the rebuild question in [`named-without-a-row.md`](named-without-a-row.md)
  §6 answered first — a scratch project and a human.
- **Wiring this into `build_ec_decompile.py --check`.** The tool imports
  `second_copy_census` at module level, and `build_ec_decompile.py` is already
  4,652 lines of which `--check` is most; a third edit there is the
  merge-conflict site `CLAUDE.md` warns about, for no coverage the test runner
  does not already give. `ec/tools/test_nested_frame_census.py` is reached by
  `bash tools/run-tests.sh` with no workflow edit, and adding a cheap-tier gate
  line is a human's change routed through `ElDavoo/agent-pipeline` upstream.
- **The `0x1664` direction / issue #466.** That is `functions_touched`
  *under*counting its readers; this is the direction it cannot reach, a column
  that can only overcount. Recorded, not addressed. The column's *meaning* is
  no longer open on this side of it — [`xdata-frame-credit-column.md`](xdata-frame-credit-column.md)
  rules that the counting is per committed `out_file`, which is what makes the
  direction unreached a fact about the export rather than a fact about an
  undefined column — but the undercounting direction itself is still not
  addressed, and this bullet does not claim otherwise.
- **The `auto`-seeded cluster of Ghidra's own frames** — the mutually nested
  `common 0x6A02` / `0x6D46` pair and `common 0x65A6`, whose listing reaches
  back below its own entry point. Measured, bucketed, and left as the named
  follow-up §6 gives.
- **Anything requiring hardware, Windows, Ghidra or the network.** Nothing here
  needs any of them.

## 9. Reproducing every figure above

```
python3 ec/tools/nested_frame_census.py --check      # the population, per program and per seed_basis
python3 ec/tools/nested_frame_census.py --self-test  # the named claims, the two buckets, the refusals
python3 ec/tools/test_nested_frame_census.py         # the unittest wrapper
python3 ec/tools/gen_findings_index.py --check       # the index regenerated, not hand-edited
python3 ec/tools/check_no_append_logs.py              # this file grew no log
python3 ec/tools/check_findings_frozen.py             # docs/findings.md still frozen, untouched
python3 ec/tools/check_no_conflict_markers.py         # no marker survived the §8 edit
python3 ec/tools/grade_name_basis.py --check          # a clean no-op: the CSVs were not disturbed
python3 tools/test_readme_suite_table.py              # the table row is a row and the lead is intact
bash tools/run-tests.sh                               # picks the new suite up by find
```

`grade_name_basis.py --check` being a clean no-op is the evidence that
`ghidra-functions.csv` was not disturbed: nothing here adds an annotation,
renames a row, or changes a register's `status:`.
