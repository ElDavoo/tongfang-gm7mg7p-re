# Which `citations()` partition a citation-gap pair came from, and why it matters (issue #1268)

The population `citation_gap_scan.py` measures is the union of all three
partitions `call_graph.citations()` returns — `kept`, `undecided` and
`rejected` — and the tool then derived a verdict for each pair from bytes
alone. The partition was discarded inside `context()`, so neither the CSV nor
the report said which of the three a row belonged to. That is the defect this
page is about: **a `no-transfer` on a pair the citation gate had already
refused is not evidence about a comment**, because there was no code claim for
a window to fail to support, and pooling the two published it as though there
were.

The fix is two columns and a print. `why` carries `"<partition>:<reason>"` on
every row, `fall_through` grades the one shape no transfer-based verdict can
express, and the report prints the split with a gloss on each partition before
it prints any verdict at all.

## The split, and the command that prints it

```sh
python3 ec/tools/citation_gap_scan.py
```

On this tree the population divides as the report prints it:

| partition of the 121 published pairs | count | what it means |
|---|---:|---|
| `kept` | 21 | a code frame, or a listing transfer, credits this as a code citation; the verdict is about corroboration |
| `undecided` | 16 | the frame settled nothing; the window walk is the only evidence there is |
| `rejected` | 84 | `citations()` already decided this is not a code citation — a data frame, or the program veto — so the verdict describes a window, not a claim |

The issue's own text put these at 22 / 15 / 84. **`rejected` is exactly as it
was filed and the other two have each moved by one**, which is the
no-hand-kept-totals rule biting in real time: the number moved between the issue
being opened and this branch landing. Nothing in the code, the CSV or the tests
holds any of the three; they are stated here once, beside the command that
prints them, for the reason `CLAUDE.md` gives.

The three verdicts, split by the partition, are the reading that was missing:

| | pairs | `boundary-cut` | `no-transfer` | `not-code` |
|---|---:|---:|---:|---:|
| `kept` | 21 | 2 | 19 | 0 |
| `undecided` | 16 | 0 | 16 | 0 |
| `rejected` | 84 | 0 | 83 | 1 |

**Both `boundary-cut` verdicts in the whole population are on `kept` pairs, and
the single `not-code` pair is on a refused one.** With two `boundary-cut` pairs
that is a small sample and it is stated here as what the table says, not as a
rule: the `why` column is per row precisely so this is readable rather than
inferred. What the two tools are for does line up with it. `boundary-cut` means
the window *does* carry a transfer to the named callee, and the citation gate
had already accepted these two as code citations — the corroboration the cut
then confirms is corroboration of a claim that was already a claim. The
`not-code` pair is the opposite: `common,1300` cited by `bank0,3AD6` is a
mention the gate refused, and a window landing on bytes the MCS-51 map assigns
to no instruction says something about those bytes, not about a comment nobody
was making.

**And the pooled figure the tool has been publishing is mostly the refused
third.** "118 of the 121 pairs are `no-transfer`" is true, and 83 of those 118
sit on pairs `citations()` had already decided were not code citations. Of the
19 that sit on a `kept` pair, the 2 the window corroborated are the ones a
reader can act on.

## What each partition means, and why the reason is the caller's

`why` is derived from what `citations()` already returned; there is no second
reading of the prose, which is the tool's own rule for `population()`.

- **`rejected`** → the first of the `Candidate.reasons` strings the caller
  recorded. `citations()` concatenates the program veto ahead of the data
  reasons, so the first is not a choice this tool makes about which veto
  mattered.
- **`kept`** → which of the two keep arms fired. The citing listing's own bytes
  (`kept:listing-corroborated`) or the comment's frame (`kept:code-frame`).
  **No pair in this population is `listing-corroborated`**, and that is
  structural rather than lucky: the population predicate is a citing row whose
  listing yields no transfer line, and the corroboration arm requires one that
  resolves to this callee. The two conditions are each other's negation, so a
  pair can satisfy at most one. The column still derives the arm rather than
  assuming it, because the population is not the only thing that will ever be
  classified.
- **`undecided`** → the frame settled nothing. Every pair in this partition
  carries exactly that frame verdict, which is what makes "every pair carries a
  reason" assertable with no empty case.

A rejected pair can carry several reasons and the column shows one. The report
names every pair where that happens rather than leaving it implicit; one of
them is the first of the collisions below, which carries both
`cross-program` and `data-marker:dptr`.

## The two cross-program collisions, read one at a time

