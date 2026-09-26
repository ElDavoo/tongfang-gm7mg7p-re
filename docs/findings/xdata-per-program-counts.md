# The per-program count columns: `refs` and the five buckets, split, with `refs` itself unmoved (issue #713)

**Issue #713, 2026-09-26.** `ec/annotations/xdata-registers.csv` carried
`spellings_by_program` (column 21) after #711, which split what a `program=both`
row *spells* — and left every *count* on that row a sum. `0x04A3` reads 4
`read` / 3 `write` / 0 / 0 / 1 with nothing in the row saying that the main-EC
seven are 4 read + 3 write and the pd one is 1 address-taken, so a reader
looking for a writer saw three bank1 writes and a single pd `address-taken`
mixed together in one cell. The registers CSV now carries **twelve more
columns** that say which half is which, and `refs` on a `both` row is still the
sum it always was.

This is a report about a census that already exists. No register `status:`
moved, no register was read back, `xdata-clusters.csv` did not change a byte,
`registers.yaml` and `ec/ghidra/xdata-symbols.csv` were not involved, and no
hardware or Windows machine was involved — every number here re-derives from
the committed decompiled tree and the committed CSV. The sibling page,
[`xdata-spelled-as-union.md`](xdata-spelled-as-union.md), is the one this
extends; where the two say different things about the same row, both are quoted
below.

## What the twelve columns are, and where they sit

Columns **22–33**, appended after `spellings_by_program`:

| | main EC | pd image |
|---|---|---|
| references | `refs_main_ec` | `refs_pd` |
| read | `read_main_ec` | `read_pd` |
| write | `write_main_ec` | `write_pd` |
| read+write | `read+write_main_ec` | `read+write_pd` |
| passed-to-call | `passed-to-call_main_ec` | `passed-to-call_pd` |
| address-taken | `address-taken_main_ec` | `address-taken_pd` |

**Metric first, then program,** so one program's whole half is a contiguous run
(`cut -d, -f22-33`) and the interleaved reading — the two numbers for one
metric next to each other, with the summed cell 16 columns to their left — is
the default order. `_pd`, not `_pd_image`: `ec/annotations/registers.yaml`
writes its own per-program figures `static_refs_main_ec` /
`static_refs_pd_image`, and that is the precedent #713 cites, but this CSV's
vocabulary is already `pd` — the `program` column's value, the `cluster_id`
prefix, the `pd=` label in `spellings_by_program` two columns to the left on the
same row — so `_pd_image` would put two spellings of one program in one line,
which is the confusion the columns exist to remove. The divergence is
deliberate and is recorded in the tool beside `program_suffix()`. The bucket
name keeps its `+` and its `-` because it is the bucket name; a second
vocabulary for the same thing is the thing to avoid, and nothing splits a
header on `+`.

**Written on every row, not only on the 49 `both` ones.** On a `program=main-ec`
row `refs_main_ec` is that row's whole `refs` and `refs_pd` is `0`; on a `pd`
row the reverse. The alternative — populating only the `both` rows — is a
column blank on 1,277 of 1,326 rows, which is a shape no `csv.DictReader`
consumer can rely on: `int('')` where `int` is the natural read. It is also
what makes `refs == refs_main_ec + refs_pd` checkable corpus-wide rather than
only on the 49 rows where it is interesting.

**Comma-free is mechanical, not a rule.** `per_program_counts_of()` can only
write an `int`; there is no formatting path in which a thousands separator, a
unit suffix or a comment could reach a cell. That is what keeps
`awk -F, '{s+=$6}'` exact, and §"The positional readers, re-run" below
demonstrates it rather than asserting it.

## What changed, and what did not

