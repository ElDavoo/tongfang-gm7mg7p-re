# What a re-encode row's own columns say, and the ceiling they support

`ec/tools/verify_reassembly.py`'s `check_one()` returned one count under two
names. The report's `instructions_checked` column is how many instructions
`to_sdas()` translated and handed to `sdas8051`; the number of bytes that
actually reached the comparison against the firmware image was never counted.
For most rows the two are the same number. For the rows this is about they are
not, and the difference is the whole of it.

The sentence it fed — "N of M instructions re-encode to the exact bytes in the
firmware" — counts a translation as a verification. It is corrected in place at
the head of `docs/findings.md` §11, at the restatement in §11a, at §13, at §14f,
at §14g, at the §14h table row, and in `ec/ghidra/README.md`. This file is the
derivation behind those corrections and the questions it leaves open.

Every census figure below is re-derived at run time by
`ec/tools/reassembly_checked_bound.py --check` from the committed file and
attributed to the commit it was measured at; the tables are transcriptions of
that run, not values any gate holds. That is the property worth keeping, and
the reason is not tidiness: `ec/tools/verify_gap_text.py`'s
`EXPECT_CHECKED = 45394` was a hand-kept count of the same stream, the export
grew underneath it, and it was red on the tree this started from without
anything noticing — it is in no gate, which is the whole of how a stale figure
survives.

## The two return sites, and what each one means

`check_one()` returned the string `assembler-gap` from two places, and they do
not mean the same thing.

**`if not checked:`** — nothing in the function translated, so nothing was ever
handed to the assembler. That is a genuine expressiveness gap and it is where
the name belongs.

**`return "assembler-gap", "no bytes emitted at %04X"` inside the comparison
loop** — every instruction translated, the `.s51` was written, `sdas8051` ran
and exited 0, `read_lst()` parsed its listing, and the loop then found no entry
at the first address it reached. What was observed is the absence of an entry in
a parse. It is not a refusal to express a form, and it is not evidence that
nothing was emitted.

Both returned `len(checked)` as `instructions_checked`, so the second case
reported instructions it had never compared.

`OUTCOMES` gains `listing-gap` for the second case, and the name is one word
apart on purpose: `assembler-gap` is about what the assembler can express,
`listing-gap` is about what its listing carried. `split_tally()` iterates
`OUTCOMES`, so it picked the new one up without change; `run_status()` still
fails only on `mismatch`, and its docstring says why — a `listing-gap` says the
listing a run read had no entry, and the pinned build settles what that is
about, not whichever runner is reporting it. (Corrected 2026-10-03:
`run_status()` no longer fails *only* on `mismatch`. The residual half of its
policy was settled later, in `reassembly-unmeasured-row-policy.md`, and
`listing-gap` is still not adjudicated — measured, which is the reason given
here and is still the reason.)

The count is now two counts. `check_one()` returns the instructions it
translated *and* the bytes that reached the `got != want` test, accumulated
inside the loop, and `instructions_checked` keeps its old meaning so every
committed row's value is unchanged. `--self-test` asserts both: 7 bytes across
4 instructions on the agreeing fixture, and 0 bytes across 4 translated
instructions on the empty-listing one.

## The census, from the committed file and nothing else

`python3 ec/tools/reassembly_checked_bound.py` reads
`ec/ghidra/reassembly.csv` and `ec/decompiled/listing-index.csv` with the
standard library and no assembler. Each row whose detail is a
`no bytes emitted at <addr>` one falls into exactly one of three classes:

| class | what the detail names | what it establishes |
|---|---|---|
| at its own anchor | the address the `.org` was emitted at | **nothing was compared** — the loop returned at the first translated instruction |
| further on | an address above the anchor | an unknown part was compared; the ceiling cannot recover how much |
| not a `no bytes emitted` detail | an `ajmp 0x…` and the like | nothing was translated, so nothing could be compared |

At `d456411` the classes are 48 / 4 / 6 rows. The 6 are the `ajmp` functions
§11a already accounts for, and their `instructions_checked` is 0, so they cost
the bound nothing.

