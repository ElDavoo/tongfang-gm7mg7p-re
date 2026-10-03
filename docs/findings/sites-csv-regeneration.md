# The committed sites tables are re-derived from the firmware, not from the pages that print the command (issue #313)

Every `*-sites.csv` in `ec/annotations` that carries `trace_xdata_refs.py`'s
schema is the product of one command over `ec/firmware/GMxMGxx_11.800`, and the
page above each one prints that command in a §1 so a reader can re-run it. What
no CI step did was re-run it. The claim each page rests on — that the table is
the map of the addresses it says it is — was a transcript, verified once by
hand. `ec/tools/test_sites_csv_regeneration.py` re-derives each table from the
committed image on every run of `bash tools/run-tests.sh` and compares it.

## The premise needs correcting, and the conclusion survives it

Issue #313 reported that *"Grepping the suites for those filenames returns
nothing — no test reads them."* That is wrong, and the suites it names are
worth listing rather than contradicting, because a reader who believed the
premise would not know where to look:

| suite | what it reads, and from where |
|---|---|
| `ec/tools/test_walk_budget_census.py` | every `access` cell of the tables in `walk_budget_census.TABLES`, re-derived through `classify()` |
| `ec/tools/test_dptr_rebuild_forms.py` | every `terminator` and `access` cell of its own `SIX`, through `walk_why()` and `classify()` |
| `ec/tools/check_site_census.py` | the `census` column of `xdata-086x-dispatch-sites.csv`, against the per-address correspondence files |
| `windows/tools/test_gpu_block_watch.py` | a census of its own over `ec-07c4-07d5-sites.csv` and `ec-0x07c5-sites.csv` |
| `ec/tools/test_access_cell_corrections.py` | the corrected `access` cells, against `access_cell_corrections.BY_OFFSET` |
| `ec/tools/test_pd_site_clusters.py`, `test_findings_4o_correction.py`, `test_code_pointer_sites.py`, `test_0741_bit7_chain.py`, `test_code_table_records.py`, `test_trace_xdata_refs_usage.py` | these files' rows as *input* to another claim |

**The gap is one level below where the issue places it.** Every one of those
checks iterates the rows **already in the file** and re-derives a cell of each,
because a row that is not there is not iterated. A few go further and
regenerate a table whole rather than re-derive a cell of it, so the "none of
them re-derives the row set" version of the claim is false for the tables they
cover:

| table | suite and case | what it compares |
|---|---|---|
| `manual-fan-ctrl-0751-sites.csv` | `test_trace_xdata_refs_usage.py::test_the_terminator_line_reproduces_its_committed_table` | the tool's stdout against the committed file read in binary — every row |
| `xdata-086x-dispatch-sites.csv` | `test_trace_xdata_refs_usage.py::test_the_default_check_still_reproduces_its_table`, and `test_walk_budget_census.py::test_the_sweep_reproduces_the_086x_table_byte_for_byte` | `--check`'s exit code, which is `check_table()`'s verdict on any difference |
| `ap-oem-0741-bit7-sites.csv` | `test_0741_bit7_chain.py::test_the_reproduction_command_reproduces_the_committed_table` | the tool's stdout against the committed file |

Each was measured on committed inputs by deleting a data row and confirming the
named case goes red. So the tables were not held to nothing — those were held
whole, and the rest were held, cell by cell, to a row set that nothing
checked.

## What notices a change, measured on committed inputs

Each row below is one mutation applied to a committed CSV, the relevant suites
re-run, and the file restored. "caught by" names the suite that went red.

