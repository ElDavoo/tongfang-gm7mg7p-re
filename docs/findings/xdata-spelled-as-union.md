# `spelled_as` is a union across programs, and the column that says so (issue #709)

**Issue #709, 2026-09-25.** `ec/annotations/xdata-registers.csv` records one
`spelled_as` cell per address, and on a `program=both` row that cell is the
union of what *either* program spells. The file therefore could not answer a
per-program question, and on one row today it says something that is wrong read
that way: `0x04A3` is `DAT_EXTMEM+pair-literal` there, while the main EC spells
it `pair-literal` and the PD image spells it `DAT_EXTMEM`. This page records
what the union is, which rows it hides something on, the 58-versus-59
reconciliation it was the cause of, the column that takes it apart, and — the
part the column does *not* fix — the union that remains.

Neither number in §2 is corrected here. `ec/tools/xdata_register_map.py` pins
58 mixed / 156 pair-only **within a program** and the CSV's own split is 59 /
155 **across** them; both are right, they count different sets, and the one
address that moved is named in both.

This is a report about a census that already exists. No register `status:`
moved, no register was read back, `xdata-clusters.csv` did not change a byte,
`registers.yaml` and `ec/ghidra/xdata-symbols.csv` were not involved, and no
hardware or Windows machine was involved — every number here re-derives from
the committed decompiled tree and the committed CSV.

## What "union across programs" means, precisely

`build()` walks `all_addrs`, and for an address both programs touch it makes
one `blank_entry()` and `absorb()`s the main-EC entry and the pd entry into it.
`absorb()` unions `spellings`, so `entry["spellings"]` afterwards holds
everything either program contributed, and the row's `spelled_as` renders that
set. `merge_group()` is the other half and runs *before* the absorb: it keys
spellings per program, which is why the census's own pair split (§4.7 of
`ec/annotations/xdata-register-map.md`) is measured over a main-EC entry that
has not yet met the pd one.

The two are separate address spaces — `ec/decompiled/pd/` is the
self-contained `ITE8850-PD` image with its own XDATA map, and a shared address
number is not a shared byte. So the union is a statement about *this address
number, as these two programs spell it*, and never about what either program
means by it. That is the `pd-xdata-overlap.md` distinction, and this column
makes it checkable rather than leaving it to be inferred from the `program`
column being present.

There are **49 `program=both` rows** and on **15** of them the two halves are
different sets of spellings. The other 34 are `DAT_EXTMEM` in both programs, so
their union is their main-EC half and nothing is hidden by the cell. A reader
can list the 15 from the committed file without running the tool:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$2=="both" { n=split($21,p,";"); delete seen; for (i=1;i<=n;i++) { split(p[i],q,"="); seen[q[2]]=1 } k=0; for (x in seen) k++; b++; if (k>1) { d++; list = list " " $1 } } END { print b, "both rows;", d, "of them have per-program halves that differ:" list }'
49 both rows; 15 of them have per-program halves that differ: 0x04A3 0x07D3 0x07D4 0x07D5 0x07D8 0x07D9 0x07DA 0x07F3 0x07F6 0x0809 0x080C 0x080D 0x0834 0x0835 0x0836
```

Eleven of the 15 are the `symbol`-versus-`DAT_EXTMEM` rows §2 of the map
already documents for its own reason — `0x07D3`-`0x07D5`, `0x07D8`-`0x07DA`,
`0x07F3`, `0x07F6`, `0x0809`, `0x080C`, `0x080D` — where the exporter named
the address for the EC and `gen_xdata_symbols.py` refuses to name the PD program
at all. The remaining four are this issue's, and they are the four §2's table
presents as one kind of row.

## The four `both` rows that carry `pair-literal`

| address | main-EC | main-EC refs | pd | pd refs | row `refs` |
|---|---|---:|---|---:|---:|
| `0x04A3` | `pair-literal` | 7 | `DAT_EXTMEM` | 1 | 8 |
| `0x0834` | `DAT_EXTMEM+pair-literal` | 48 (1 + 47) | `DAT_EXTMEM` | 18 | 66 |
| `0x0835` | `DAT_EXTMEM+pair-literal` | 48 (1 + 47) | `DAT_EXTMEM` | 4 | 52 |
| `0x0836` | `DAT_EXTMEM+pair-literal` | 9 (1 + 8) | `DAT_EXTMEM` | 4 | 13 |

**All four are a cross-program shape, and only three of them are mixed inside
the main EC.** `0x04A3` is the exception the tool's 58-versus-59 pins are
measured on: its seven main-EC references are *all* reached through an
accessor, and its single pd reference is a `DAT_EXTMEM_` token. The CSV's one
column cannot say which of the two programs contributed which token, and §2's
table gave the four as one row of the kind "both · `DAT_EXTMEM+pair-literal` · 4
· 139" — which is arithmetically true and, read as a statement about either
program, wrong for one of the four.

`0x04A3` is worth reading as a row, because it is the one where the union is
load-bearing and it is otherwise unremarkable. Its `functions` cell names six
main-EC routines and one pd routine:

```console
$ grep '^0x04A3,' ec/annotations/xdata-registers.csv | cut -d, -f1,2,3,6,17,21
0x04A3,both,DAT_EXTMEM+pair-literal,8,bank1:0xAD7D=forwarder_to_af06 [forwarder]; bank1:0xAF06=gate_0490_04ff_0505_then_call_b0d1 [logic]; bank1:0xAF32=FUN_CODE_af32; bank1:0xB0D1=step_index_056b_update_0495_0493 [state]; bank1:0xC392=FUN_CODE_c392; bank1:0xC3A0=dec_0622_when_04a2_below_0cee [writer]; pd:0xF22E=read_04a3_then_call_9a90 [reader],main-ec=pair-literal;pd=DAT_EXTMEM
```

Seven bank1 sites reach it as a literal argument to one of the seven pair
accessors (§4.7 of the map) and the PD image's single site reads it as a
token. Nothing here says the two programs agree about what the byte is, and
the column is not a claim that they do.

## The 58-versus-59 reconciliation

`PAIR_ROWS_MIXED = 58` sits beside `PAIR_ROWS = 214` in the tool, and the
tool's own comment used to explain the 58 by pointing at the CSV's 59. The
number is a count over **one program's** entries: every pair-reached address is
a main-EC one, because the PD image's own accessor `read_be16_from_dptr` is
called once with no argument, so `merge_group()`'s main-EC entry for `0x04A3`
carries `pair-literal` alone and the address counts as pair-only. The CSV
counts **the union**, where the same row carries `DAT_EXTMEM` too and counts as
mixed.

| set | mixed | pair-only | total |
|---|---:|---:|---:|
| within one program (`PAIR_ROWS_MIXED`, `PAIR_ROWS_PAIR_ONLY`) | 58 | 156 | 214 |
| the CSV's union (`spelled_as`) | 59 | 155 | 214 |

The symmetric difference of the two mixed sets is `0x04A3` alone, in both
directions — 58 + 156 and 59 + 155 both close on 214, and the union can only
ever *add* a spelling, so the difference can only run one way. The direction is
not a coincidence: **no pd-program entry carries `pair-literal` at all**, so a
`both` row's union differs from its main-EC half only by picking up a pd token.
That is also why these four are the only `both` rows the pair pass reaches.

From the committed file, with no tool:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$3 ~ /pair-literal/ {if ($3 ~ /\+/) m++; else o++} END {print "CSV union:", m, "mixed /", o, "pair-only"}'
CSV union: 59 mixed / 155 pair-only
$ tail -n +2 ec/annotations/xdata-registers.csv | cut -d, -f21 | grep -o "pair-literal" | wc -l
214
```