**The 47 / 5 / 6 the issue filed, and the 48 / 4 / 6 this measures.** Both are
right about their own reading, and the difference is the anchor. Counting a
detail that names the row's *own address* and requiring `unchecked == 0` finds
47 rows carrying 766 instructions, of which 46 stop at the row's own address
and carry 590. Counting against the *anchor* finds 48 rows carrying 702. Two
rows move between the two readings:

- `bank0 E9DE` (`rmw_1603_and_wait_tf1_2500_times`) carries 35 checked
  instructions and 2 unchecked ones, and its detail is `no bytes emitted at
  E9DE` — its own address *and* its own anchor. It compared nothing, and the
  `unchecked == 0` condition excludes it.
- `common 6D46` (`FUN_CODE_6d46`) carries 77 checked and 6 unchecked, and its
  detail is `no bytes emitted at 67EC`. Its row address is 0x6D46; its anchor is
  0x67EC, because the listing's first instruction is 0x55A below the function
  entry Ghidra gave it. On the row's address this reads as a row that got some
  way in; on the anchor it is a row that got nowhere.

The 47/5/6 split is not wrong about §14g — 52 rows moved, 47 to `match` and 5 to
`partial`, 6 stayed — because an `outcome` cell is not one of the two columns
being classified here. It is only wrong about *how many instructions never
reached a comparison*, which is what it was used for.

## The ceiling

```
$ python3 ec/tools/reassembly_checked_bound.py --check
  reassembly report: 2717 row(s), 45518 instruction(s) checked, 143 unchecked, 45661 in all
  rows whose detail says the listing parse had no entry:
    at the row's own anchor, so nothing compared : 48 row(s), 702 instruction(s)
    further on, so an unknown part compared       : 4 row(s)
    a detail that is not a `no bytes emitted` one: 6 row(s)
  ceiling: at most 44816 of the 45661 instructions reached a comparison.
```

**44,816 is a ceiling, not a figure, and the difference matters.** The 702 are
the only instructions this file proves did not reach a comparison. The four
rows in the middle class stopped part-way through — `bank0 D091` at 0xD169,
`bank1 D946` at 0xDA6E after 148 instructions in, `bank1 ED3A` at 0xEDA7,
`pd 4D6F` at 0x4B12 — and each contributed some number above zero that the
committed file does not record, because a row's model is a count and the first
address with no entry, not the set of them. The real figure is below 44,816 and
this change cannot recover by how much.

`D946`'s 148 is walked off the committed listing rather than read out of the
row: `bank1/D946.asm` runs 0xD946–0xDAAC, and 148 of those instructions — 296
bytes, ending at 0xDA6D — sit below the 0xDA6E its own `detail` names. The
row's `instructions_checked` is 176, which is the whole row: the number the
issue's "176 in" column carried, and exactly the translation count this file is
about.

**These numbers have already moved once.** The issue was filed against a file
of 2,705 rows and 45,537 instructions; the committed CSV is now 2,717 rows and
45,661 instructions, and the 590 the issue derived is unchanged while its
denominator was not. That is why the ceiling is computed here and quoted as
"what `--check` prints", and why the two figures that appear in prose are
attributed to `d456411` rather than left to rot. §14h's own table says the same
thing about its row: those two columns are computed by `to_sdas()` before the
assembler is invoked, so they cannot move with the build — which is why they
were identical across the two builds, and also why being identical is not a
robustness result.

## The anchor census

14 rows of the committed report anchor somewhere other than their own address:
the `.org` is emitted at `insns[0][0]`, the listing's first parsed address,
while the report is keyed on Ghidra's function entry. Nine read `match`, three
`partial`, two `assembler-gap`.

| row | row address | anchor | delta | outcome |
|---|---|---|---|---|
| `common 65A6` `FUN_CODE_65a6` | 65A6 | 60ED | −0x4B9 | partial |
| `common 6D46` `FUN_CODE_6d46` | 6D46 | 67EC | −0x55A | assembler-gap |
| `pd 4D6F` `dispatch_case_06` | 4D6F | 4A12 | −0x35D | assembler-gap |
| `bank0 D434` | D434 | D41C | −0x18 | partial |
| `bank0 E567` | E567 | E544 | −0x23 | match |
| `bank0 F002` | F002 | EF96 | −0x6C | match |
| `bank1 AE42` | AE42 | AE3B | −0x7 | match |
| `bank1 C80E` | C80E | C7F6 | −0x18 | match |
| `bank1 CDCB` | CDCB | CDB3 | −0x18 | match |
| `bank1 E8A4` | E8A4 | E89B | −0x9 | match |
| `common 71B9` | 71B9 | 717D | −0x3C | match |
| `pd 0B85` | 0B85 | 0B51 | −0x34 | match |
| `pd 0E54` | 0E54 | 0E18 | −0x3C | match |
| `pd C873` | C873 | C819 | −0x5A | partial |