`refs`, the five buckets, `readers`, `writers`, `functions_touched`,
`single_function`, `name`, `functions`, `cluster_key`, `co_reading`,
`sources_beyond`, `spelled_as`, `spellings_by_program`, `span_group` and
`cluster_id` are all exactly what they were, byte for byte, and so are every
`ORACLE`, `BUCKET_TOTALS`, `OWNERSHIP` and `DIRECTION_INVARIANT` value in the
tool. **No reference was added, de-duplicated or re-bucketed**, so the cluster
ranking is untouched, `cluster_id` keeps its exact values, and
`xdata-clusters.csv` regenerates byte-identically — which is the strongest
single statement available that nothing moved:

```console
$ md5sum ec/annotations/xdata-clusters.csv
302505310c35b3b105b677a9f65d1f74  ec/annotations/xdata-clusters.csv
$ python3 ec/tools/xdata_register_map.py >/dev/null
$ md5sum ec/annotations/xdata-clusters.csv
302505310c35b3b105b677a9f65d1f74  ec/annotations/xdata-clusters.csv
```

The only edited generated file is `ec/annotations/xdata-registers.csv` itself,
1,326 rows × 33 columns, written by the tool's default mode and never by hand.
It is already listed in `.github/workflows/agent-conflicts.yml` as a
never-hand-merge generated file.

## The `both` rows' split, and the arithmetic that says it is this census

There are 1,326 rows: 1,169 `main-ec` carrying 13,891 references, 108 `pd`
carrying 603, and 49 `both` carrying 1,202.

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{c[$2]++; r[$2]+=$6} END {for (k in c) print k, c[k], r[k]}' | sort
both 49 1202
main-ec 1169 13891
pd 108 603
```

The 1,202 on the `both` rows split **947 main-EC + 255 pd**, and those two
numbers are the cross-check that says the columns split *this* census rather
than counting it a second time. The per-program totals the tool already pins are
each the single-program rows plus one half of the `both` rows:

| | single-program rows | `both` rows' half | total |
|---|---:|---:|---:|
| main EC | 13,891 (`main-ec` rows) | 947 | **14,838** = `ORACLE["main_refs"]` |
| pd image | 603 (`pd` rows) | 255 | **858** |
| all | 14,494 | 1,202 | **15,696** = `ORACLE["refs"]` |

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{m+=$22;p+=$23} END{print m, p}'
14838 858
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$2=="both"{m+=$22;p+=$23;s+=$6} END{print m, p, s}'
947 255 1202
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$22+$23!=$6' | wc -l
0
```

The last line is the per-row partition: `$22 + $23 == $6` on all 1,326 rows, and
not only on the 49 where the halves differ.

The 49 rows' buckets, per program rather than summed:

| | read | write | read+write | passed-to-call | address-taken | refs |
|---|---:|---:|---:|---:|---:|---:|
| main EC | 546 | 165 | 212 | 16 | 8 | 947 |
| pd | 95 | 74 | 2 | 56 | 28 | 255 |
| both programs summed | 641 | 239 | 214 | 72 | 36 | 1,202 |

The bottom row is the figure the sibling page publishes as "the row's own
`refs` column, summed over both programs", so nothing a reader had before is
gone; the two rows above it are the same five numbers with the two address
spaces apart. 546 + 95 = 641 and 165 + 74 = 239, which is the partition holding
on the `both` rows specifically.

## The four `pair-literal` rows, per program

These are the four `both` rows whose union carries `pair-literal`, and the ones
the sibling page singles out: three of them are genuinely
`DAT_EXTMEM+pair-literal` *inside the main EC*, and `0x04A3` is not. The
`refs` figures here were already published in
[`xdata-spelled-as-union.md`](xdata-spelled-as-union.md) and in
`ec/annotations/xdata-register-map.md` §2; the bucket figures for two of the
four were, and those are what make the per-row assertion an independent check
rather than a self-consistent one (§"The assertions" below).

