# The per-program function counts: `readers`, `writers`, `functions_touched`, `single_function`, `co_reading` and `sources_beyond`, split (issue #907)

**Issue #907, 2026-10-02.** [`xdata-per-program-counts.md`](xdata-per-program-counts.md)
split `refs` and the five direction buckets per program and left one sentence
open: "Whether their *counts* should get the same treatment is a real question
this change does not answer." Those are the *function* counts, and this is the
answer: **twelve more columns at 34–45**, appended, written on every row, from
the same per-program entries the reference split already reads. The unsuffixed
`readers`, `writers`, `functions_touched`, `single_function`, `co_reading` and
`sources_beyond` stay the row's own figures, exactly as `refs` and the five
buckets did.

The question was worth asking because the summed cell is not a mild imprecision
on a `both` row. `0x080C` reads `functions_touched` 49, `writers` 48 and
`co_reading` 47, and 48 of those functions are the main EC's while the single
pd one is the writer — so the row's `writers` cell is a statement about the
wrong program, in the same way `0x04A3`'s 4 / 3 / 0 / 0 / 1 was before the
reference split.

This is a report about a census that already exists. No register `status:`
moved, no register was read back, `xdata-clusters.csv` did not change a byte,
`registers.yaml` and `ec/ghidra/xdata-symbols.csv` were not involved, and no
hardware or Windows machine was involved — every number here re-derives from
the committed decompiled tree and the committed CSV.

## What the twelve columns are, and where they sit

Columns **34–45**, appended after `address-taken_pd`:

| | main EC | pd image |
|---|---|---|
| readers | `readers_main_ec` | `readers_pd` |
| writers | `writers_main_ec` | `writers_pd` |
| touching functions | `functions_touched_main_ec` | `functions_touched_pd` |
| single-function | `single_function_main_ec` | `single_function_pd` |
| co-reading | `co_reading_main_ec` | `co_reading_pd` |
| beyond the group | `sources_beyond_main_ec` | `sources_beyond_pd` |

**Metric first, then program,** the same ordering rule the twelve before them
follow and for the same reason: one program's whole half is a contiguous run,
so `cut -d, -f34,36,38,40,42,44` is the main EC and the odd fields are the pd
image's. The metrics sit in the order their unsuffixed cells do — `$12`, `$13`,
`$14`, `$15`, `$19`, `$20` — so `$12` and `$34` answer the same question about
different address spaces. `_pd`, not `_pd_image`, for the reason
`program_suffix()` records: this CSV's vocabulary is already `pd`.

```console
$ head -1 ec/annotations/xdata-registers.csv | cut -d, -f34,36,38,40,42,44
readers_main_ec,writers_main_ec,functions_touched_main_ec,single_function_main_ec,co_reading_main_ec,sources_beyond_main_ec
$ wc -l < ec/annotations/xdata-registers.csv; head -1 ec/annotations/xdata-registers.csv | awk -F, '{print NF}'
1327
45
```

**Written on every row, not only on the 49 `both` ones.** On a `program=main-ec`
row `readers_main_ec` is that row's whole `readers` and `readers_pd` is `0`; on
a `pd` row the reverse. The alternative is a column blank on 1,277 of 1,326
rows, which is a shape no `csv.DictReader` consumer can rely on, and it is what
makes the per-row partition checkable corpus-wide rather than only on the 49
rows where the halves differ.

**Comma-free is mechanical, not a rule.** Ten `int`s and two `yes`/`no`.
`per_program_function_counts_of()` has no formatting path in which a thousands
separator, a unit suffix or a comment could reach a cell, which is what keeps
the `awk -F,` readers in §"The positional readers, re-run" exact.

## The partition is arithmetic, not approximate

A main-EC function key is `(common | bank0 | bank1, addr)` and a pd one is
`(pd, addr)`. The two key sets are **disjoint**, so `len(A ∪ B) == len(A) +
len(B)` exactly — which is why `readers == readers_main_ec + readers_pd` holds on
a `both` row rather than holding closely, and why the same is true of all four
other counts. The corpus arithmetic is the same statement over more rows:

| metric | main EC | pd | sum | row's own unsuffixed cells |
|---|---:|---:|---:|---:|
| readers | 4,600 | 188 | 4,788 | 4,788 |
| writers | 4,854 | 229 | 5,083 | 5,083 |
| functions_touched | 6,905 | 351 | 7,256 | 7,256 |
| co_reading | 3,319 | 35 | 3,354 | 3,354 |
| sources_beyond | 3,586 | 316 | 3,902 | 3,902 |

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{m+=$34;p+=$35;w+=$36;q+=$37;t+=$38;u+=$39} END{print m, p, w, q, t, u}'
4600 188 4854 229 6905 351
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$34 + $35 != $12 || $36 + $37 != $13 || $38 + $39 != $14 || $42 + $43 != $19 || $44 + $45 != $20' | wc -l
0
```

The last line is the per-row partition over all 1,326 rows, not only the 49.
Every figure in the table was re-derived from the committed CSV rather than
transcribed from anything written before this change; one of them, the corpus
`readers` total, came out at 4,788 where a working figure for this split had
said 4,787, and the measured value is the one pinned.

**`single_function` is the one metric of the six that is not a sum.** It is
`len(funcs) == 1` *in that program*, so `$40` and `$41` do not add to `$15` and
neither of them has to equal it: a `main-ec` row that touches one function reads
`yes` at `$15` and `no` in the pd half, which has no function at all. What holds
is `single_function_<g> == "yes"` exactly where that program's own
`functions_touched_<g>` is `1`. Because the two halves are `yes`/`no` rather
than numbers, `awk -F,` reads both as `0`, so no arithmetic reader over this file
can be tempted to add them; the identity is asserted in `--self-test` instead.

## The 49 `both` rows, split

| address | main-EC fns | pd fns | readers (main / pd) | writers (main / pd) | co_reading (main / pd) | sources_beyond (main / pd) | single_function (main / pd) |
|---|---:|---:|---|---|---|---|---|
| `0x00D0` | 1 | 1 | 0 / 0 | 0 / 1 | 0 / 0 | 1 / 1 | yes / yes |
| `0x0300` | 1 | 2 | 0 / 0 | 0 / 1 | 0 / 0 | 1 / 2 | yes / no |
| `0x04A3` | 6 | 1 | 3 / 0 | 3 / 0 | 0 / 0 | 6 / 1 | no / yes |
| `0x07D3` | 3 | 5 | 2 / 3 | 2 / 5 | 0 / 0 | 3 / 5 | no / no |
| `0x07D4` | 3 | 12 | 3 / 8 | 3 / 6 | 2 / 0 | 1 / 12 | no / no |
| `0x07D5` | 5 | 7 | 3 / 1 | 5 / 4 | 2 / 0 | 3 / 7 | no / no |
| `0x07D8` | 1 | 4 | 0 / 3 | 1 / 4 | 0 / 0 | 1 / 4 | yes / no |
| `0x07D9` | 1 | 2 | 0 / 0 | 1 / 2 | 0 / 0 | 1 / 2 | yes / no |
| `0x07DA` | 1 | 3 | 0 / 1 | 1 / 2 | 0 / 0 | 1 / 3 | yes / no |
| `0x07F3` | 44 | 1 | 43 / 1 | 44 / 0 | 42 / 0 | 2 / 1 | no / yes |
| `0x07F6` | 41 | 1 | 41 / 1 | 37 / 1 | 36 / 0 | 5 / 1 | no / yes |
| `0x07FD` | 6 | 1 | 1 / 0 | 3 / 1 | 4 / 0 | 2 / 1 | no / yes |
| `0x07FE` | 6 | 1 | 1 / 1 | 6 / 1 | 4 / 0 | 2 / 1 | no / yes |
| `0x07FF` | 6 | 1 | 1 / 1 | 6 / 1 | 4 / 0 | 2 / 1 | no / yes |
| `0x0801` | 8 | 1 | 8 / 1 | 3 / 0 | 0 / 0 | 8 / 1 | no / yes |
| `0x0803` | 1 | 5 | 0 / 3 | 1 / 2 | 0 / 0 | 1 / 5 | yes / no |
| `0x0804` | 1 | 3 | 1 / 1 | 1 / 1 | 0 / 0 | 1 / 3 | yes / no |
| `0x0805` | 4 | 4 | 0 / 1 | 3 / 1 | 0 / 0 | 4 / 4 | no / no |
| `0x0806` | 6 | 1 | 3 / 0 | 4 / 1 | 1 / 0 | 5 / 1 | no / yes |
| `0x0808` | 1 | 1 | 0 / 0 | 0 / 1 | 0 / 0 | 1 / 1 | yes / yes |
| `0x0809` | 43 | 3 | 42 / 2 | 43 / 2 | 42 / 0 | 1 / 3 | no / no |
| `0x080B` | 1 | 2 | 0 / 0 | 1 / 2 | 0 / 0 | 1 / 2 | yes / no |
| `0x080C` | 48 | 1 | 3 / 0 | 47 / 1 | 47 / 0 | 1 / 1 | no / yes |
| `0x080D` | 45 | 3 | 43 / 1 | 44 / 2 | 42 / 0 | 3 / 3 | no / no |
| `0x080E` | 2 | 2 | 1 / 1 | 1 / 2 | 0 / 0 | 2 / 2 | no / no |
| `0x080F` | 4 | 2 | 2 / 0 | 3 / 2 | 1 / 0 | 3 / 2 | no / no |
| `0x0815` | 2 | 2 | 2 / 1 | 0 / 1 | 0 / 0 | 2 / 2 | no / no |
| `0x0816` | 2 | 1 | 1 / 0 | 2 / 1 | 0 / 0 | 2 / 1 | no / yes |
| `0x0817` | 11 | 1 | 3 / 0 | 10 / 1 | 0 / 0 | 11 / 1 | no / yes |
| `0x0819` | 1 | 2 | 0 / 1 | 1 / 1 | 0 / 0 | 1 / 2 | yes / no |
| `0x0825` | 4 | 1 | 1 / 1 | 3 / 1 | 1 / 0 | 3 / 1 | no / yes |
| `0x0832` | 18 | 9 | 18 / 5 | 18 / 4 | 4 / 0 | 14 / 9 | no / no |
| `0x0834` | 30 | 5 | 29 / 4 | 6 / 2 | 15 / 0 | 15 / 5 | no / no |
| `0x0835` | 30 | 3 | 29 / 2 | 6 / 2 | 15 / 0 | 15 / 3 | no / no |
| `0x0836` | 5 | 2 | 4 / 2 | 4 / 0 | 4 / 0 | 1 / 2 | no / no |
| `0x083A` | 4 | 1 | 0 / 0 | 3 / 1 | 0 / 0 | 4 / 1 | no / yes |
| `0x083B` | 4 | 1 | 0 / 0 | 3 / 1 | 0 / 0 | 4 / 1 | no / yes |
| `0x083C` | 2 | 1 | 0 / 1 | 1 / 1 | 0 / 0 | 2 / 1 | no / yes |
| `0x083D` | 2 | 4 | 0 / 1 | 1 / 2 | 0 / 0 | 2 / 4 | no / no |
| `0x0845` | 4 | 1 | 4 / 1 | 1 / 1 | 3 / 0 | 1 / 1 | no / yes |
| `0x0846` | 2 | 1 | 2 / 1 | 0 / 1 | 0 / 0 | 2 / 1 | no / yes |
| `0x0848` | 5 | 1 | 5 / 0 | 4 / 1 | 4 / 0 | 1 / 1 | no / yes |
| `0x084C` | 1 | 2 | 1 / 1 | 1 / 1 | 1 / 0 | 0 / 2 | yes / no |
| `0x0851` | 1 | 1 | 1 / 0 | 1 / 1 | 0 / 0 | 1 / 1 | yes / yes |
| `0x0852` | 4 | 1 | 3 / 1 | 4 / 0 | 0 / 0 | 4 / 1 | no / yes |
| `0x0855` | 3 | 1 | 0 / 0 | 2 / 1 | 0 / 0 | 3 / 1 | no / yes |
| `0x0856` | 3 | 2 | 0 / 0 | 2 / 2 | 0 / 0 | 3 / 2 | no / no |
| `0x097E` | 1 | 1 | 1 / 0 | 1 / 1 | 0 / 0 | 1 / 1 | yes / yes |
| `0x097F` | 6 | 1 | 6 / 1 | 5 / 0 | 3 / 0 | 3 / 1 | no / yes |

Every row is `program=both`, so every row has a function in each half — which
is why the `both` half of the "a `both` row carries a touching function in both
programs" assertion is a real one and not a tautology: an address in
`groups[g]` has at least one reference there by construction.

**`0x080C` and `0x07F6`, the two worked rows, and why the summed cell
misleads.** They are the two directions the split has to get right: `0x080C` is
48 main-EC functions against a single pd one and is nearly all **writers** —
3 of the 48 main-EC functions read it — while `0x07F6` is 41 against 1 and is
nearly all **readers**, 37 of the 41 writing it. On both rows the single pd
function is a writer, so the row's own `writers` cell is one higher than the main
EC's: 48 against 47, and 38 against 37. Both rows read `single_function=no` and
both have `single_function_pd=yes`, because one program saw one function and the
other saw dozens.

```console
$ for a in 0x080C 0x07F6 0x00D0; do echo -n "$a  "; grep "^$a," ec/annotations/xdata-registers.csv | cut -d, -f1,2,12,13,14,15,19,20,34-45; done
0x080C  0x080C,both,3,48,49,no,47,2,3,0,47,1,48,1,no,yes,47,0,1,1
0x07F6  0x07F6,both,42,38,42,no,36,6,41,1,37,1,41,1,no,yes,36,0,5,1
0x00D0  0x00D0,both,0,1,2,no,0,2,0,0,0,1,1,1,yes,yes,0,0,1,1
```

Read the `0x00D0` line: `$14` is `2` and `$15` is `no`, and the split says
`1 / 1` with `yes / yes`. **That is the fact the summed cell cannot carry** —
a row it calls "not a single-function row" is two single-function rows, one per
address space. Four rows are like it: `0x00D0`, `0x0808`, `0x0851` and
`0x097E`. Over the 49 `both` rows, 13 have exactly one main-EC function and 25
have exactly one pd function, so both halves earn their column.

## Which of the six are re-derivable from the `functions` cell, and which are not

This is the issue's second half, and the answer is not uniform.

The `functions` cell (column 17) is semicolon-separated and every site carries
its program as a prefix — `bank0:`, `bank1:`, `common:` for the main EC and
`pd:` for the pd image. Over the 49 `both` rows the prefixes are 79 `bank0:`,
353 `bank1:`, 2 `common:` and 115 `pd:`, which is 434 main-EC against 115 pd.

- **`functions_touched`** — re-derivable. The cell's prefix partition *is* the
  count's partition, and splitting it reproduces `functions_touched` per program
  on every row.
- **`co_reading` and `sources_beyond`** — re-derivable, but only *with*
  `group_of`: the per-program figure is the number of a program's own sites that
  are in a co-reading group, and the group relation is not in the cell. Given
  it, both fall out of the same split (`sources_beyond` as the complement).
- **`readers` and `writers`** — **not** re-derivable. The cell's `[reader]` /
  `[writer]` / `[logic]` / `[state]` labels are `ftype` documentation out of
  `ghidra-functions.csv`, not this classifier's per-address output. Reading a
  per-program `readers` off them would be a second reading of a comment. The
  halves are computed from each program's own `dirs` map instead, which is
  exactly the computation `build()` already does for the unsuffixed cell — so a
  per-program `readers` is the same measurement as the summed one rather than a
  second classifier.
- **`single_function`** — not a sum at all, so "re-derivable" is the wrong
  question; it is `functions_touched == 1` on each half.

That is why `functions_touched`'s cell is used as the *cross-check* and never as
the source of a number:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$2=="both"{print $17}' | tr ';' '\n' | grep -o '\(bank0\|bank1\|common\|pd\):' | sort | uniq -c
     79 bank0:
    353 bank1:
      2 common:
    115 pd:
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$42 + $43 != $19 || $44 + $45 != $20 || $42 + $44 != $38 || $43 + $45 != $39' | wc -l
0
```