The 214 is the count of `pair-literal` clauses in the new column — one per
pair-reached address, because there is exactly one clause per program that
reaches one, and only the main EC ever does. `awk -F,` is safe on this file
because no cell before column 21 can contain a comma; the new cell is
comma-free for the same reason (`+`, `;` and `=` only), which is why appending
it could not break the committed positional readers in
`xdata-census-totals.md` and `xdata-export-ownership-page-census.md`.

## `spellings_by_program`, and the two assertions that hold it

The registers CSV now carries a second spelling column, **appended last** (21,
after `sources_beyond`):

> `spellings_by_program` — the same vocabulary as `spelled_as`, one
> `program=<spellings>` clause per program the row touches. `main-ec=<…>` alone
> on a main-EC row, `pd=<…>` alone on a pd one, and
> `main-ec=<…>;pd=<…>` on a `both` row. Its token set is `spelled_as`'s token
> set on every row: it **partitions** the union, it does not add to it.

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | cut -d, -f1,2,3,21 | grep -E '^0x(04A3|083[456]),'
0x04A3,both,DAT_EXTMEM+pair-literal,main-ec=pair-literal;pd=DAT_EXTMEM
0x0834,both,DAT_EXTMEM+pair-literal,main-ec=DAT_EXTMEM+pair-literal;pd=DAT_EXTMEM
0x0835,both,DAT_EXTMEM+pair-literal,main-ec=DAT_EXTMEM+pair-literal;pd=DAT_EXTMEM
0x0836,both,DAT_EXTMEM+pair-literal,main-ec=DAT_EXTMEM+pair-literal;pd=DAT_EXTMEM
```

The column is **appended** rather than placed beside `spelled_as` on purpose.
`docs/findings/xdata-census-totals.md` reads this file by field position — it
sums `$6` and adds up `$7`-`$11` — and that page already names "the thing that
would break first if a column were added" as `addr`…`cluster_id` being
comma-free. Inserting beside column 3 moves every one of those fields;
appending leaves each meaning what it means today:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{s+=$6} END{print s}'
15696
```

Unchanged, and unchanged is the point. No committed Python tool reads this CSV
by index — `check_cluster_citations.py`, `check_site_census.py`,
`test_xdata_cluster_names.py`, `rank_common_runtime.py` and
`check_capture_claims.py` all go through `csv.DictReader` or a regex over a
named cell, and the one positional reader in `check_cluster_citations.py`
parses markdown table rows rather than this file.