| address | row `refs` | row buckets (r / w / rw / ptc / at) | main-EC | pd |
|---|---:|---|---|---|
| `0x04A3` | 8 | 4 / 3 / 0 / 0 / 1 | 7 = 4 r + 3 w | 1 = 1 at |
| `0x0834` | 66 | 56 / 8 / 1 / 1 / 0 | 48 = 40 r + 7 w + 1 ptc | 18 = 16 r + 1 w + 1 rw |
| `0x0835` | 52 | 42 / 9 / 0 / 1 / 0 | 48 = 40 r + 7 w + 1 ptc | 4 = 2 r + 2 w |
| `0x0836` | 13 | 8 / 4 / 0 / 1 / 0 | 9 = 4 r + 4 w + 1 ptc | 4 = 4 r |

`0x0835` and `0x0836` have no published per-program bucket figures; those four
cells are derived from the tool.

**`0x04A3` is the worked example, because it is the one row where the union was
load-bearing and it is otherwise unremarkable.** Its `functions` cell names six
main-EC routines and one pd routine; the row's buckets read 4 / 3 / 0 / 0 / 1
and the new columns say the main EC's seven are 4 read + 3 write while the pd
image's one is an `address-taken`:

```console
$ cut -d, -f1,2,3,6,7,8,9,10,11 ec/annotations/xdata-registers.csv | grep -E '^0x(04A3|083[456]),'
0x04A3,both,DAT_EXTMEM+pair-literal,8,4,3,0,0,1
0x0834,both,DAT_EXTMEM+pair-literal,66,56,8,1,1,0
0x0835,both,DAT_EXTMEM+pair-literal,52,42,9,0,1,0
0x0836,both,DAT_EXTMEM+pair-literal,13,8,4,0,1,0
$ for a in 0x04A3 0x0834 0x0835 0x0836; do echo -n "$a  "; grep "^$a," ec/annotations/xdata-registers.csv | cut -d, -f22-33; done
0x04A3  7,1,4,0,3,0,0,0,0,0,0,1
0x0834  48,18,40,16,7,1,0,1,1,0,0,0
0x0835  48,4,40,2,7,2,0,0,1,0,0,0
0x0836  9,4,4,4,4,0,0,0,1,0,0,0
$ head -1 ec/annotations/xdata-registers.csv | cut -d, -f22-33
refs_main_ec,refs_pd,read_main_ec,read_pd,write_main_ec,write_pd,read+write_main_ec,read+write_pd,passed-to-call_main_ec,passed-to-call_pd,address-taken_main_ec,address-taken_pd
```

Read down the `0x04A3` line: 7 and 1 references, 4 and 0 reads, 3 and 0 writes,
nothing in the three buckets that describe a handoff, 0 and 1 address-taken. So
the single `address-taken` on that row is the PD image's, and a reader looking
for a writer is looking at three bank1 writes with the cell now saying so.
`0x0834` is the more interesting shape: 40 + 16 reads, 7 + 1 writes, and one
`read+write` that is the PD image's alone.

**The same two columns on a single-program row.** `0x07D0` is a `pd` row
(`BATTERY_CHARGE_LIMIT_DOWN` in `name`, `DAT_EXTMEM_07d0` in the PD image's own
text — the `pd-xdata-overlap.md` distinction, and the reason `spelled_as` and
`name` are separate columns), so its `refs_main_ec` is `0` across all six:

```console
$ grep '^0x07D0,' ec/annotations/xdata-registers.csv | cut -d, -f1,2,6,7,8,9,10,11,22-33
0x07D0,pd,41,17,4,2,16,2,0,41,0,17,0,4,0,2,0,16,0,2
$ grep '^0x0004,' ec/annotations/xdata-registers.csv | cut -d, -f1,2,6,7,8,9,10,11,22-33
0x0004,main-ec,13,0,13,0,0,0,13,0,0,0,13,0,0,0,0,0,0,0
```

`0x0004` is the mirror: 13 references, all of them bank0's `write`s, and
`refs_pd` zero. On 1,277 of the 1,326 rows the twelve columns are a restatement
of the six beside them, and that is the point — the shape is uniform, so a
consumer never has to ask which kind of row it is holding.

