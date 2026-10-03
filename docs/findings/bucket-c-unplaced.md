# The unplaced bucket-C census: what the sites no data region covers say

## What this is

[`ec-data-regions.md`](ec-data-regions.md) §4 closed with the honest follow-up:

> The honest follow-up is a census of anchored high-scoring sites that fall
> **outside** every listed region — the mirror of what this issue asked for, and
> the population where a real call and a phantom look identical.

This is that census. [`bucket-c-codemap.md`](bucket-c-codemap.md) classified all
140 bucket-C sites against a recovered code map of the common area and labelled
the 35 that fall inside a span
[`data-regions.yaml`](../../ec/annotations/data-regions.yaml) lists as a table.
The other **105** — 50 of them anchored — had never been looked at individually,
and this page puts each one in
[`bucket-c-unplaced.csv`](../../ec/annotations/bucket-c-unplaced.csv) with the
evidence beside its answer.

It is a census **over** that classification, not a second walk.
[`bucket_c_unplaced.py`](../../ec/tools/bucket_c_unplaced.py) *runs*
`bucket_c_codemap.build()` and `audit_call_targets.survey()` and re-derives
nothing either of them already derived, for the discipline
`bucket_c_codemap.bucket_c_rows()` sets in its own docstring.

**Nothing here decides bucket C, and no site is decided.** Every verdict is a
reading of bytes by one method. No register was read back, no capture was
opened, no EC was powered, no `status:` in `registers.yaml` moves, and no
Windows binary is involved.

## The population is derived, so a new region moves it

The 105 is not written into the tool or the CSV. It falls out of running
`data_regions.region_at()` over every bucket-C row the image's own scan produces,
and `--check` holds `unplaced + labelled == 140` in both directions, so a region
added to `data-regions.yaml` moves this table instead of leaving a stale figure
in prose.

The count is stated in a sentence in `data-regions.yaml`'s own header, in
[`bank-call-audit.md`](../../ec/annotations/bank-call-audit.md), and in
`data_regions.py`'s module docstring. **None is edited here**, because no region
is added by this change and so the number is not moving; editing shared files to
restate a figure that is already right is precisely the churn CLAUDE.md's totals
rule was written about. Instead
[`test_bucket_c_unplaced.py`](../../ec/tools/test_bucket_c_unplaced.py)'s
figure-pin cases hold the derived count against each of them, so the next region
to be listed turns `bash tools/run-tests.sh` red **and names the file** rather
than leaving a sentence to go quietly stale. That is
`check_citation_lines.py`'s model, and it is the opposite of the failure
CLAUDE.md records at bit #1169, where four concurrent branches each bumped a
hard-coded count from a different base.

## The verdicts

Four values, closed, ordered, first match wins. A value outside the vocabulary
is a `SystemExit` rather than a rendered row, and every row carries a non-empty
reason from its verdict's own set.

| verdict | sites | what it means |
|---|---:|---|
| `trampoline` | 1 | the **target** is an address a BL51 trampoline names |
| `table-entry` | 0 | on a listed region's grid, adjacent to it, shape decodes |
| `code` | 93 | the byte is inside something a method read as code |
| `unresolved` | 11 | not decided here; the walk's own reason is in the next column |

By reason:

| reason | sites |
|---|---:|
| `mid-instruction-in-a-span-this-walk-decoded` | 74 |
| `inside-a-ghidra-common-function` | 17 |
| `tail-jump` | 7 |
| `ret` | 4 |
| `on-an-instruction-boundary-this-walk-decoded` | 2 |
| `target-named-by-a-trampoline` | 1 |

**`code` does not mean the byte starts an instruction**, and the CSV says so
beside it rather than inside it. `on_instruction_boundary` is a separate boolean
and it reads **yes for 2 of the 105**. Of the 93 `code` rows, **74 sit inside a
span this walk decoded without being the first byte of anything**, and **17 sit
inside a `common` function `ec/decompiled/index.csv` records** — every one of
those 17 a row the walk itself never reached, so it is a second method's
coverage and not this one's. The 91 is the combined count of `code` rows that do
not start an instruction; 74 is the count this walk is answerable for, and the
two are not interchangeable: attributing the 17 to the descent would be
`docs/findings.md` §4c's error one level up, since a byte covered by the
Ghidra `common` function set is not a byte the #49 walk decoded. The 74 are the
census's original phantom shape: a `0x12` that is the operand of a
`mov dptr,#imm16` rather than the opcode of a call. `0x055DC` is the precedent
that the two questions have to stay apart; it is reached, covered, *and*
genuinely a table entry on the same evidence.

## `table-entry` is empty, and that is a result

No unplaced site is a table entry of a region beside it. The closest any of them
comes is 5 bytes from its nearest listed region's edge, and the narrowest stride
in the file is 2 — so the grid question has content for every row and the
adjacency question has none.

The `table-entry` verdict requires the site to sit on the nearest region's grid,
have that region's shape decode under it, **and** be within one stride of the
region. Drop that last clause and 23 rows become table entries — including one
6562 bytes past `common-055a8-be-words`'s end, whose leading byte happens to
satisfy that region's descending-word shape. That is one byte matching a
predicate at an arbitrary distance, and calling it a table entry would be the
overclaim this repository has retracted twice. So the measurement stays ungated
in its own column and the verdict is gated.