`citations()`'s program veto fires on a mention whose address resolves into a
different program than the comment sits in. Three pairs in this population carry
`cross-program`, and they are not the same shape as each other.

**`common,0408` cited by `pd,34FB`** — the only one of those three carrying
two reasons. The
`pd,34FB` comment reads "it reads the byte at DPTR keeps it in R7 and points
DPTR at 0x0408 which is the base the file names for the 0x60-byte records", and
the listing says exactly that: `34FD 90 04 08 mov DPTR, #0x408`. So the mention
is a **data** frame twice over — it is naming an XDATA base, not a function —
and `data-marker:dptr` is right. The program veto fires on top because 0x0408 in
the `common` scope is a *code* row (`FUN_CODE_0408`), so the same number names
two different things in two address spaces. The column shows `cross-program`
because the veto outranks the frame; the pair is a genuine collision *and* a
genuine data mention, and neither reading cancels the other.

**`common,1042` cited by `pd,1041`** — a collision with nothing else wrong. The
`pd,1041` comment describes a four-byte XDATA store and says so precisely: "The
stores are the MOVX instructions at 0x1042/45/48/4B". Those are instruction
addresses inside the `pd` listing, transcribed as bare numbers. Resolved from
the `pd` scope, 0x1042 lands on the `common` row `FUN_CODE_1042` — a *different
program's* function that merely shares the number. The comment is right about
the firmware and the citation is still wrong, because a reader following the
number out of a `pd` listing lands in the `common` address space. This is the
shape issue #489's `bank1 0xE924` pair was, and it is a defect in the comment's
spelling rather than in what it says.

**`common,10F0` cited by `pd,10E8`** — the same shape. The `pd,10E8` comment
reads "Stores R3 then R2 then R1 at DPTR with an inc dptr between each, rets at
0x10F0"; 0x10F0 is where that listing's `ret` is, and `common,10F0` is
`FUN_CODE_10f0` in the common area.

`ec/decompiled/pd/0012.asm`'s own header calls the PD image "a separate program
with its own address space, not a third bank", which is the premise these rest
on. **The missing direction of `program_reason` is the other half and it is not
fixed here**: a `bank0`/`bank1`/`common` comment naming a `pd` row is still
never vetoed, because `citation_frames.program_reason` is one-directional by
design. Measured on this tree the reverse case — a `bank`/`common` citer with a
`pd` callee — has no instances, so making it two-directional would change
nothing measurable here and is a separate change with its own evidence.

## The three pairs issue #489 retired

`citation-gap-scan.md` records that #489 took three pairs out of the table and
that "each of the three wants its own reading". **All three are absent from
`ec/ghidra/gap-citation-scan.csv` on this tree** — naming a callee stops
`citations()` proposing the pair, and none of the three resolves back in. They
cannot be CSV rows, so the readings are prose here.

- **`pd 0x06EA` cited by `bank0 0xD045`.** The comment reads "It then clears
  0x06EA and 0x06EB to zero", and `bank0/D045.asm` shows those are XDATA:
  `D048 90 06 ea mov DPTR, #0x6ea` / `D04B f0 movx @DPTR, A` / `D04C a3 inc
  DPTR` / `D04D f0 movx @DPTR, A`. There is no `bank0/06EA.asm`,
  `common/06EA.asm` or `bank1/06EA.asm`; the token resolved to `pd 0x06EA`,
  `test_r4r5_bit15_then_rrc_40bit_and_negate_32bit`. **Not a missing reach — a
  different program's address space.** The comment is right and the citation is
  unfollowable.
- **`pd 0xE930` cited by `bank1 0xE924`.** The comment reads "The listing has no
  RET: it ends at 0xE930 and falls through into 0xE931, which is a bare ret".
  `bank1/E924.asm` confirms 0xE930 is its own last instruction, and
  `bank1/E931.asm` exists. The pair resolved to `pd 0xE930`,
  `write_07ca_indexed_and_restore_saved_byte_when_flag_e7` — a `pd`-image code
  address that merely shares the number. **A cross-program address collision**,
  and the same shape as the two live ones above.
- **`pd 0x39E6` cited by `pd 0x39E7`.** A true same-program relationship and not
  a collision at all: `pd/39E6.asm` is one instruction, `39E6 fd mov R5, A`,
  with no `ret` of its own, and execution continues into 0x39E7. This is the
  fall-through, and it is what the next section is about.

## The fall-through: a column, and what a fourth verdict would cost