The second command is the **new identity**, and it is the one the split makes
available for the first time: `co_reading + sources_beyond == functions_touched`
is what the row's own three cells already share, and per program it becomes two
identities rather than one. It is asserted per program *and* per row, which is
the part the `both` rows need — a main-EC function is never a co-reading of a pd
one, so `0x080C`'s main-EC half is 47 + 1 = 48 while its pd half is 0 + 1 = 1.

## `0x07D1`, where the issue's figure does not match the committed CSV

**The issue's analysis of this split says "`0x07D1` is 1 against 76" and that a
reader asking how many functions touch it "gets 77".** On the committed file
`0x07D1` is a **`pd`-only row**: 73 references, 16 touching functions, every one
of them `pd:`, and nothing in the main EC. It is not a `both` row, it has
nothing to split, and its `functions_touched` is 16, not 77.

```console
$ grep '^0x07D1,' ec/annotations/xdata-registers.csv | cut -d, -f1,2,6,14
0x07D1,pd,73,16
$ grep '^0x07D1,' ec/annotations/xdata-registers.csv | cut -d, -f17 | tr ';' '\n' | grep -o '\(bank0\|bank1\|common\|pd\):' | sort | uniq -c
     16 pd:
```

The 1-against-N shape the issue describes is real in this block, but it
belongs to `0x07D1`'s neighbours — `0x07D8` 1 main against 4 pd, `0x07D9` 1
against 2, `0x07DA` 1 against 3 — and to `0x07D4` at 3 against 12 and `0x07D5`
at 5 against 7, both of which the issue states correctly. The 77 is not
reproducible from the committed CSV and no reading of it is offered here: a
figure that does not re-derive is recorded as not matching, not replaced by a
guess at what it was. The corrected figure is the one the CSV prints.