| mutation | caught by, before this suite |
|---|---|
| delete a data row from `ec-07c4-07d5-sites.csv` | `test_walk_budget_census.py` — `ReCutTests.test_the_only_window_cell_that_moved_is_the_preexisting_drift`, via `len(old) == len(after)` against a pinned commit |
| delete a data row from `ec-0x07d0-sites.csv` | the same case, and `test_pd_site_clusters.py` |
| delete a data row from `ec-0x07d1-sites.csv` | the same case |
| delete a data row from `ec-0x07c5-sites.csv` | `test_gpu_block_watch.py` |
| drop the whole `terminator` column from `ec-0x07c5-sites.csv` | **nothing** |
| drop the whole `terminator` column from `ec-07c4-07d5-sites.csv` | `test_walk_budget_census.py`, `test_dptr_rebuild_forms.py`, `test_trace_xdata_refs_usage.py` |
| relabel a `pd-image` row `bank0` in `ec-0x07d0-sites.csv` | `test_pd_site_clusters.py` only |
| relabel a `pd-image` row `bank0` in `ec-0x07d1-sites.csv` | **nothing** |
| relabel a `bank0` row `pd-image` in `ec-07c4-07d5-sites.csv` | `test_gpu_block_watch.py`, and only incidentally — `read_site_census` filters `bank0`, so the population moves |
| relabel a `bank0` row `pd-image` in `ec-0x07c5-sites.csv` | `test_gpu_block_watch.py`, incidentally, the same way |
| relabel a `bank0` row `pd-image` in `manual-fan-ctrl-0751-sites.csv` | `test_trace_xdata_refs_usage.py`, **directly** — `test_the_terminator_line_reproduces_its_committed_table` byte-compares the tool's stdout against the committed file, and a `region` cell is among the bytes |
| swap two adjacent data rows in `ec-07d6-07d7-sites.csv` | **nothing** |
| swap two adjacent data rows in `ec-0x07d0-sites.csv` | `test_walk_budget_census.py`, `test_pd_site_clusters.py` |

Two things follow, and the second is the sharper one.

**The row-count check that does this work is a census.** `assertEqual(checked,
1288)` in `test_walk_budget_census.py` and the `len(old) == len(after)` in
`ReCutTests` are both counts of a table, which is the shape CLAUDE.md names as
its repeated anti-pattern: a value every merge has to edit, held here for no
reason a re-derivation would not hold better. The second one is not defeated by
editing the first: deleting a row from `ec-0x07d0-sites.csv` and moving `1288`
to `1287` was measured, and `test_walk_budget_census.py` still goes red, because
`ReCutTests` compares against a row count read from a pinned historical commit
rather than against the number the other case hard-codes. Two censuses, and
editing one leaves the other.

This suite does not touch either — they are live assertions in a file several
open pull requests edit, and removing them is not this issue's work. What it
does is make them unnecessary *for this claim*, which is the half that was
available: a re-derivation from the committed image is not a number a re-cut has
to update, so it cannot go stale the way a count does.

**A `region` cell is the cell no cell-wise check derives.** `classify()` says
what a site's window did and `walk_why()` says why the window ended; neither
says which image the site is in. That is `region_of()`'s column alone, so a
relabel is noticed only where it happens to move something another check looks
at — a population, in the tables the matrix above names `test_gpu_block_watch.py`
or `test_pd_site_clusters.py` for, and the compared bytes themselves in
`manual-fan-ctrl-0751-sites.csv`, whose suite byte-compares the whole table. A
`pd-image` row read as `bank0` credits the main EC with a site in an image it is
not in, which is the exact confusion `read_site_census`'s own filter docstring
says the filter exists to prevent. The `ec-0x07d1-sites.csv` row in the table
is caught by nothing at all, and that is the issue's quiet one, confirmed.

## The inventory, and what regenerates each table

One table in the directory carrying this schema was not in the issue's list and
is in the suite: `ec-0x07c5-sites.csv`, which
`windows/tools/test_gpu_block_watch.py` reads and which reproduces the same
way as its siblings. `ec-0x07c5-sites.md` §1 prints the same command the others
do.

The suite's `committed_sites_tables()` finds the population by scanning
`ec/annotations` for the eight-column header `csv_table()` writes, plus any
subset of `census` and `terminator` — so a table cut by another issue with
`--csv` and committed under this header fails the suite until its address list
is added, rather than being silently unchecked. That scan is what tells
`flow-follow-none-sites.csv` (a `walk_flow_follow.py` schema) and
`boot-xdata-sites.csv` (a `scan_refs.py` one) apart from a table this tool
wrote, despite all three matching `*sites.csv`.

Per file, the frozen address list — **this is the suite's own claim about which
addresses a committed file maps, not something read back from the file**, which
is the whole design: deriving it from the CSV would be circular, since a row
dropped from the file would drop from the regeneration too and the comparison
would pass on the file with the row missing.

