# `xdata-register-map.md` §2 re-keyed per program, and what that moved (issue #714)

**Issue #714, 2026-09-30.** §2's split table and its three-way partition were
worked on the union `spelled_as` column, so every row of that table was a
statement about one *address number* and the `main-ec` rows of it folded in what
the PD image does with the same number. The CSV has answered the per-program
question since issue #709 added `spellings_by_program` (column 21) and issue
#713 added the per-program reference columns (22–33), so this change reads
those columns instead. It is a **presentation** change: no register `status:`
moved, `xdata-registers.csv` and `xdata-clusters.csv` did not change a byte,
nothing was re-exported, no image was opened, and no hardware or Windows machine
was involved.

**Nothing in the census moves.** Every reference figure in the tree is where it
was: Σ `refs_main_ec` is 14,838 and Σ `refs_pd` is 858, which is 15,696 either
way. Only the *distinct* keying changes, and it changes by exactly the 49
`both` rows, because an address number both images touch is one CSV row and two
program-addresses. That identity is what `xdata_program_keyed_table.py --check`
asserts, and it is why neither tool nor suite holds a total of its own.

Two findings here are not the re-key. The second one is a stale table body in
§2 that had been wrong for two days and that nothing in the tree could see.

## The two keyings, side by side

Both are derived from `ec/annotations/xdata-registers.csv` alone. The tool
prints the input's path, its row count and its SHA-256 above every table, so
"re-runnable" here also means "reproducible against a named input":

```console
$ python3 ec/tools/xdata_program_keyed_table.py
<!-- source: .../ec/annotations/xdata-registers.csv -- 1326 rows -- sha256 448e654966b6716d46a0359a5d6bcde3f1ac0a483cc5fd1280ca4d8a08a938c7 -->
```

**Per program** — each row's own `spellings_by_program` clause, references from
`refs_main_ec` / `refs_pd`:

| program | spelling | distinct | references |
|---|---|---:|---:|
| main-ec | `DAT_EXTMEM` | 846 | 7,487 |
| main-ec | `DAT_EXTMEM+pair-literal` | 44 | 490 |
| main-ec | `pair-literal` | 156 | 468 |
| main-ec | `symbol` | 158 | 6,197 |
| main-ec | `symbol+pair-literal` | 14 | 196 |
| pd | `DAT_EXTMEM` | 157 | 858 |
| **total** | | **1,375** | **15,696** |

**Union key** — `program` + `spelled_as`, the two columns the census writes,
with the one `refs` cell a row carries:

| `program` | `spelled_as` | distinct | references |
|---|---|---:|---:|
| main-ec | `DAT_EXTMEM` | 816 | 7,282 |
| main-ec | `DAT_EXTMEM+pair-literal` | 42 | 394 |
| main-ec | `pair-literal` | 155 | 461 |
| main-ec | `symbol` | 143 | 5,567 |
| main-ec | `symbol+pair-literal` | 13 | 187 |
| both | `DAT_EXTMEM` | 34 | 349 |
| both | `DAT_EXTMEM+pair-literal` | 4 | 139 |
| both | `symbol+DAT_EXTMEM` | 11 | 714 |
| pd | `DAT_EXTMEM` | 108 | 603 |
| **total** | | **1,326** | **15,696** |

**1,375 is not a correction of 1,326.** 1,326 is the CSV's row count and is the
right figure for the H1, §3's table and §4.1's table, which count rows and
addresses in the CSV's own terms — including the two places that say "0 of 1,326
addresses" and "over the 1,326 register rows", which count register rows and are
unaffected. 1,375 is the number of program-addresses: 1,218 main-EC + 157 pd,
and 1,326 + 49. §2 now prints both and neither replaces the other, because a
reader comparing the page against the CSV needs the key the CSV is written on
and a reader asking what the main EC does with `0x04A3` needs the key that is
about one program.

**The reference column is where the two keyings genuinely differ.** Under the
union key a `both` row's single `refs` cell is the sum over both programs, so
that column double-counts the 49 shared addresses across the two address
spaces; under the per-program key each row is one program's own count and there
is no row to double-count. The totals are equal (15,696 either way) because the
addresses are the same addresses — only the attribution differs.

## The partition, and the two numbers that were already in the tree

§2's three-way split of the main EC's 1,218 addresses, per program and on the
union key:

| term | per program | union key |
|---|---:|---:|
| named | 172 | 172 |
| `DAT_EXTMEM_xxxx` | 890 | 891 |
| pair-literal only | **156** | 155 |
| total | 1,218 | 1,218 |

References are `refs_main_ec` on both, so each column sums to the main EC's own
14,838: 6,393 / 7,977 / 468 and 6,393 / 7,984 / 461.

**The 155-vs-156 is one address, and the sibling page had already named it.**
[`xdata-spelled-as-union.md`](xdata-spelled-as-union.md) reconciled the same
`pair-literal` split as its 58-versus-59 table and pinned the difference to
`0x04A3` alone, in both directions; what lands here is that §2's own three-way
*partition* now carries the per-program reading beside the union one. The main
EC reaches `0x04A3` as a bare `pair-literal` and nothing else, and it is the PD
image that spells it `DAT_EXTMEM_xxxx`, so the union label folds the PD half in
and the union counts it in the middle term where the per-program key counts it
in the pair-literal-only one. `--moved` re-derives the address on demand rather
than the page asserting that there is one:

```console
$ python3 ec/tools/xdata_program_keyed_table.py --moved
0x04A3	DAT_EXTMEM -> pair-only	DAT_EXTMEM+pair-literal	pair-literal
```

**The 1,326-vs-1,375 is not one address either**, and it is worth keeping apart
from that one: it is the whole 49-row `both` population, and it is a difference
about *rows*, not about which token spells anything.

## `0x04A3` is the only address that moves, and the eleven that are not moves