## The positional readers, re-run

The append-not-insert argument rests on these commands still meaning what they
meant. Every `awk -F,` / `cut -d,` reader published in
[`xdata-per-program-counts.md`](xdata-per-program-counts.md),
[`xdata-spelled-as-union.md`](xdata-spelled-as-union.md) and
`xdata-census-totals.md` reads a field at or before `$22`, and none of them
moved.

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{s+=$6} END{print s}'
15696
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$22 + $23 != $6' | wc -l
0
$ tail -n +2 ec/annotations/xdata-registers.csv | cut -d, -f21 | grep -o pair-literal | wc -l
214
```

`$21` is still `spellings_by_program` and still selects it. It is no longer the
**last** column, and a reader who asks for "the last column" now gets
`sources_beyond_pd` rather than `address-taken_pd`. The two blocks are
contiguous, so a `cut` for either program's whole half is six fields:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | cut -d, -f34,36,38,40,42,44 | head -1
0,13,13,no,0,13
$ tail -n +2 ec/annotations/xdata-registers.csv | cut -d, -f35,37,39,41,43,45 | head -1
0,0,0,no,0,0
```

## What changed, and what did not

`readers`, `writers`, `functions_touched`, `single_function`, `co_reading`,
`sources_beyond`, `name`, `functions`, `cluster_key`, `refs` and the five
buckets are all exactly what they were, byte for byte, and so is every `ORACLE`,
`BUCKET_TOTALS` and `HAND_CHECKED` value in the tool. `PER_PROGRAM` **gains**
this block's pins beside its existing ones and changes none of them. **No
function was added, dropped, de-duplicated or re-bucketed**, so the cluster
ranking is untouched, `cluster_id` keeps its exact values, and
`xdata-clusters.csv` regenerates byte-identically — which is the strongest single
statement available that nothing moved:

```console
$ md5sum ec/annotations/xdata-clusters.csv
3098206dbb670383c2c37db3b887f42f  ec/annotations/xdata-clusters.csv
$ python3 ec/tools/xdata_register_map.py >/dev/null
$ md5sum ec/annotations/xdata-clusters.csv
3098206dbb670383c2c37db3b887f42f  ec/annotations/xdata-clusters.csv
```

The only edited generated file is `ec/annotations/xdata-registers.csv` itself,
written by the tool's default mode and never by hand. `check_citation_lines.py`'s
`xdata-registers.csv:NNN` pointers are unaffected: adding columns at the end of
the row moves no line.

## The assertions, and where they live

Six `--self-test` assertions, appended to the `#713` block in
`ec/tools/xdata_register_map.py`'s `self_test()`. **Four** are what the issue
asks for, in the order it asks for them; two are split further than that, because
one message would otherwise have had to carry two unrelated failures with a
single verdict. `#713`'s four and `#711`'s three are left as they were, with one
exception recorded below.

1. **Position, and the per-row partition, on every row.** The twelve at 34–45
   with `address-taken_pd` still the last of the twelve before them and
   `spellings_by_program` still at 21; on all 1,326 rows each of the five
   unsuffixed counts is the sum of its two halves; `single_function` reads `yes`
   in a half exactly where that program's own `functions_touched` is 1 (a derived
   identity, held as such and *not* as a sum); a single-program row carries
   nothing for the program it is not, and a `both` row carries a touching
   function in **both** halves.