The issue asks whether the verdict vocabulary needs a fourth value for a
same-program fall-through. **It is decidable from data the tool already has**,
and it is decidable in both directions, which is the part the forward-looking
framing misses.

`fall_through` is `yes` when the two rows are crossed by running off the end of
one listing into the other — the citing listing ending exactly where the
callee's begins, or the callee's own listing ending exactly where the citing
row begins. Both are the same relation with the two rows swapped, and the
**backward** direction is the one `pd 0x39E6`/`0x39E7` is: the *callee* falls
into the *citing row*, which a verdict reading only forward from the citing row
cannot see at all.

**Abutting is not the same as crossed, so the junction's own instruction is
read.** Deciding from the addresses alone called every abutting pair a
fall-through, and on this tree that is wrong for half of them: the last
instruction of the abutting listing is `ret`, `reti`, `sjmp`, `ljmp`, `ajmp` or
`jmp`, so control leaves there and never runs into the other row. Those are
`blocked`, which is deliberately **not** `no` — `no` says the two rows do not
abut, and `blocked` says they do and the crossing is closed. A *conditional*
branch falls through when it is not taken and stays `yes`, so `bank0,B4A8`
(`jc 0xb5d2`) and `bank0,B737` (`jnc 0xb83a`) are genuine, as are the three
whose junction is ordinary arithmetic.

`python3 ec/tools/citation_gap_scan.py` prints the split and names every
`blocked` pair with the instruction and the `.asm` it was read from. On this
tree ten live pairs abut, five each way; **five are `yes` and five are
`blocked`**, and all ten are same-scope and all still read `no-transfer` for the
verdict. The five `blocked` junctions are `bank0,C26E`'s `C277 ret`,
`bank0,D5D4`'s `sjmp 0xd607`, `bank1,A8C5` and `bank1,A8E4`'s `sjmp`s, and
`bank1,C924`'s `jmp @A+DPTR` — each read with `verify_reassembly.parse_listing`,
the same reader `listing_end()` uses. The motivating case the column exists for
is not among them and is genuine: `pd/39E6.asm` is one `39E6 fd mov R5, A` with
no transfer of its own.

The same-scope restriction is doing real work: two exports in different programs
that share an address are a collision, not an adjacency. `bank1 0xE924`'s
comment names a fall-through into `bank1 0xE931`, and grading the `pd 0xE930`
collision it resolved to as a fall-through would credit a data mention with a
control-flow relation it does not have. Every cross-program pair in this
population reads `no`.

**The recommendation is a column rather than a fourth verdict**, for the tool's
own precedent: `classify()` already handles `neighbour_edge` as "a column
rather than a fourth verdict, so the three still partition". A fourth verdict
would repartition every split in `citation-gap-scan.md`, in
`citing-listing-evidence.md`, in `neighbour-edge-attribution.md`, in
`ec/annotations/call-graph.md`, and in the frozen `docs/findings.md` §35 and §38
— and a partition that had been decided *before* the window was walked is not
the same kind of thing as one read off the bytes. A human who wants to overturn
this has one line to change: the column becomes a verdict and the three splits
become four.

What a fall-through row is **not** is a defect in the comment. `common,5A5A`
cited by `common,5A55` and `bank0,B4A8` cited by `bank0,B5B2` are both
`kept:code-frame` and both fall through; the citation gate already accepted
them, and the column only says that the relation is an adjacency rather than a
transfer. The same holds for a `blocked` row, which says something about where
control goes at the junction and nothing at all about whether the comment is
right — the gate's `kept` reading is untouched by it.

The column is blank, not `no`, when the callee has no listing on disk to read.
`bank0,F0A1` is an index row in this tree with no `.asm` beside it — as are
`bank1,17FE` and `bank1,D235`, so no uniqueness is claimed for it — and the
question is undecided rather than answered either way. No pair in this
population lands on that blank, and `test_citation_gap_why.py` covers it with a
fixture, because the census cannot. The same rule applies one step in: a listing
that exists but holds no instruction has no last instruction to read, and
`ends_with_transfer()` answers `False` for it rather than claiming a junction.

## What this does not establish

Nothing here is hardware-bound. It is a text measurement over committed
listings and the committed image: no listing was re-read from Ghidra, no
register `status:` changed, no test ran on a machine, and no live observation
is cited that is not already in `evidence/`.