The two rows that named a detail address *below* their own row were
`common 6D46 → 67EC` and `pd 4D6F → 4B12`. Both are in this table, and both are
rows where reading the detail against the row address gives the wrong answer:
for `6D46` it turns "compared nothing" into "compared some way in"; for
`4D6F` the detail is above the anchor, so the row really did get 0x100 in, and
the table is what says so rather than the arithmetic being wrong.

**The column does not exist, and adding it is #157's.** A column on
`write_report()` and not on the committed report is what
`tools/check_deep_schedule_emit.py`'s header hold exists to catch: it compares
`emit_csv()`'s first line against the committed file's, byte for byte, because
that is the coupling the nightly artifact's `(program, addr)` join rests on.
`check_one()` now returns the anchor and the bytes compared; both belong in
that header, and both wait for the re-report that #157 owes, the way
`listing_digest` waited for `--add-digest-column`. Until then the anchor is in
the `detail` of every `listing-gap` row, so a report written under the new code
says where it looked without a column for it.

## The cross-check the committed evidence already holds

`evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv` is the same 52 rows §14h
measured between the pinned build and a runner's, with both outcomes and both
counts. Joined against this census, it says one thing exactly:

**All 48 own-anchor rows are among the 52 that moved**, and they read `match`
or `partial` under `02.00` with the same 702 instructions checked. **The four
that moved and are not own-anchor are exactly the four `stopped-later` rows** —
`bank0 D091`, `bank1 D946`, `bank1 ED3A`, `pd 4D6F`. Nothing was classified by
hand and nothing is inferred: the 48 and the 4 fall out of the join.

That is the cross-check §14g did not have. Under `02.00` the 702 instructions
were compared and matched, so they are not a gap in the evidence — they are 702
instructions whose *verification* the committed report's single count cannot
express, and it is the committed report's build, not the code, that leaves them
uncompared. On the pinned build `assembler-gap` is the correct outcome for what
it can see; it is `instructions_checked` that is wrong.

## What the listing actually holds for two of them

The issue asked this rather than assuming it, and the answer is a measurement.
`bank0/801F` (`movx @DPTR, A`) and `bank0/AB6D` (`ret`) are single-instruction
functions, so nothing about them is a form an assembler declines, and their
committed rows are `no bytes emitted at 801F` / `at AB6D` with one instruction
checked each.

`evidence/ec-reencode/2026-10-01-listing-probe-801F-AB6D.md` has it, with the
generated `.s51` and the assembler's `.lst` committed beside it. Measured, on
the `sdas8051` a runner has (`02.00`, SDCC 4.2.0):

- both sources assemble, **exit 0**, no diagnostic;
- both listings carry one addressed entry with the byte and the `[24]`
  relocation class — `00801F F0 [24]` and `00AB6D 22 [24]`;
- `read_lst()` parses both to `{0x801F: 0xF0}` and `{0xAB6D: 0x22}`;
- `check_one()` returns `match` for both, with the digests the committed
  report carries.

So on this build the two rows are not a refusal and not a listing `read_lst()`
cannot see. What that does **not** establish is what the pinned
`05.50.4+NoICE+SDCCmods-WIP-R14` build printed, and the committed rows were
measured with that one. `evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv`
already records both rows and `bank1/D946` moving to `match` under the apt
build; what it does not commit is a listing, which is what it would take to
read one.

## What this does not settle

