# §5's `size` and `refs` columns were never read; re-derived, they hold

Issue #1240. The tree's own `check_cluster_citations.py` is the only thing
holding the hand-typed worklist in `ec/annotations/xdata-register-map.md` §5 to
`ec/annotations/xdata-clusters.csv`, and it was holding **one** of that table's
four figures. The size and the reference count were looked for in the wrong
cells, found nothing there, and reported nothing — while the tool's own
docstring said all four were held. Fixed here, and every §5 row re-derived.

## The defect

A census row's columns were read by fixed index: `row[1]` as the size and
`row[2]` as the reference count. That is the shape the tool's fixtures use,
`cluster | size | refs | range | named inside`, and it is not the shape §5
uses. §5's header is nine columns wide, because `cluster_key` and
`cluster_name` sit between the id and the size:

```
| cluster | key | name | size | refs | range | named inside | co-reading | the functions ... |
```

So on every real §5 row, `row[1]` was a `k<12 hex>` content hash and `row[2]`
was a hand name or an em dash. `number()` returns `None` for both, the
comparison never ran, and the row passed.

The range and the named count were read correctly, and that is why the defect
was invisible: the two figures the rule found by scanning for a span were the
two it held, and the two it read by index were the two it never checked.

The row below carries **999** for a size the census holds at **152** and **888**
for a reference count it holds at **873**. Against the fixed-index reader it
passed, reporting nothing at all; against the reader in the tree today it is
three disagreements:

```console
$ python3 -c "
import sys; sys.path.insert(0,'ec/tools')
import check_cluster_citations as ccc
counts = ccc.census()[2]
row = '| \`main-ec-001\` | \`ke794087e13a6\` | — | 999 | 888 | \`0x0300\`-\`0x097B\` | 77 | prose |'
for p in ccc.census_row('x', 1, row, counts): print(p[3])"
152 addresses in the census, 999 in the row
873 references in the census, 888 in the row
11 named addresses in the census, 77 in the row
```

The first two lines are the ones the fixed-index reader did not print. That
the named count was reported all along, while the size and the reference count
beside it were not, is the shape of the defect: the figures read correctly were
the ones found by scanning for a span, and the two that were not were the two
read by index.

## The fix

Columns are now found by the row's own **range cell** rather than by index: the
two cells before it are the size and the reference count, the cell after it is
the named count. The transcript above is that reader's output.

The anchor rather than the header, for two reasons worth stating. `units()`
yields one table row at a time and carries no table with it, so a
header-resolving reader would have to reach past the unit for state the walk
does not keep. And the shorter five-column shape the tool's other fixtures use
**has no header row at all**, so a header-only reader would check less than
this one does — it would drop the fixture shape the existing count suite is
written in. The range is the one cell whose *content* says which column it is,
and both shapes carry it. A row without one is passed over rather than read on
a guess; that is a new way for the rule to say nothing, and it is listed in the
tool's docstring beside the others.

## What the re-derivation found: nothing moved

Every figure in §5 agrees with the committed census. All three are now read;
all three were right.

| cluster | size | refs | range | named | census agrees |
|---|---|---|---|---|---|
| `main-ec-001` | 152 | 873 | `0x0300`-`0x097B` | 11 | yes |
| `main-ec-002` | 92 | 1,130 | `0x0456`-`0x1809` | 35 | yes |
| `main-ec-003` | 43 | 4,966 | `0x0460`-`0x09CE` | 43 | yes |
| `main-ec-004` | 28 | 181 | `0x045C`-`0x1C3A` | 15 | yes |
| `main-ec-005` | 16 | 94 | `0x043E`-`0x300E` | `0x043E` (a listing, not a count) | yes |
| `main-ec-006` | 15 | 68 | `0x0388`-`0x03C9` | none | yes |
| `main-ec-007` | 12 | 280 | `0x0045`-`0x1504` | none | yes |
| `main-ec-008` | 12 | 107 | `0x0A43`-`0x0FC3` | none | yes |
| `main-ec-009` | 12 | 37 | `0x049A`-`0x05C3` | none | yes |
| `main-ec-010` | 12 | 35 | `0x00C0`-`0x2275` | none | yes |
| `main-ec-011` | 12 | 26 | `0x040A`-`0x0547` | 4 | yes |
| `main-ec-012` | 11 | 43 | `0x045E`-`0x1F07` | 4 | yes |