Eleven `both` rows change their *label* between the keys — `symbol+DAT_EXTMEM`
becomes `symbol` in the main EC — and none of them changes term, because §2's
partition counts a mixed union label in the named term under either key (its own
rule: "the eleven `both` rows that carry both token spellings are counted in
the 161 and not again in the 902"). So the per-program table has no
`symbol+DAT_EXTMEM` row and the partition does not move. A report that listed
those eleven as moves would be counting a rename as a move, which is why
`bucket_moves()` compares the three partition terms rather than the labels.

Per program, those 49 rows are 37 spelled `DAT_EXTMEM_` in both programs, 11
named in the main EC and `DAT_EXTMEM_` in the PD image, and the 49th is
`0x04A3`, whose main-EC half is a bare `pair-literal`.

## §2's table body was stale in two cells, and it was not this issue's doing

Re-measuring §2 against the committed CSV turned up two cells that were already
wrong before this change, independently of it:

| row | §2 printed | committed CSV | Δ |
|---|---|---|---|
| main-ec · `DAT_EXTMEM` | 822 / 7,334 | 816 / 7,282 | −6 / −52 |
| main-ec · `symbol` | 137 / 5,515 | 143 / 5,567 | +6 / +52 |

The other seven rows and the total row are exact. The cause is dated and
attributable: `ec/tools/xdata_register_map.py`'s own 2026-09-28 note (issue
#1296) records a re-export that moved `symbol_main_distinct` 161 -> 167 and
`extmem_main_distinct` 901 -> 895 — "the addresses and the references did not
change, only which token spells them". §2's body was not re-measured when the
tool's pins moved.

**The total row could not see it, and that is the lesson.** Nothing about the
census moved, so a total row that stayed right hid a body that had not. This is
the failure mode §2's own header rule names — "re-measure the *table body*, not
just its total row, because a total its own rows do not sum to is a worse error
than a stale one" — and it is the first time here that not following it has cost
anything. `test_xdata_program_keyed_table.py::TheMapAgrees` is the standing
answer: it parses both tables back out of the markdown and compares them to a
regeneration, so a page edit that changes a cell or restores a superseded figure
is now a red run rather than a stale sentence nobody notices.

Re-measuring the paragraph around the table found three more places that had
gone the same way, all from the same cause:

- the `CPU_TEMP` transcript at the top of §2 said 54 and now prints 56;
- "the other 146 named main-EC addresses" is 166 — there are 172 named main-EC
  addresses, `CPU_TEMP` among them;
- the partition's own 161 / 902 / 155, its 6,416 references and its "other
  1,057" were all downstream of the two stale cells. 6,416 is exactly what the
  stale body implies (5,515 + 187 + 714), which is the clearest sign the
  paragraph was re-derived from the stale rows rather than measured
  independently.

**The 902 is not reproducible from this tree on either key**, and it sits one
above the 901 the same pre-#1296 pin held for `extmem_main_distinct`. Its own
provenance is not recoverable here, so it is recorded as measured rather than
explained — the §2 correction says so in those words.

One more thing the stale 6,416 was doing: it was a `refs`-column figure, and on
a `both` row that column is a sum over both programs, so it was never a main-EC
figure. On the same column the union-keyed partition reads 6,468 / 8,164 / 461
= 15,093, which is the main EC's *addresses* carrying the PD half's references
with it. Both partitions here quote `refs_main_ec`, so each column sums to
14,838 and the two readings are comparable.

## Reproducing it with nothing but a shell

The tool is one command, but a reader should not have to run it to believe it.
Every headline figure above also comes out of `awk -F,` on the committed CSV,
with no Python at all — which is the same discipline the committed positional
readers in [`xdata-census-totals.md`](xdata-census-totals.md) and
[`xdata-export-ownership-page-census.md`](xdata-export-ownership-page-census.md)
already hold themselves to.

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{s+=$6} END{print s}'
15696
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{r+=$7;w+=$8;rw+=$9;p+=$10;a+=$11} END{print "read",r,"write",w,"read+write",rw,"passed-to-call",p,"address-taken",a}'
read 8827 write 3587 read+write 2482 passed-to-call 534 address-taken 266
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{n+=gsub(/=/,"&",$21)} END{print n}'
1375
$ tail -n +2 ec/annotations/xdata-registers.csv | wc -l
1326
```

The third is the whole re-key in one expression: `$21` carries one `program=…`
clause per program the address belongs to, so counting the `=` signs counts
program-addresses. `$6` and `$7`–`$11` are the committed readers re-run
verbatim and unmoved, and `$21` is the new column — which was appended last
precisely so the first two keep meaning what they mean.

The per-program split itself:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{
    n = split($21, c, ";")
    for (i = 1; i <= n; i++) {
      split(c[i], kv, "=")
      k = kv[1] " " kv[2]
      rows[k]++; ref[k] += (kv[1] == "pd" ? $23 : $22)
    }
  } END { for (k in rows) printf "%-34s %6d %9d\n", k, rows[k], ref[k] }' | sort
main-ec DAT_EXTMEM                    846      7487
main-ec DAT_EXTMEM+pair-literal        44       490
main-ec pair-literal                  156       468
main-ec symbol                        158      6197
main-ec symbol+pair-literal            14       196
pd DAT_EXTMEM                         157       858
```

and the two partitions, which differ only in the middle and last terms:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{
    if (index($21, "main-ec=") == 0) next
    split($21, c, ";"); split(c[1], kv, "="); s = kv[2]
    t = (index(s, "symbol") ? "named" : index(s, "DAT_EXTMEM") ? "DAT_EXTMEM" : "pair-only")
    n[t]++; r[t] += $22
  } END { for (t in n) printf "%-12s %6d %9d\n", t, n[t], r[t] }' | sort
DAT_EXTMEM      890      7977
named           172      6393
pair-only       156       468
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '$2 != "pd" {
    s = $3
    t = (index(s, "symbol") ? "named" : index(s, "DAT_EXTMEM") ? "DAT_EXTMEM" : "pair-only")
    n[t]++; r[t] += $22
  } END { for (t in n) printf "%-12s %6d %9d\n", t, n[t], r[t] }' | sort