Three candidates explain `no bytes emitted at <addr>`, and nothing here
distinguishes them. **A `sdas8051` that cannot express the form.** Ruled out
for `801F` and `AB6D` on this build and live for the pinned one, which is not
the same answer. **The listing's shape differing under `-lxosgff` for the
pinned build**, which would make the same form print in a shape
`read_lst()`'s regex cannot see. **`.area`/`.org` anchoring producing something
`read_lst()` cannot see**, which the probe argues against on this build and
which the 14-row anchor census keeps live on any build — a `.org` at an address
the listing prints differently is not a shape `read_lst()` was written against.

What `read_lst()` structurally requires is worth stating, because it is why a
listing can parse to `{}` while containing the bytes: an address, a byte run,
**and** the bracketed relocation class, all on one line. Drop the class and the
line does not match; that is a statement about the regex, not about what any
particular run produced.

**The cause may be per-row rather than global.** `bank0 E9DE` is a one-address
failure on a 35-instruction row and `bank1 D946` stops part-way into a much
longer one; a single global cause would have to explain both, and nothing
measured here does.

**What would settle it.** Re-reporting `ec/ghidra/reassembly.csv` under the
pinned build (#157) does one half: rows that move tell you the apt build's
listing is fine and the committed one was not, and rows that stay tell you the
opposite. The other half is a committed `.lst` from the pinned build for one
`no bytes emitted` row — the `801F` probe, one directory over — which is a
command on a machine with the nix toolchain and nothing more.

**And it is not a claim about the disassembly.** Nothing here says a listing is
wrong, or that a byte is not the firmware's. `verify_reassembly.py --check`
compares every committed listing byte against the image with no assembler and
finds no disagreement, and that covers the instructions this re-encode never
reached.

## What changed, and what deliberately did not

- `check_one()` returns the instructions translated and the bytes compared, and
  `listing-gap` for the second of the two cases; `OUTCOMES`, `write_report()`'s
  row, `verify()`'s summary and `compare_tally()`'s cell lines follow.
- `--self-test` gains a case that needs no assembler — a stub that exits 0 and
  writes an empty listing — placed before the `find_assembler()` early return so
  it runs in the cheap tier on every commit. It asserts the new outcome, 0
  bytes against 4 translated instructions, and an exit status of 0.
- `verify_gap_text.py`'s `EXPECT_CHECKED` is gone. What replaces it is two
  derivations of the same committed file — one through `to_sdas()` over every
  `.asm`, one through the CSV's own columns — asserted to agree, and a ceiling
  asserted to sit below both. That is a claim rather than a census: a total
  moves on every export, an agreement between two derivations does not.
- `verify_gap_text.py --check` was red on the tree this started from, on one
  row's `row_name`: `common,0D7B` had been renamed and
  `ec/ghidra/gap-text-check.csv` had not been regenerated. Fixed in this branch
  by running the tool's own `--report` — one row, one column, no assembler —
  which is the same note `docs/ci/agent-gates-gap-text-check.patch` records
  about its own patch.
- `parse_listing()` closes its file handle. It held 2,717 of them per run and
  CPython collected them promptly enough that no run complained; a unit test
  calling it under unittest's warning filters printed one `ResourceWarning` per
  listing. Three suites carry a comment about the leak and one reads listings
  with its own reader to avoid it; the census cannot, because the claim it
  makes is that this reader and `check_one()` agree on a listing's first
  address.
- `disasm8051.py` and `xdata_register_map.py` carried the same stale
  denominator in a comment each. Both now say what they mean without it.

## What this opens

- **A per-row anchor and bytes-compared column**, with `--report` under the
  pinned build, which is #157 and not this change.
- **The three candidates above**, none settled and possibly per-row.
  `bank0 E9DE` is the cheapest one to work on and the shortest to reproduce.
- **§14g's open question, unchanged by any of this**: a report row whose
  outcome is `error` or `assembler-error` is named by the residual and
  `check()` still passes it. (Settled since, in
  `reassembly-unmeasured-row-policy.md`: all five residual outcomes fail now,
  and `write_report()` refuses to write a run carrying one.)
- **`check_one()`'s row model.** A row records a count and the first skipped
  address, not the set of them, so the middle class above cannot be resolved
  from the committed file at all. Recording the number of bytes compared per
  row would turn the ceiling into a figure and is the same column as above.

Nothing here needs hardware, no register was read back, and no driver is
touched.