Two limits carry over unchanged and are worth restating because the new columns
sit next to them. A `boundary-cut` is evidence about framing and about the
comment's accuracy, **not** proof that a function entry belongs at the site; a
data island inside a function's range decodes exactly as convincingly as code,
which is what the `bank0,D091` correction in `citing-listing-evidence.md`
stands warning about. And `call_graph.py` is untouched, so
`call-graph-callees.csv` is byte-identical either way — this changes what the
gap scan *reports*, not what the call graph believes.

**The verdicts did not move, and nothing here claims a new reach.** What changed
is that a reader can now tell which rows were ever about a comment.

## One published denominator was never pooled: `cited_by`

The corrections below name a partition for the figures that were missing one.
One figure those corrections touch is **not** one of them, and saying so is part
of getting them right rather than a footnote to them.

`neighbour-edge-attribution.md`, `../findings.md` §35 and §38 and
`call-graph.md` all quote the pair as "**15 of the 90** `cited_by == inbound`
agreements". The **15** is a gap-scan figure and is pooled like the rest: it is
built by filtering `ec/ghidra/gap-citation-scan.csv` on `neighbour_edge`, so it
counts pairs from all three buckets. **The 90 is not pooled, and never was.**
`cited_by` is `len(citing)` in `call_graph._row`, and `build()` is handed the
**kept bucket alone** — `call_graph.py` calls `citations()`, unpacks all four
returns, and passes only `cited`. `rejected` and `undecided` therefore never
reach a `cited_by`, so the `cited_by == inbound` agreement set is a kept-only
figure by construction, and it never needed a partition it was not silently
missing.

This is a fact about the code rather than a count measured here, which is why it
is stated this way: a row count of `call-graph-callees.csv` would be a value the
next merge moves, and the construction is what the reading rests on. A reader
who wants the measurement anyway gets it from the table itself — every row with
`cited_by > 0` names only kept citers in its `citing` column:

```sh
python3 -c "
import csv
cal = list(csv.DictReader(open('ec/annotations/call-graph-callees.csv', newline=''), strict=True))
print('rows with cited_by > 0:', sum(1 for r in cal if int(r['cited_by'])))
"
```

**Why it matters for reading the fifteen.** §35's own #705 correction already
found the seven-against-eight split: for 7 of the 15, the population pair and the
kept citation are two different rows, and the population pair is a rejected or
undecided mention contributing nothing to `cited_by`. That correction is the
denominator's kept-only footing showing through, and it is why "15 of the 90" is
a statement about the kept rows wearing a pooled numerator. **The fifteen and
the 9 / 6 split are unaffected by this page**, and the `why` column only adds
that a reader can now see per row which of the two rows a verdict was read off.

## Where the pooled figures are corrected

The four documents that publish a split over the population without naming the
partition carry a correction pointing here, each leaving its own figures as they
were written:

- [`citation-gap-scan.md`](citation-gap-scan.md) — the owner file, whose lead
  publishes the pooled split and whose two paragraphs describing
  `EXPECT_ROWS`/`EXPECT_PAIRS` describe pins the tool no longer has.
- [`citing-listing-evidence.md`](citing-listing-evidence.md) — its #489
  correction fixed the *size* of the population; this fixes the *composition*,
  and both stand.
- [`neighbour-edge-attribution.md`](neighbour-edge-attribution.md) — its
  `Re-deriving` command reproduces a pooled pair count.
- [`../../ec/annotations/call-graph.md`](../../ec/annotations/call-graph.md) —
  the `## What is left` section's pooled prose.

The first and last of those carry a second correction, for the reason in the
preceding section: each quoted "15 of the 90" as one pooled figure, and only the
numerator was. `citing-listing-evidence.md` needs none — it quotes the pooled
`2 / 118 / 1` and no denominator from `call-graph-callees.csv`.

`docs/findings.md` §38 carries a short note inside the existing section and §35
is left alone: its first line is already a pointer to the owner file, and
`citation-gap-scan.md` records that decision with a reason.

**The regression checks are relations, not counts.** `--self-test` asserts that
the three partitions partition the population exactly, that every row's `why`
is one `citations()` recorded and not one this tool invented, that a `kept` row
names the arm `listing_kept` identified, and that `fall_through` equals the set
re-derived from the committed `.asm` files — **junction instruction included, so
a criterion that went back to reading addresses alone fails rather than agreeing
with itself.** It also pairs `NO_FALL_THROUGH` against `disasm8051` the way the
map-unassigned set is paired, because the set is a list of mnemonic names and
the pairing is what keeps it from becoming a second partial copy of the
decoder's transfer coverage. `--check` holds the rendered CSV byte-identical, so
a table whose `why` was altered is rejected naming the row and the column.