## The assertions, and where they live

Four `--self-test` assertions, appended to the `#709` block in
`ec/tools/xdata_register_map.py`'s `self_test()`. Three read the **committed**
registers CSV rather than a fresh generation: the whole of the issue is that
the artifact a reader opens could not answer the question, so a check against
what this run would write would not be answering it. #711's three assertions
are untouched — a new column is not a licence to weaken what the old one is
held to, and a reader of that block is entitled to assume `refs` on a `both` row
is still the sum, which is what the first assertion holds.

1. **The columns' own contract, on every row, and where they sit.** All twelve
   at 22–33 with `spellings_by_program` still at 21; on all 1,326 rows each of
   the six unsuffixed counts is the sum of its two halves; a `main-ec` row
   carries nothing for `pd`, a `pd` row nothing for `main-ec`, and a `both` row
   carries both. The last is a real assertion rather than a tautology: an
   address in `groups[g]` has at least one reference there by construction, so a
   `both` row with a zero half means the file and the tool disagree about which
   programs touch the address number at all.
2. **Attribution against a fresh generation.** Every one of the 15,912 cells
   (1,326 rows × 2 programs × 6 metrics) is the per-program entry it claims to
   be, read against `groups` rather than against a rendered row. A column
   written wrongly in *both* `build()` and the CSV is internally consistent and
   assertion 1 would pass it; this is the cross-check that can fail, and an
   address in no program of `groups` expects a zero rather than being skipped.
3. **The aggregate reconciliation.** 14,838 + 858 == 15,696 over all 1,326
   rows; 947 + 255 == 1,202 on the 49 `both` rows, which is what those rows'
   own `refs` column sums to; and their five buckets per program are
   546/165/212/16/8 against 95/74/2/56/28. A column that moved a reference
   between programs keeps assertion 1 true and fails this.
4. **The four `pair-literal` rows, to the bucket.** `0x04A3`'s 4 read + 3 write
   against 1 address-taken, `0x0834`'s 40 / 7 / 0 / 1 / 0 against 16 / 1 / 1 /
   0 / 0, and the two derived rows beside them. **Two of the four are checked
   against prose nobody re-derived for this change** — the sibling page and the
   map's §2 both publish those per-program bucket figures — which is what makes
   this an independent check rather than a self-consistent one.

Every key of the new `PER_PROGRAM` pin block and every entry of
`PAIR_BOTH_PAIR_LITERAL_BUCKETS` is read by one of those four. The rule is
issue #849's: a value in a module-level dict that nothing subscripts is a
promise wearing the costume of a pin.

The failure messages cap the disagreeing rows at eight and **count the
overflow**, the way the three `#709` assertions immediately above them in the
tool already do — a silent cap reads as "covered" when it is not. And `per_program_cell()` returns
−1 for a missing or blank cell rather than letting `int('')` raise: see
"the one real hazard" below.

The two gates:

```console
$ python3 ec/tools/xdata_register_map.py --check
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
/home/runner/work/tongfang-gm7mg7p-re/ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
/home/runner/work/tongfang-gm7mg7p-re/ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
$ python3 ec/tools/xdata_register_map.py --self-test
  ... 106 assertions in all, of which these four are #713's ...
  ok    issue #713: the 12 per-program columns sit at 22-33 with `spellings_by_program` still at 21, and on all 1326 rows of annotations/xdata-registers.csv each of the six unsuffixed counts is the sum of its two halves -- `refs == refs_main_ec + refs_pd` and the same for all five buckets -- while a `main-ec` row carries nothing for `pd`, a `pd` row nothing for `main-ec`, and a `both` row carries both (rows that disagree: none)
  ok    and every one of those cells is the per-program entry it claims to be, read against a fresh generation of the census rather than against a rendered row -- 1218 main-EC and 157 pd program-addresses, so a `both` row's halves come out of two different entries and a single-program row's other half comes out of nothing at all (cells that disagree: none)
  ok    and the split partitions the census rather than re-counting it: the two columns sum to 14838 + 858 = 15696 over all 1326 rows (got 14838 + 858), each side being the single-program rows plus one half of the 49 `both` rows, which carry 947 main-EC + 255 pd = 1202 -- the same 1202 the rows' own `refs` column sums to (got 947 + 255) -- and those rows' five buckets per program, in read, write, read+write, passed-to-call, address-taken order, are 546, 165, 212, 16, 8 main-EC against 95, 74, 2, 56, 28 pd (got 546, 165, 212, 16, 8 and 95, 74, 2, 56, 28)
  ok    and those four rows say which program does what: 0x04A3, 0x0834, 0x0835, 0x0836 -- 0x04A3's seven main-EC references are 4 `read` and 3 `write` and its single pd one is 1 `address-taken`, which is the row's own 4 / 3 / 0 / 0 / 1 with nothing left to guess, and 0x0834's 48 are 40 / 7 / 0 / 1 / 0 against the pd 18's 16 / 1 / 1 / 0 / 0 -- two of these four were already published per program, so the column is checked against prose nobody re-derived for it (rows that disagree: none)
  ...
  all assertions passed
```