**A zero here is "not found by this method", never "absent."** This page's
entire subject is one method's blind spots, so `docs/findings.md` §4c applies to
it harder than to almost anything else in the tree.

## The base rate `0x021C6`'s alignment is worth

`0x021C6` is on the stride grid of `common-219c-ff-triples` — 0x12 past its
`file_hi` of `0x21B4`, which is six whole stride-3 entries — and `d[0x021C6]` is
`0x12`, where an `ff-triples` entry needs a leading `0xFF`. So the grid cell
reads `on-grid shape-fails`, which is a different claim from `off-grid`: the byte
is exactly where an entry would go and is not one.

That is worth reporting, and it is worth exactly as much as the base rate. Across
the population, **43 of the 105 sit on their nearest region's grid and 23 of
those have the shape decode** — which is the rate at which alignment and a shape
match arrive here by arithmetic. A single site reported without that share is the
figure-without-its-denominator this repository has had to retract twice, so the
tool prints the share and the write-up cannot quietly omit it.

The tool prints both numbers on every run rather than leaving them to this page.

## The gap below the walk's frontier

[`bucket-c-codemap.md`](bucket-c-codemap.md) §Limits names what it declines to
carry: a `not-reached` site can be a finding about the byte, or it can be a
statement about *this seed set* having stopped and never come back, and
`walk_reason` does not distinguish the two. `bytes_below_frontier` materialises
the gap that §Limits asks a reader to measure by hand — the distance to the
nearest instruction start the walk decoded at or below the site.

**No threshold is applied to it.** A row is never promoted out of `unresolved`
by sitting far below the frontier, because a cut would be a hand-set value every
future seed set has to re-argue — the same disease as a hand-kept count. The
distribution is printed and the column is left as a measurement.

It is measured to the nearest instruction *start*, not the nearest decoded byte.
That is the definition `bucket-c-codemap.md`'s own `0x021C6` figure was taken
under: this tool reproduces **921** for that site under the start-based
definition and 919 under the byte-based one, and a column disagreeing with a
committed sentence by two is a column a reader has to re-derive. 103 of the 105
sit in a gap, from 1 to 921 bytes deep.

## Is the target named anywhere

Item 3 of the question, and the answer has a shape worth stating plainly.

60 of the 105 sites name their target in
[`ghidra-functions.csv`](../../ec/annotations/ghidra-functions.csv) — 37 in one
bank, and **23 in both banks under different names**. Both-banks-different is the
problem restated, not resolved: the same address is a different routine in each
bank, which is precisely why `offset_for_runtime()` returns `None`. It says the
address is a plausible entry point. It does not say any site reaches one.

45 sites' targets are named nowhere. Four of those addresses
(`0xA3E0`, `0xAF32`, `0xE322`, `0xF002`) do appear in
[`decompiled/index.csv`](../../ec/decompiled/index.csv), and they are reported
as **not annotated** rather than folded in: their index rows carry
`seed_basis` of `call-target` or `auto`, so the names are what the decompiler
found, not what a person wrote down. The census reads the annotations CSV —
CLAUDE.md's editable surface — and records the index separately, because the
index is generated from it and reading the generated file instead would make
"annotated" and "discovered" indistinguishable in one column.

## `0x021C6`, stated as a row

Two readings stay open and this census picks neither.

| column | value |
|---|---|
| `verdict` | `trampoline` |
| `verdict_reason` | `target-named-by-a-trampoline` |
| `grid_state` | `on-grid shape-fails` |
| `bytes_to_nearest_region` | 18 |
| `bytes_below_frontier` | 921 |
| `walk_verdict` | `not-reached` |
| `walk_reason` | `tail-jump` |
| `on_instruction_boundary` | `no` |
| `target_is_trampoline_entry` | `yes` |
| `target_named_in` | `no` |

The last line is the finding this census adds about it. `0xE000` is the one
address of the 102 that the linker itself recorded as a banked entry point, and
**no hand annotation names it, in either bank**. The bank-0 half of that is
already on record: [`forwarder-targets.csv`](../../ec/annotations/forwarder-targets.csv)
carries `0xE000` as `no-listing`, "no committed export names this address in
bank0", per [`forwarder-target-bank-census.md`](forwarder-target-bank-census.md)
§"The unlisted targets, read off the image". What this census adds is the
bank-1 half, and the linkage — the best-evidenced site in the bucket points at
the one address of the 102 that is both a trampoline's entry point and unnamed.
It is not the only unnamed target: 69 of the 102 have no annotation in any bank.
It is the only one of those the linker recorded as a banked entry point. That is
not evidence for or against either reading — a routine can be perfectly real and
unnamed — but it is a fact about where the evidence is thinnest.