2. **Attribution against a fresh generation.** Every cell is the per-program
   entry it claims to be, read against `groups` and `group_of` rather than
   against a rendered row; an address in no program of `groups` expects a zero,
   not a skip. `want` is written out again in the assertion rather than taken
   from `per_program_function_counts_of()`, for the reason #713's equivalent
   writes its own.
3. **The `functions` cell as an independent reading.** On all 1,326 rows the
   non-`pd:` entries are `functions_touched_main_ec` and the `pd:` ones
   `functions_touched_pd` — a derivation from the rendered cell that shares no
   code with `groups`, and the one check a column written wrongly in *both*
   `build()` and the CSV still fails.
4. **The per-program identity.** `co_reading_<g> + sources_beyond_<g> ==
   functions_touched_<g>`, per program and per row.
5. **The aggregate reconciliation.** Over all 1,326 rows the halves sum to the
   corpus `readers` / `writers` / `functions_touched` / `co_reading` /
   `sources_beyond` totals, over the 49 `both` rows to that subset's, and each
   is held against both the rows' own unsuffixed cells and the pin — so a column
   that moved a function between programs keeps the per-row partition true and
   fails here.
6. **The `single_function` split, and the worked rows.** All 49 `both` rows read
   `single_function=no`, and the halves are not all `no`: 13 / 25 / 4, the four
   addresses by name, `0x080C` and `0x07F6` as the two worked rows. **One leg of
   this is checked against prose nobody re-derived for this change**:
   `HAND_CHECKED["0x0440"]["writers"] == 0`, read off the decompiled C by hand and
   carried as the "**No writer**" prose `registers.yaml` records, has to equal
   the new `writers_main_ec`.

All six read the **committed** registers CSV, because the whole of the issue is
that the artifact a reader opens could not answer the question, so a check
against what this run would write would not be answering it. What differs is
what each holds those committed cells against: four of them against the census
or against arithmetic over it, #2 is the deliberate exception and holds them
against a *fresh* generation, and #3 reads the committed `functions` cell — the
census's own rendering of the same partition — rather than either. Every new
`PER_PROGRAM` key is read by one of the six and named in that one's message,
which is the rule issue #849 corrected, and the failure messages cap the
disagreeing rows at eight and **count the overflow** the way the assertions
above them already do.