**This is the finding, not a null result.** The figures in §5 are hand-typed
prose about a generated CSV, and until now two of the four were checked by
nothing at all. They happen to be right today. That is a statement about
*right now*: `main-ec-004`'s size and reference count had drifted once, and a
two-column reading is what would have caught it, as it will any that drift from
here. The value of the re-derivation is that the guard now exists, not that it
found something.

`main-ec-002`'s size and reference count are the pair to look at first when
checking this by hand, because they are the ones §5's surrounding prose quotes
in its own sentences (the `charge_target_update` / `mode-oem-init`
discussion). The census holds `92` and `1130`; the row holds `92` and `1,130`.

## What the columns mean, now that something reads them

The worklist is the census's top twelve by the ranking `xdata_register_map.py`
uses — `(size, refs, lowest address)` — and it is a ranking, not a
significance order. Two readings off the figures §5 publishes, both derived
from `xdata-clusters.csv` and re-derivable with the command below.

**The twelve rows are a third of the address space and half of the references**
— 417 of the 1218 main-EC cluster addresses, and 7840 of the 14838 references.
Both halves are properties of the committed census's `size` and `refs`
columns, and only the first survives the export-ownership reading below.

**The `refs` column is a count of files, and 42 files can be one routine.**
`ec/annotations/xdata-06c2-06db-timers.md` §2a measures the size of that here:
at least 4,642 of `main-ec-003`'s 4,966 references are the same 393 bytes
counted once per each of 42 overlapping function-boundary exports, and the 43
addresses have 345 direct `MOV DPTR,#addr` sites between them, which is the
number that means something. `xdata-register-map.md` §4.5 is the same reading
for the census as a whole. So `main-ec-003`'s 115.5 references per address
against `main-ec-007`'s 23.3 is a statement about how the routine is exported,
not about how often the firmware reads those addresses — and
`--export-ownership`, which reads each routine once from the export that owns
it, inverts the ranking: `ff-fill-stubs` becomes the densest of the twelve, and
the sweep cluster is not carried by that run at all (its `k733222e83898` best
matches any of that run's clusters at 0.48, under the 0.50 floor). That run
re-keys the clusters, so the two columns are read by name there, not by id.

```console
$ python3 ec/tools/xdata_register_map.py --export-ownership \
    --out-clusters /tmp/own-clusters.csv --out-registers /tmp/own-registers.csv
$ python3 -c "
import csv
def top(p): return [r for r in csv.DictReader(open(p)) if r['program'] != 'pd']
for label, p in (('committed', 'ec/annotations/xdata-clusters.csv'),
                 ('export-ownership', '/tmp/own-clusters.csv')):
    rows = top(p); t = rows[:12]
    print(f'{label}: {sum(int(r[\"size\"]) for r in t)}/{sum(int(r[\"size\"]) for r in rows)} addrs, '
          f'{sum(int(r[\"refs\"]) for r in t)}/{sum(int(r[\"refs\"]) for r in rows)} refs')
    for v, cid, nm in sorted(((int(r['refs'])/int(r['size']), r['cluster_id'], r['cluster_name'])
                              for r in t), reverse=True)[:2]:
        print(f'  {cid}: {v:.1f} refs/addr {nm}')"
committed: 417/1218 addrs, 7840/14838 refs
  main-ec-003: 115.5 refs/addr counter-sweep
  main-ec-007: 23.3 refs/addr ff-fill-stubs
export-ownership: 419/1218 addrs, 2962/9320 refs
  main-ec-007: 15.5 refs/addr ff-fill-stubs
  main-ec-002: 12.7 refs/addr mode-oem-init
```

The two censuses disagree about which cluster is densest and about how much of
the reference mass the twelve hold, and both are readings the tree's own
`--export-ownership` flag produces. Nothing here establishes a call frequency.
`docs/findings/counter-sweep-entry-set.md` bounds the sweep's **call sites** —
one confirmed caller among the 180 census rows that target into the run — and
that is a bound on sites, not on executions; what would establish the latter is
a live reading on the machine.

**A caveat on all of it.** Every figure here re-derives from two committed
CSVs. Nothing was read back from hardware, no register was observed, and none
of this is a claim about what the EC does — only about how the committed
census groups the addresses and how strongly each group is referenced. The
per-program `refs` column is `check_cluster_refs_projection.py`'s subject, not
this one's; a row's `refs` is the sum of its members' `refs_<program>`, and
§5's own prose says so.

## The tests

`ec/tools/test_check_cluster_citations_census_columns.py`, a new suite rather
than cases appended to the existing one — the existing suite is long and every
other branch appends at its end.

What is held, and each case goes red when the fix is reverted (verified by
restoring the fixed-index reader and re-running):

| case | asserts |
|---|---|
| `test_the_three_figures_are_read_from_their_own_columns` | all three perturbed on §5's real header, all three reported — **the case that goes red first** |
| `test_a_wrong_size_is_reported` / `..._reference_count_...` / `..._named_count_...` | each figure read from its own cell |
| `test_a_reference_count_is_compared_as_a_number_not_as_its_text` | `1,130` equals 1130 rather than disagreeing with it |
| `test_the_shorter_shape_is_still_read` | the five-column fixture shape still checked, so a fix that only understood §5's header would fail it |
| `test_a_row_with_no_range_is_not_read` / `..._no_room_before_it_...` | an unanchorable row is passed over, with its figures wrong on purpose |
| `test_an_alternate_census_without_a_range_column_still_holds_two_figures` | a `--clusters` CSV with no `addr_range` still holds `size` and `refs` — moving the read to the anchor did not take them into the `addr_range` guard |
| `test_a_listing_in_the_named_column_is_still_not_a_count` | §5's `` `0x043E` `` cell is not read as a count of one |
| `test_only_the_first_span_anchors` | a second span in the named column is not a second anchor |
| `test_every_committed_worklist_row_agrees_with_the_committed_census` | every §5 row read **out of the committed file**, not from fixtures |
| `test_a_perturbed_committed_row_is_reported` | the negative of that, on the committed census — what says the case above passes because the figures are read |

That last pair is the one that would have caught this. It reads the rows out of
`xdata-register-map.md` rather than restating them here, so a table that lost
its range column fails it by finding no rows to read.

## Scope

Only the column resolution and its tests. The §5 figures needed no correction,
so `xdata-register-map.md` is not edited, and the header cell is unchanged.

`check_cluster_citations.py`'s other importers — `check_citation_lines.py`,
`check_capture_claims.py`, `check_testdata_row_claims.py` and
`census_citation_exemptions.py` — are untouched; they import `units()`,
`census()`, `cited_clusters()` and the rest, none of which changed.

## Follow-ups this opens

1. **The count rule still cannot read a table whose shape it has never seen.**
   The anchor assumes a size and a reference count sit immediately before the
   range. That holds for both shapes in the corpus, and nothing in the tree
   enforces it — a table that inserted a column between the reference count and
   the range would be read against the wrong cells again, silently, which is
   the failure mode this file is about. Header-driven resolution would not
   have it, and would need `units()` to carry the header, which is a change to
   a walk three other tools share.
2. **`--clusters` against a regeneration now holds more of §5 than it did.**
   Running the tool against a guard-off census reads three figures per §5 row
   rather than one. That is the intended consequence, and it is measured rather
   than estimated: the re-measurement issue #1240 asked for is written up in
   [`xdata-no-eq-guard-census-scale-join.md`](xdata-no-eq-guard-census-scale-join.md),
   which separates this change's contribution from the drift already in the
   figure that page published. What it leaves open is whether any §5 figure is a
   reading of a generation other than the committed one.
3. **`main-ec-005`'s named cell is a listing, so that row's named count is not
   checked.** It is the one §5 row where the fourth figure is a real gap rather
   than a read zero. Not worth a rule of its own for one cell.