`bytes_to_nearest_region` reads **18**, which is the 0x12 above under §4's
reference: the column measures from the region's half-open `file_hi`, so
`0x21C6 - 0x21B4` is 0x12, against 0x13 measured from the last entry byte at
`0x21B3`. The column is that difference, not a count of the bytes strictly
between the edge and the site — which would be 17. §4 gives the other two
because it is quoting two different edges; the site is the same byte under all
of them, and `test_bucket_c_unplaced.py` pins the `file_hi` reading so the three
cannot drift apart unnoticed.

Two readings, unchanged: a real call into bank space, or another misframed table
or an unnamed routine. Its target being the one address of the 102 that a
trampoline names is **evidence, not a verdict** — a byte scan does not say which
bank is mapped when the common area runs.

## The function-boundary question is still open, and unowned

The boundary work is still needed and **this page names no issue as its owner**,
per the question's own instruction, because naming a closed one is the
stale-pointer failure the question already flags. `ec-data-regions.md` §4 is
where the routing currently goes — it hands the decision to "a recovered
common-area function boundary set, which is a disassembler's job and issue #20's"
— and §Limits and `data-regions.yaml`'s header repeat it. That is quoted here as
the stale pointer it is, the reason this page declines to repeat it; the open
question stands on its own without an issue number attached.

Two artifacts stand for whoever picks it up, and neither needs this census:
[`bucket_c_codemap.py`](../../ec/tools/bucket_c_codemap.py) `--spans` emits the
reached-span set a different seed base can start from, and
[`ec/ghidra/README.md`](../../ec/ghidra/README.md) is where a Ghidra-side
attempt would be recorded.

## Limits

- **No site is decided, and no verdict is a behavioural claim.** `code` is a
  statement about where a byte falls relative to something a method in this
  repository read as code — 74 rows by the #49 walk, 17 by the `common` function
  set `ec/decompiled/index.csv` records. It is not a reading of the byte, and
  certainly not an observation of the machine.
- **`trampoline` is a claim about the target, not the site.** A bucket-C site is
  a `0x12`/`0x02` byte and cannot itself be a trampoline; the verdict records that
  the *linker* treated the address as a banked entry point.
- **Every count is a count of one method over one seed set.** The `code` verdict
  rests on `bucket_c_codemap.py`'s descent from the seed set
  [`bucket-c-codemap.md`](bucket-c-codemap.md) states; a different seed set,
  budget or depth moves the `inside-a-ghidra-common-function` and walk-spanned
  rows between them, and the table is regenerated rather than reconciled.
- **`0x021C6`'s `not-reached` is a coverage statement.** At 921 bytes below the
  frontier it is the furthest row in the table, and that is a fact about this
  walk, not about the byte.
- **A `table-entry` count of zero is this gate's result, not a finding about the
  image.** An ungated count would have been 23, and those 23 are kept in the
  `grid_state` column rather than discarded.
- **The 43-of-105 grid share is a base rate for *this* population against *these*
  regions.** It moves if a region is listed, which is one of the reasons the
  population is derived.
- **Not a code/data separation of the image.** This is the narrow slice of it one
  question needed, and the boundary work behind it is the open question above —
  unowned here, deliberately.
- **No hardware, no Windows, no capture, no `registers.yaml`.** No register is
  read back and no behavioural claim about any register is made or denied.
- **`--check` is not a gate.** It is not in
  `.github/scripts/agent-gates.sh`, which is a template copy the push token has
  no `workflow` scope to edit, and whose tool-list region is already contested by
  prepared patches per
  [`prepared-gate-patches.md`](prepared-gate-patches.md). The suite is ungated
  and `bash tools/run-tests.sh` collects it today — the same position
  `bucket-c-codemap.md` §Limits records for its own `--check`.

## Reproducing it

```sh
python3 ec/tools/bucket_c_unplaced.py ec/firmware/GMxMGxx_11.800 --check
python3 ec/tools/bucket_c_unplaced.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/bucket_c_unplaced.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/bucket_c_unplaced.py ec/firmware/GMxMGxx_11.800 --for-offset 0x021C6
python3 ec/tools/test_bucket_c_unplaced.py

# the inputs did not move
python3 ec/tools/data_regions.py --check
python3 ec/tools/bucket_c_codemap.py ec/firmware/GMxMGxx_11.800 --check
```

The plain run prints the population, the verdict and reason tables, the frontier
distribution, the naming summary and the grid base rate — so every figure on this
page is a line in that output rather than a number copied out of it.

## Follow-ups this opens

- **`0x021C6`'s target `0xE000` is unannotated in both banks.** It is the only
  address of the 102 that a trampoline names, so an annotation there would be
  worth more than another seed at the site itself: of the 69 targets no
  annotation names, it is the one place in this population where a name would
  resolve an ambiguity no amount of framing can.
- **`0x021C6` sits at the far end of the frontier distribution.** Closing that
  hole from a different seed base remains the narrowest useful next step, and
  `bucket_c_codemap.py --spans` is where a new base would start from.
- **The 23 both-banks-different targets are the population where a name is worth
  the most.** Every one of them is an address whose meaning depends on which bank
  is mapped, and the bank-window overlap this census records per row is what a
  future cross-bank attribution pass would start from.