The contract is defined in the tool's module docstring beside the
`spelled_as`/`name` one, and `--self-test` holds it with three assertions that
all read the **committed** file rather than a fresh generation — the whole of
the issue is that the artifact a reader opens cannot answer the question, so a
check against what this run would write would not be answering it:

1. on all 1,326 committed rows the token set of `spellings_by_program` equals
   the token set of `spelled_as`;
2. the four rows above carry the halves and the per-program reference figures
   in the table, and each row's single `refs` cell is still the sum of its two
   halves;
3. the per-program mixed set and the CSV's mixed set differ by exactly
   `PAIR_UNION_ONLY` in both directions, and 58 + 156 == 59 + 155 == 214.

A second cross-program row would keep the arithmetic true and quietly move a
published figure, so (3) is asserted as a set relation rather than as two equal
counts. `--self-test` is deliberately not in
`.github/scripts/agent-gates.sh`; that file says why, and the PR quotes the
three lines rather than claiming a gate covers them. The gate that does run is
`python3 ec/tools/xdata_register_map.py --check`, and it is what holds the
column from drifting at all — the committed file is compared row for row
against a fresh generation.

The tool's own pin block now carries the reconciliation, and the four rows are
pinned in `PAIR_BOTH_PAIR_LITERAL` beside it. Nothing that used to be in the
`PAIR_ROWS_MIXED` comment was wrong, so nothing is corrected in place: this is
a promotion, from prose that a reader had to find, to a column and three
assertions that fail on their own.

## The union that remains, stated rather than left to be found

The column splits **the spelling**. It does not split anything else on a `both`
row, and a reader who assumes it did would be wrong in a second place. On all
49 `both` rows these stay sums over the two programs:

* **`refs`** — 1,202 of the census's 15,696 references, counted twice across
  the two address spaces and once across the row. The four rows' halves are in
  the table above; e.g. `0x04A3`'s 8 is 7 main-EC plus 1 pd.
* **the five direction buckets** — likewise summed. For `0x04A3` the main-EC
  seven are 4 `read` and 3 `write` and the pd one is 1 `address-taken`, so the
  row reads 4 / 3 / 0 / 0 / 1 and a reader looking for a writer sees three
  bank1 writes and a single pd address-taken with nothing in the cell to say
  which program each came from. For `0x0834` the main-EC 48 are 40 `read`,
  7 `write` and 1 `passed-to-call` against the pd 18's 16 `read`, 1
  `read+write` and 1 `write`.
* **`readers`, `writers`, `functions_touched`, `single_function`,
  `co_reading`, `sources_beyond`, `functions`** — function *names* keep their
  program prefix (`bank1:0xAD7D=…`, `pd:0xF22E=…`), so those cells are
  attributable by reading them; their counts are not split.

None of this is fixed here. Splitting per-program `refs` and buckets would move
every published reference figure the census quotes, and re-keying §2's `both`
rows per program would move that table's own `distinct` total from 1,326 to
1,375 (1,218 main-EC + 157 pd program-addresses) and invalidate the three
superseded-table correction blocks §2 carries. Both are their own changes with
their own corrections. The `functions` cell already answers the per-program
question for sites, which is why it is listed as the exception above rather
than as an open item.

*(Correction, 2026-09-26, issue #713. The paragraph above is **incomplete, not
wrong**, and it is kept as written: `refs` on a `both` row **is** still the sum
of the two halves, and the five unsuffixed buckets still are, which is what
`xdata-registers.csv` carries today. What has changed is that the row now also
carries a per-program answer beside the summed one — the twelve columns at
22–33, `refs_main_ec` / `refs_pd` and each of the five buckets once per program,
written on every row rather than only on the 49 `both` ones. So the bullets
above are now true of the *unsuffixed* columns and no longer describe the whole
row, and "None of this is fixed here" is no longer true of `refs` and the
buckets: it is still true of the function counts and of §2's table, which the
re-keying half of this issue's follow-up has not done. Nothing was retracted and
no figure moved — the 1,202 is still the `both` rows' `refs` column summed, and
it is now also 947 main-EC + 255 pd. The write-up is
[`xdata-per-program-counts.md`](xdata-per-program-counts.md), and the three
places in the tree that said no per-program count exists carry the same dated
correction beside the original sentence.)*

## What this does not establish

The column says how each program **spells** an address, not what either one
means by it, and not that the two agree — `0x04A3` being `pair-literal` in the
main EC and `DAT_EXTMEM` in the PD image is a fact about two decompiled text
trees and says nothing about whether the two images are looking at the same
register. Every count here is over the committed decompiled tree, so a call
site the exporter dropped is still out of reach, and "not in this set" is
"not found by this method" and never "absent". Nothing here claims the EC acts
on any of these bytes: a resolved pair site is a **static** read or write, which
§4.7 of `ec/annotations/xdata-register-map.md` states at length. And no
`pd` row became an EC-register claim — the column's labels are the same
`main-ec` / `pd` tokens `cluster_id` uses, and the separation it records is the
one §3 of that page already insists on.