| table | addresses | `census` | `terminator` |
|---|---|---|---|
| `ec-07c4-07d5-sites.csv` | `0x07C4 0x07D3 0x07D4 0x07D5` | no | yes |
| `ec-07d6-07d7-sites.csv` | `0x07D6 0x07D7` | no | yes |
| `ec-09e9-09eb-sites.csv` | `0x09E9 0x09EA 0x09EB` | no | no |
| `ec-0x07c5-sites.csv` | `0x07C5` | no | yes |
| `ec-0x07d0-sites.csv` | `0x07D0` | no | yes |
| `ec-0x07d1-sites.csv` | `0x07D1` | no | yes |
| `ap-oem-0741-bit7-sites.csv` | `0x0741` | no | yes |
| `manual-fan-ctrl-0751-sites.csv` | `0x0751` | no | yes |
| `xdata-0400-045f-sites.csv` | the `0x0400`–`0x045F` addresses with a committed row | no | yes |
| `xdata-086x-dispatch-sites.csv` | `0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B 0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07` | **yes** | no |
| `xdata-1c3x-consumers-sites.csv` | `0x1C39 0x1C3A 0x1C12 0x1C13 0x1C14 0x1C36 0x1C37 0x1C38 0x1C01 0x1C02 0x1C03` | no | no |

Reproduce any row of it with the command its page prints, or with the one below,
which is the comparison the suite makes:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D1 --csv \
          --terminator-column \
  | diff - ec/annotations/ec-0x07d1-sites.csv && echo identical
identical
```

### Address order is load-bearing

`csv_table()` emits each address's sites where the caller put the address, so a
regenerated table is a function of the address list's *order*. Two committed
tables are not in address order — `xdata-1c3x-consumers-sites.csv` is committed
`0x1C39` before `0x1C12`, and `xdata-086x-dispatch-sites.csv` `0x0860` before
`0x1C39`. Both were checked both ways: sorting the frozen list for
`xdata-1c3x-consumers-sites.csv` reproduces nothing, and the suite says which
kind of failure that is rather than leaving it in a comment.

### Why not `--check`

`--check` unconditionally loads the census map (`main()` does it whenever
`args.check is not None`), which appends a `census` column that none of these
tables but one carries — so a `--check` run is red on the committed data before
any real difference. That is the failure mode `check_table`'s own docstring
calls worse than no check. The suite calls `csv_table()` directly, which is the
same comparison one function lower, with the map passed only for the table whose
committed header has the column.

`xdata-086x-dispatch-sites.csv`'s `census` column is not image-derived at all —
it is a hand-typed reading of the decompile, held by `check_site_census.py` — so
the byte comparison covers that column as *rendered*. A red run on that table is
a disagreement about the correspondence files first and about the image second,
and `CensusColumnTests` asserts the `not recorded` fallback appears nowhere in
it, so a table full of the fallback cannot pass while asserting nothing.

## What a green run means

It means **this method found the same sites, in the same order, with the same
cells**, as the committed file records. It does not mean the enumeration is
complete. A site reached through a computed DPTR, or through any form
`scan_refs.py`'s blind spot covers, has no row here and would have none in a
regenerated table either — the regeneration would agree with the file that
omits it. "Not found by this method, never absent" is the phrasing in
`trace_xdata_refs.py`'s module docstring and in `ec/annotations/registers.yaml`,
and it is the honest reading of a green run.

## The §1 blocks now point at a command that runs

`ec-07c4-07d5-sites.md`, `ec-0x07d0-sites.md` and `ec-0x07d1-sites.md` each said
"that is the reconciliation check this file rests on" over a transcript. Each §1
now also names `test_sites_csv_regeneration.py`, so the sentence points at
something a CI run repeats rather than at a reader's memory.

## Verification

Committed inputs only: the 256 KiB image, the committed CSVs, and the
correspondence files. No EC is opened, no register is read back, no Ghidra and
no network.

```console
$ bash tools/run-tests.sh ec/tools
...
$ python3 -m unittest discover -s ec/tools -p test_sites_csv_regeneration.py
OK
```

The suite's teeth were checked by mutation rather than asserted: a data row
deleted, a row added, a row swapped with its neighbour, an `access` cell
rewritten, a `region` cell relabelled and a `terminator` column dropped, each
applied to a committed CSV and each restored afterwards. Every one turns the
suite red, including each row marked **nothing** above, which no other suite
notices.