```console
$ python3 ec/tools/xdata_register_map.py --check
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
/home/runner/work/tongfang-gm7mg7p-re/tongfang-gm7mg7p-re/ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
/home/runner/work/tongfang-gm7mg7p-re/tongfang-gm7mg7p-re/ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
$ python3 ec/tools/xdata_register_map.py --self-test
  ...
  all assertions passed
```

Both are in the cheap gate: `.github/scripts/agent-gates.sh` runs
`python3 "$tool" --check && python3 "$tool" --self-test` for this tool, so none
of these six can be removed without CI going red.

### The one existing assertion this change did touch, and why

#713's first assertion ends `REGISTER_COLUMNS[21:] == list(columns)` — "the
twelve sit contiguously right after `spellings_by_program`". That slice became
false the moment a second block was appended behind them, and it would have
failed for the right reason and named the wrong one. It now reads
`REGISTER_COLUMNS[21:21 + len(columns)]`, which asserts **the same property** —
the twelve are contiguous and immediately follow `spellings_by_program` — and
does not care what is appended after them. It is a narrowing of the *slice*, not
of the claim; nothing #713's assertion holds has been dropped, and #713's other
three are untouched.

## What this does not establish

**A zero in the other program's column means the census found no reference in
that program, and nothing more.** It is "not found by this method over the
committed decompiled tree" — never "absent from the image", never a claim that
the program cannot reach the byte, and never a prediction about a future export.
This is `CLAUDE.md`'s calibration rule and
`ec/annotations/registers.yaml`'s own caveat, restated for a block of columns
that makes the zeros much more numerous and therefore more quotable. A
`functions_touched_pd` of `0` on a `main-ec` row says what the `program` column
already said.

**A per-program `writers` is still a static shape.** `writers_main_ec = 47` on
`0x080C` is forty-seven `=`-shaped occurrences in decompiled C. It is not
evidence that the EC acts on that byte, and no column here is. §4.7 of
`ec/annotations/xdata-register-map.md` states this at length and nothing in this
change touches it.

**A split of a function *count* is not a split of a function *identity*.** The
two programs' halves are counted over two disjoint key sets, which is what makes
the arithmetic exact; it does not make the two counts about the same routine.
`0x080C`'s main-EC 48 and its pd 1 are 48 bank0/bank1/common routines and one
`pd` routine, and the row says which is which without saying they correspond.

**Two programs touching one address *number* is still a collision in the
numbering, not a shared byte.** `ec/decompiled/pd/` is the self-contained
`ITE8850-PD` image with its own XDATA map. A `both` row is two address spaces
described side by side, never one register counted two ways. No pd half became
an EC-register claim, and the suffixes are the same `main-ec` / `pd` tokens the
`program` column and `cluster_id` already use.

**The split is over the committed decompiled tree, so a call site the exporter
dropped is still out of reach** — on both halves.

**`registers.yaml`'s `static_refs_main_ec` / `static_refs_pd_image` figures
were not cross-checked against these columns, and are not expected to agree.**
They come from `register_ref_table.py` over the firmware image, a different
method over different bytes, and no `status:` moved and none of those figures was
refreshed.

## Deliberately not done, and why

- **A per-program `functions` *cell*.** The per-program *site* question is
  already answerable by reading the existing cell's prefixes — §above shows that
  reading reproducing `functions_touched` on every row — so a
  `functions_by_program` column would duplicate what is there for no count that
  is not now a column.
- **Moving the unsuffixed cells.** `readers` / `writers` / `functions_touched` /
  `co_reading` / `sources_beyond` stay summed over both programs, exactly as
  `refs` and the five buckets did. Moving them would move every published figure
  the census quotes, and the per-program question is now answerable beside them.