`--check` is what holds the committed artifact to what the tool generates, byte
for byte, so no future change can quietly drop one of the twelve, and
`--self-test` is what holds the twelve to the tree. **Both are in the cheap
gate**: `.github/scripts/agent-gates.sh:261-262` runs
`python3 "$tool" --check && python3 "$tool" --self-test` for this tool, so
neither of these four assertions can be removed without CI going red. (The
sibling page still says `--self-test` is *not* gated; that was true when it was
written and stopped being true with issue #815, whose
[`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md) is the page
that switched the mode back on.)

`python3 ec/tools/test_xdata_register_map.py` is a different file and *is*
deliberately ungated — the gate file says why, at `:256-260`: `--no-eq-guard`
and `--export-ownership` change what the census means and are refused by the
refusals that file holds, and no gate calls it. Run by hand it is 23 tests,
all passing, which is what says those refusals are unaffected. Its only
CSV-column access is `column_totals(path, column)`, a `csv.DictReader` keyed by
column *name* (`"write"`, `"refs"`), and nothing in it asserts a column count
or the header — so it needed no edit for this change, which is a reading of the
file rather than a change to it.

### The one real hazard, and the shape that answers it

`render()` writes with `csv.DictWriter(fieldnames=columns, extrasaction="ignore")`
and the default `restval=""`. `extrasaction` governs the other direction — keys
*in a row* that are not in `fieldnames` — and a key in `fieldnames` that is
**missing from a row** is not an error at all: writing `{'a': 1}` against
`fieldnames=['a', 'b']` produces `a,b\n1,\n` and raises nothing. So adding a
name to `REGISTER_COLUMNS` and forgetting it in one `build()` branch yields a
plausible-looking CSV with empty numeric cells, `--check` goes red only as a
byte diff, and the new assertions die on `int('')` with a traceback pointing at
the wrong line.

The answer here is structural rather than a review convention:
`per_program_columns()` is the *only* source of the twelve names, and
`build()` has exactly one `register_rows.append()` site, so
`**per_program_counts_of(groups, addr)` supplies all twelve or the list is
wrong in a way assertion 1's position check fails. And `per_program_cell()`
reports a missing or blank cell as a self-test failure with the address beside
it, instead of a `ValueError`. Both are the same argument `spellings_of()`
makes for the two spelling columns.

## The positional readers, re-run

The append-not-insert argument rests on these commands still meaning what they
meant, so here they are, verbatim, on the committed file after the change. The
three `xdata-spelled-as-union.md` console blocks are the same commands it
published before this change and the outputs are identical to what it recorded.

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{s+=$6} END{print s}'
15696
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{r+=$7;w+=$8;rw+=$9;p+=$10;a+=$11} END{print "read",r,"write",w,"read+write",rw,"passed-to-call",p,"address-taken",a}'
read 8826 write 3587 read+write 2482 passed-to-call 534 address-taken 267
$ tail -n +2 ec/annotations/xdata-registers.csv | cut -d, -f21 | grep -o pair-literal | wc -l
214
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$3 ~ /pair-literal/ {if ($3 ~ /\+/) m++; else o++} END {print "CSV union:", m, "mixed /", o, "pair-only"}'
CSV union: 59 mixed / 155 pair-only
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$2=="both" { n=split($21,p,";"); delete seen; for (i=1;i<=n;i++) { split(p[i],q,"="); seen[q[2]]=1 } k=0; for (x in seen) k++; b++; if (k>1) { d++; list = list " " $1 } } END { print b, "both rows;", d, "of them have per-program halves that differ:" list }'
49 both rows; 15 of them have per-program halves that differ: 0x04A3 0x07D3 0x07D4 0x07D5 0x07D8 0x07D9 0x07DA 0x07F3 0x07F6 0x0809 0x080C 0x080D 0x0834 0x0835 0x0836
```

`$21` is still `spellings_by_program` and still selects it; it is no longer the
**last** column, and a reader who asks for "the last column" now gets
`address-taken_pd`. The two new sums, and the per-row partition over all 1,326
rows rather than the 49 that carry the information:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{m+=$22;p+=$23} END{print m, p}'
14838 858
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$22+$23!=$6' | wc -l
0
$ wc -l < ec/annotations/xdata-registers.csv
1327
$ head -1 ec/annotations/xdata-registers.csv | awk -F, '{print NF}'
33
```

**One thing to know about the `8341` a reader may find in
`docs/findings/xdata-census-totals.md`.** That page is a *snapshot* of the
census as of #557 — its own opening rule is "if anything here disagrees with
those two files, those two files are right" — and issue #279 has since moved the
census from 1,171 / 14,819 to 1,326 / 15,696. So its `$6` reader prints
`14819` and its `$7`-`$11` reader `8341 / 3195 / …` against today's `15696` and
`8826 / 3587 / …`. **That is a pre-existing staleness in that page, not
something this append caused**: the numbers were already off before column 22
existed, and the page is the historical record behind its own correction
rather than a reader of the current census. It is left alone here for the same
reason `xdata-export-ownership-page-census.md`'s stale `md5sum` is.

## What this does not establish

**A zero in the other program's column means the census found no reference in
that program, and nothing more.** It is "not found by this method over the
committed decompiled tree" — never "absent from the PD image", never a claim
that the program *cannot* reach the byte, and never a prediction that a future
export will not find a site there. This is `CLAUDE.md`'s calibration rule and
`ec/annotations/registers.yaml`'s own caveat on the same point, restated for a
column that makes the zeros more numerous and therefore more quotable. A
`refs_pd` of `0` on a `main-ec` row says what the `program` column already
said, and no more.

**A per-program `write` is still a static shape.** `write_main_ec = 3` on
`0x04A3` is three `=`-shaped occurrences in decompiled C. It is not evidence
that the EC acts on that byte, and no column here is. §4.7 of
`ec/annotations/xdata-register-map.md` states this at length and nothing in this
change touches it.

**Two programs touching one address *number* is still a collision in the
numbering, not a shared byte.** `ec/decompiled/pd/` is the self-contained
`ITE8850-PD` image with its own XDATA map; `refs_main_ec = 947` and
`refs_pd = 255` over the same 49 rows is two address spaces described
side by side, never one count split two ways. No `pd` half became an EC-register
claim: the suffixes are the same `main-ec` / `pd` tokens the `program` column
and `cluster_id` use.

**The split is over the committed decompiled tree, so a call site the exporter
dropped is still out of reach** — on both halves, and the `int('')`
of a whole missing program is `0` either way.

**`registers.yaml`'s `static_refs_main_ec` / `static_refs_pd_image` figures
were not cross-checked against these columns, and are not expected to agree.**
160 entries carry both keys (the issue's 161 counts the header comment that
names them). They come from `register_ref_table.py` over the firmware image,
which is a different method over different bytes, and the tree already records
where the two disagree: the `PAIR_RESOLVED` block's `0x0402` entry works
through 10 census references against the 3 `mov DPTR,#0x0402` + `lcall`
encodings the image scan counts, and says so as "the two methods" rather than
as a defect. The naming precedent was used for the `_pd` decision above and
for nothing else — no `status:` moved and none of those figures was refreshed.

## Deliberately not done, and why

- **Re-keying `ec/annotations/xdata-register-map.md` §2's `both` rows per
  program.** That is the *other* half of #709's follow-up. It moves §2's
  `distinct` total from 1,326 to 1,375 (1,218 main-EC + 157 pd
  program-addresses) and invalidates §2's three superseded-table correction
  blocks. It is a second, larger edit to the same long shared file, and doing
  both in one change is exactly the merge conflict CLAUDE.md's "new work goes
  in new files" rule exists to prevent. §2 gets one clause naming the count
  columns, and the re-keying stays open.
- **Splitting `readers`, `writers`, `functions_touched`, `single_function`,
  `co_reading`, `sources_beyond`.** #713 does not ask for them. The `functions`
  cell already carries program-prefixed names (`bank1:0xAD7D=…`,
  `pd:0xF22E=…`), so a per-program *site* question is already answerable by
  reading it — which is why the sibling page lists those columns as the
  exception rather than as an open item. Whether their *counts* should get the
  same treatment is a real question this change does not answer.
- **Any `status:` change in `registers.yaml`, and any refresh of its per-program
  reference figures** — different method, different bytes, as above.
- **Refreshing the stale `md5sum` in `xdata-export-ownership-page-census.md`.**
  Pre-existing, historical, and in someone else's page; touching it invites a
  conflict for no gain.
- **The `--export-ownership` and guard-off runs publish the new columns too**,
  since they go through the same `build()`. A per-program guard-off measurement
  — what the `==` guard moves *within* each program rather than in the summed
  total — is measurable from the same recipe and is not done here.

## The three places that said no per-program count exists, corrected in place

None of the three was *wrong* — `refs` really is still the sum on a `both` row,
and that sentence is unchanged. Each was incomplete, and each gets a dated,
attributed correction **beside** the original rather than a silent edit, per
the `docs/findings.md` §4a-4d pattern:

| where | what it said | what changed |
|---|---|---|
| `docs/findings/xdata-spelled-as-union.md`, "The union that remains" | `refs` and the five buckets "stay sums" / "None of this is fixed here" | a dated note beside the closing paragraph: true of the unsuffixed cells, no longer true of the row as a whole |
| `ec/README.md`, the `xdata-registers.csv` bullet | "the last column" for `spellings_by_program`, and "the reference and direction counts stay sums" | a pointer to columns 22–33 and to this page; the second clause kept, narrowed |
| `ec/tools/xdata_register_map.py`, the `build()` comment | "`refs`, the five buckets … stay summed over both programs … nothing here splits those" | the block rewritten in place to say the unsuffixed cells stay summed *and* that the twelve after them split the counts |

`docs/findings.md` §39's closing sentence — "The follow-up this opens is
per-program `refs` / bucket columns, and re-keying §2's `both` rows per
program" — is **left exactly as written**, because the re-keying half is still
open. The new summary section names which half landed.

Nothing here is a restatement of a previously wrong number. No figure in the
tree moved, so there is no wrong version to keep visible: the numbers
`xdata-spelled-as-union.md` publishes for `0x04A3` and `0x0834` are the same
numbers this change's columns now publish, and the two agree.