DAT_EXTMEM      891      7984
named           172      6393
pair-only       155       461
```

Note that the per-program partition takes its spelling from the **main-EC
clause** (`c[1]`, which `spellings_by_program`'s contract puts first) rather
than from `$3`, and the union one from `$3`; that single difference is the whole
change. The reference column is `$22` on both, which is why both sum to 14,838
rather than to the 15,093 the `refs` column would give.

## What the tool asserts, and what it deliberately does not hold

`--check` asserts **relations**, never a total:

- Σ per-program distinct = the two programs' own addresses, added;
- per-program distinct − union distinct = the number of `both` rows;
- references do not move under the re-key — the per-program reference total is
  the CSV's `refs` total, and the two programs' halves add to it;
- each partition's three terms sum to the main EC's distinct and reference
  counts, and no row falls in no term;
- the two partition terms the re-key introduces equal `ORACLE["symbol_main_distinct"]`
  and `ORACLE["extmem_main_distinct"]`, read out of `xdata_register_map.py` **by
  AST and not by import** — those pins already exist, already self-test, and
  already carry a dated note about why they moved;
- the per-program and union partitions differ in the pair-literal term by
  exactly the addresses `--moved` reports.

**No *check* holds a census total as a constant.** `grep` finds no `1375` and no
`7534` in the tool and no numeric `850` anywhere in it; the three figures the
write-up quotes appear there once each, inside `check()`'s own docstring, in the
sentence that says why they are not constants. A constant in a check is
a value every landing branch has to remember to bump, which is the defect
`CLAUDE.md` names under "no hand-kept totals"; here a re-derivation shows up as
a relation failing or as `TheMapAgrees` reading a stale page, not as a number
that quietly describes last month's tree.

`--self-test` runs over fixtures written in the tool's own source, covering the
shapes the committed census does not happen to have: a `both` row whose halves
disagree, the address that moves bucket, a relabelled row that must **not**
count as a move, and a row naming a program the tool does not declare. That last
one is the useful case — an undeclared program has no reference column, so its
references are attributable to nobody and the reconciliation fails loudly
rather than passing on a total that is short by exactly those references.

## The four corrections, and what each one does

The calibration rule governs all of them, and none of them is a deletion.

1. **The two stale cells.** Corrected in place, because a *current* table cell
   that is wrong is corrected under the map's own rule, and the old values are
   named in the dated correction so the correction is checkable rather than
   silent.
2. **The 161 / 902 / 155 partition, its 6,416 and its 1,057.** Kept visible with
   the measured 167 / 896 / 155 and 167 / 895 / 156 beside them. The 902's own
   provenance is recorded as unrecoverable rather than guessed at.
3. **The 1,171 / 14,819 and 1,172 / 14,801 tables, and the 147 / 6,201 and
   41 / 448 partitions.** Untouched. Each was right about the tree it was
   measured on, and each gains one sentence saying what the re-key does to it —
   which is nothing, because a superseded figure of the union key is not a
   superseded figure of the per-program key, which did not exist before this
   change.
4. **The three-rows and `0x07D0` block.** Untouched, plus one sentence: the
   per-program table has no `symbol+DAT_EXTMEM` row, and a reader arriving from
   that table should be told why rather than left to read the absence as a
   dropped row.

## What this does not establish

- **No new addresses.** Nothing here is a claim about the firmware reaching a
  byte. The tool reads one committed CSV; no image is opened, no reference is
  re-scanned, and `xdata_register_map.py --check` reports 0 differences over the
  1,326 rows, which is what says the census did not move.
- **No change to the census's keying.** The tool still emits 1,326 rows keyed on
  `program` + `spelled_as`, and `ORACLE["distinct"]` is still 1,326. What changed
  is how §2 *presents* the table. Re-keying the CSV itself would move the pins,
  churn two generated files and invalidate far more than this issue asks for;
  the per-program column is the answer that does not.
- **The function counts are still not split.** `readers`, `writers`,
  `functions_touched`, `single_function`, `co_reading` and `sources_beyond` are
  *not* per-program on a `both` row, and this change does not make them so. They
  are the last thing `spellings_by_program` and columns 22–33 do not answer, and
  both sibling pages name them as open.
- **`spelled_as` is still a union.** The CSV's own key is unchanged, so the
  second table in §2 still double-counts the 49 shared addresses in its
  reference column. The re-key adds the reading that does not; it does not
  remove the one that does.
- **A percentage moves with its key.** §2's "73% of the register file the main
  EC uses is `DAT_EXTMEM_xxxx`" is the union-keyed 891 of 1,218; counted per
  program it is 890 of 1,218, which rounds to 73% either way. One address out of
  1,218 is the entire difference, and it is stated rather than left to whichever
  table a reader reached for first.

## The re-key's own figures moved once more (issue #1425), and only `0x04A2`

Every table above is re-derived from the committed CSV and the version it was
measured on is left standing, per the calibration rule this repository applies
to a superseded figure. The movement is five addresses across three issues and
one total that did not move:

| | per program | union key | was |
|---|---:|---:|---|
| named | 172 | 172 | 167 |
| `DAT_EXTMEM_xxxx` | 890 | 891 | 895 / 896 |
| pair-literal only | 156 | 155 | 156 / 155 |

`0x04A2` and `0x04A3` are issue #1425's — the `PACK_TEMP_DK` rows, whose
re-export put the name into the text — and `0x04A2` is the one that **leaves**
the `DAT_EXTMEM` term for `symbol` in the main EC. `0x086C` is issue #333's and
`0x07FD`/`0x07FE`/`0x07FF` issue #573's: each added a `registers.yaml` row
without a re-export, and this run's export carried all three into the text. The
attribution is per address in `xdata-register-map.md` §2's correction, and the
pins are the dated block above `named_in_tree` in `xdata_register_map.py`.

**`0x04A3` is still the one address that moves between the two keys, and it
still moves for this document's own reason.** Its main-EC half is a bare
`pair-literal` and the `DAT_EXTMEM` spelling is the PD image's, so naming it
changed its `name` column and nothing else:

```console
$ python3 ec/tools/xdata_program_keyed_table.py --moved
0x04A3	DAT_EXTMEM -> pair-only	DAT_EXTMEM+pair-literal	pair-literal
```

**Nothing in the census moved.** Distinct addresses, references, the 1,375
program-addresses, `pd 157 / 858` and the 49 `both` rows are all where they
were; what moved is which token spells five addresses. That is the same
cross-check `xdata_register_map.py`'s ORACLE block uses, and it is why the
correction is a rename and not five new registers.

## Deliberately not done, and why

- **`.github/scripts/agent-gates.sh` and the workflows.** The agent-push token
  has no `workflow` scope, so a branch touching them fails at the end rather
  than the start. The new tool's `--check` is therefore covered by
  `bash tools/run-tests.sh` through the suite, which is how
  `check_doc_figure_pins.py`, `check_pin_table_rows.py` and
  `check_citation_lines.py` are covered today. Landing a gate entry is a human's
  change, and the prepared-patch precedent is `docs/ci/agent-gates-*.patch`.
- **The totals at §4.1's bucket table and §4.6's `--export-ownership` table.**
  Both are sums of the five *reference* buckets, and references are unmoved by a
  distinct re-key. Their per-program halves already exist in columns 24–33 and
  are published in [`xdata-per-program-counts.md`](xdata-per-program-counts.md);
  splitting those tables is a different change.
- **The `1,326` at "0 of 1,326 addresses" and "over the 1,326 register
  rows".** Both count register rows, which is what the CSV still has.
- **A new section in `docs/findings.md`.** The file is closed; `docs/findings.md`
  §39 gets a dated correction inside the section that already exists, and
  `FROZEN_SECTIONS` is not raised.
- **Anything upstream.** This produces no driver patch and opens nothing in
  another repository.

## What this opens

Two things, both named by the pages that already knew about them. The
**function-count columns** are the last thing on a `both` row that
`spellings_by_program` and columns 22–33 do not answer. And the **stale-body
window** — two days between #1296's export and this change, in which a table's
total row stayed right while its body did not — is short enough to be worth the
standing check `TheMapAgrees` now is, re-measuring a document's table *body*
against the CSV rather than trusting its total row.

## The suite

`ec/tools/test_xdata_program_keyed_table.py`, run by `bash tools/run-tests.sh`
(the runner finds it by `find`; the row in `tools/README.md`'s suite table is the
one step it cannot do). It has two halves with different jobs, which is the
split `test_xdata_guard_off_row_join.py` records and this follows:

- **`ThePublishedFigures`** holds the page's numbers as constants *typed from
  the pages* and compares them against a derivation from the committed CSV —
  never one derived from the other, which is the distinction #753 exists for and
  the failure mode where a suite compares a tool against itself.
- **`TheMapAgrees`** parses §2's two tables and its partition blockquote back
  out of the markdown. `--check` asserts relations inside one derivation and
  cannot see the page beside it, so this class is the gap the stale-cell finding
  above would otherwise have left open.

It also holds that no superseded figure was deleted, that the `CPU_TEMP`
transcript and **the four one-liners in the shell transcript above** both
reproduce when re-run, and — in `TheToolWritesNothing` — that the tool has no
write mode and no `--out-` argument over its parser, and that a full run of every
mode leaves the tree byte-identical.

Holding that block by re-running it rather than by holding its four figures is
what caught a small error in it. The fourth command was `awk -F, 'END{print
NR-1}'`, which printed `1325` under a page saying `1326`: `tail -n +2` has already
removed the header, so `NR` is the row count and the `- 1` subtracted it a second
time. It is the house `wc -l` idiom now, as at
[`xdata-census-totals.md`](xdata-census-totals.md). Holding the block by re-running
it is also the point — a transcript which stops reproducing is then a red run
rather than something a reader has to be the one to notice.