- **Splitting a *cluster* column.** `functions_touched` and `shared_functions`
  feed `xdata-clusters.csv`; a cluster column must not be split in the same
  change. That is why the clusters CSV's byte-identical regeneration is
  recorded above as a control rather than as an expectation.
- **A per-program guard-off measurement** — what the `==` guard moves *within*
  each program rather than in the summed total. Measurable from the same recipe
  as the one [`xdata-per-program-counts.md`](xdata-per-program-counts.md) left
  open; not this change.
- **Any live hardware or Windows run.** None is involved: every number here
  re-derives from the committed decompiled tree and the committed CSV. Nothing
  here is evidence that the EC acts on any byte.

## What growing the tool moved, on the record

Adding twelve columns means adding lines to `ec/tools/xdata_register_map.py`,
and a line number into that file is a **rank**: everything below it moves. Three
checks in this repository hold such pointers, and all three are re-pointed here
rather than left quietly wrong.

- **`check_eq_guard_citations.py`** holds nine `--no-eq-guard` anchors by name
  and requires each declared citation's `:NNN` to be the line the anchor is on
  today. **Every one of the nine moved** — by 27, 118, 181, 190 and 484 lines
  depending on where in the file it sits — and every declared citation across
  `docs/findings.md`, `ec/annotations/xdata-register-map.md`,
  `docs/findings/xdata-4-4-identity-rederivation.md` and
  `docs/findings/xdata-no-eq-guard-refusal-contract.md` was re-pointed to its
  anchor's new line. The tool's own rule is "hold the code, and let the number
  follow", and this is that: the anchor strings did not change, and no `:NNN`
  outside a `>` quotation was touched.
- **`test_check_doc_figure_pins.py`** holds two spans in the same file — the
  `check()` that reads `ORACLE["extmem_pd_distinct"]` and the one that reads
  `export_ownership.OWNERSHIP_ORACLE["largest_class"]` — because the property it
  checks is *which lines a checker reports*. Both moved (`:3744-3761` →
  `:3934-3951` (`:3971-3988` once merged with main) with its negative guard `:3734` → `:3924` (`:3961`), and `:4560-4566` →
  `:5044-5050` (`:5096-5102`)) and both were **re-measured against the file**, which is what
  that file's own comment history says to do at each step. The pair that moves
  together moved together, which is the point of holding both.
- **`check_pin_table_rows.py`** holds the per-pin table in
  `test-line-pin-census.md` against the census's own run, keyed on the citing
  line. The §2 clause above moved two citing lines in
  `ec/annotations/xdata-register-map.md` (`1617` → `1621`, `2997` → `3001`) with
  the cited text byte-identical, and both rows were re-anchored with the step
  recorded in the style the table already uses for the other eight.

**The rest of the class is not swept here.** There are over a hundred
`xdata_register_map.py:NNN` citations in the tree and **nothing holds them**:
`check_pin_table_rows.py` covers `test_*.py:NNN`, and
`check_eq_guard_citations.py` covers its own nine anchors and no more. The
general `.py:NNN` pointer checker that would is not in the tree, and
`check_eq_guard_citations.py`'s own header says so and names issue #868 as the
one whose write-up states that its fix needs one. Re-pointing a hundred-odd
citations a change did not author is its own work and this does not attempt it.
The six that [`xdata-0860-note-live-pointers.md`](xdata-0860-note-live-pointers.md)
re-pointed as *live* pointers are the exception, because that page says they are
live: they are re-measured in place there and in `docs/findings.md` §87, with the
old figures left visible beside the correction.

## Where the open question is now recorded

The sentence in [`xdata-per-program-counts.md`](xdata-per-program-counts.md)
that named this question open is kept as written, with a dated correction beside
it pointing here. So is the one in
[`xdata-spelled-as-union.md`](xdata-spelled-as-union.md) that says the function
counts are "still … sums", and the three sentences in the former page that a
second append made stale. Nothing was retracted and no figure in the tree moved.