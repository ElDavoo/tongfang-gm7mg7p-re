# Re-deriving the export-ownership page: every figure on `xdata-export-ownership.md`, from a fresh run (issue #654)

`ec/annotations/xdata-export-ownership.md` measures what `--export-ownership`
does to the XDATA census, and it was still quoting the census totals from
before issue #267. #267 gave `0x1665`, `0x1666` and `0x166A` their
`registers.yaml` rows, which re-spells three references as symbols and adds
three more: the census moved 14,819 → 14,822 references on the default side and
9,401 → 9,404 on the de-duplicated one, and the tool's own `ORACLE` and
`OWNERSHIP` were re-pinned for it. The page did not move with them, so seven of
its cells had been a tree that no longer exists.

This is the re-derivation that page needed, not a restatement of it. Every
figure on it is recomputed below from a fresh run of the committed tool, and
the page is corrected only where that run disagrees. It is deliberately a
*page measurement* and not a test: see
[`xdata-export-ownership-refusal-contract.md`](xdata-export-ownership-refusal-contract.md)
§Calibration, which decided that these figures stay relations and page
measurements rather than suite pins, because re-pinning them would make a
refusal-contract suite red for an unrelated re-derivation.

> **(2026-09-25, issue #279: this is a snapshot, and every cluster id in it is
> the one the #654 runs printed — not the one the census carries now.)** #279
> re-derived the census, adding 39 `cluster_key`s among the main-EC rows
> (380 → 389) and moving the ranking under them, so the two runs transcribed
> below name clusters the committed census no longer numbers that way. They are
> left as the runs printed them, per `docs/findings.md` §4a, rather than
> renumbered into transcripts that never happened. For the two this page leans
> on: the 43-address / 4,966-reference counter block (`main-ec-002` throughout,
> key `k733222e83898`) is **`main-ec-003`** today, and the 28-address
> `level-block-086x` block (`main-ec-003`, key `ka39cda99615f`) is
> **`main-ec-004`**; `ff-fill-stubs` is still `main-ec-007` (key
> `kea0c67af9b51`). The
> `mode-oem-init` key is the one that did not merely move rank — `k7497cf885614`
> names a membership the census has lost, and the name now rides
> `kefb63d82f8c7` on `main-ec-002` (92 addresses), re-keyed for #279 in
> `ec/annotations/xdata-cluster-names.csv`. `cluster_key` is the stable handle
> and `main-ec-NNN` is a rank slot; every conclusion below is a relation
> between keys or a count, and none of them turns on a rank.
> `ec/annotations/xdata-export-ownership.md` itself has been renumbered to the
> current ids, because its rows are membership claims against the committed
> census rather than a record of a run.

Nothing here is an EC finding. No register's `status:` changed, no
`registers.yaml` row was added, no census CSV was regenerated, no hardware or
Windows machine was involved, and both committed census CSVs are byte-identical
before and after the two runs below. Every figure is a count in decompiled
text, which is evidence about static shape and never about what the EC does
with a byte; a zero is "not found by this method", never "absent"
(`docs/findings.md` §4c).

## The two runs, and the only way to get the "after" half

The page's own §5 prints these, and they are copied here verbatim so a reader
does not have to find them. Both write **only** to `/tmp`. `--export-ownership`
is refused with `--check` and with `--self-test`, and refused without scratch
`--out-registers` *and* `--out-clusters`, on the grounds the sibling flag's
refusal contract records: both guards are about the committed CSVs, and a flag
that re-buckets occurrences while writing nothing must not be answerable from a
mode whose claim is that those files already match. So a scratch write is the
only route to the after side.

```console
$ python3 ec/tools/xdata_register_map.py --out-registers /tmp/before-registers.csv \
    --out-clusters /tmp/before-clusters.csv
  names: seeded 10, exact 0, carried by overlap 0, tied, not carried 0, with no name 420
wrote /tmp/before-registers.csv: 1171 rows
wrote /tmp/before-clusters.csv: 430 rows
  main-ec: 1062 distinct addresses, 13964 references, 380 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 50 clusters at threshold 0.5

$ python3 ec/tools/xdata_register_map.py --export-ownership \
    --out-registers /tmp/after-registers.csv --out-clusters /tmp/after-clusters.csv
  names: seeded 5, exact 0, carried by overlap 3, tied, not carried 0, with no name 424
    main-ec-001 carries mode-oem-init by overlap, Jaccard 0.97 from k7497cf885614 -- re-key annotations/xdata-cluster-names.csv if the name moved
    main-ec-003 carries level-block-086x by overlap, Jaccard 0.75 from ka39cda99615f -- re-key annotations/xdata-cluster-names.csv if the name moved
    main-ec-007 carries ff-fill-stubs by overlap, Jaccard 0.60 from kea0c67af9b51 -- re-key annotations/xdata-cluster-names.csv if the name moved
wrote /tmp/after-registers.csv: 1171 rows
wrote /tmp/after-clusters.csv: 432 rows
  main-ec: 1062 distinct addresses, 8546 references, 382 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 50 clusters at threshold 0.5
```

The committed pair is untouched by both:

```console
$ md5sum ec/annotations/xdata-registers.csv ec/annotations/xdata-clusters.csv
c9a45a9a7ceaa9a3969b3581ce91a47a  ec/annotations/xdata-registers.csv
57ac9bf204e20cf9d7ab256498ab58d6  ec/annotations/xdata-clusters.csv
$ git status --porcelain
```

(the `md5sum` above was taken before *and* after the two runs; `git status`
prints nothing.)

## The census figures, cell by cell

`tail -n +2` skips the header and nothing else, so the `awk` conditions carry
**no `NR` test** — `docs/findings/xdata-census-totals.md` records what
`NR>1` does to that line, and the trap is worth re-reading once rather than
re-learning. Column 6 is `refs`; columns 7-11 are the five buckets.

```console
$ tail -n +2 /tmp/before-registers.csv | wc -l
1171
$ tail -n +2 /tmp/before-registers.csv | awk -F, '{s+=$6} END{print s}'
14822
$ tail -n +2 /tmp/before-registers.csv \
    | awk -F, '{r+=$7;w+=$8;rw+=$9;p+=$10;a+=$11} END{print "read",r,"write",w,"read+write",rw,"passed-to-call",p,"address-taken",a}'
read 8344 write 3195 read+write 2482 passed-to-call 534 address-taken 267
$ tail -n +2 /tmp/before-clusters.csv | wc -l
430

$ tail -n +2 /tmp/after-registers.csv | wc -l
1171
$ tail -n +2 /tmp/after-registers.csv | awk -F, '{s+=$6} END{print s}'
9404
$ tail -n +2 /tmp/after-registers.csv \
    | awk -F, '{r+=$7;w+=$8;rw+=$9;p+=$10;a+=$11} END{print "read",r,"write",w,"read+write",rw,"passed-to-call",p,"address-taken",a}'
read 4923 write 2707 read+write 1018 passed-to-call 500 address-taken 256
$ tail -n +2 /tmp/after-clusters.csv | wc -l
432
```

Cluster `refs` sums to the register total on both sides, which is the same
projection `--self-test` asserts and is here only the cheapest cross-check that
column 4 was the column read:

```console
$ tail -n +2 /tmp/before-clusters.csv | awk -F, '{s+=$4} END{print s}'
14822
$ tail -n +2 /tmp/after-clusters.csv | awk -F, '{s+=$4} END{print s}'
9404
```

Everything the page derives *from* those two runs — what moves, what is lost,
what the flip would cost — comes out of the same pair of files:

```console
$ python3 - <<'PY'
import csv
b = {r['addr']: r for r in csv.DictReader(open('/tmp/before-registers.csv'))}
a = {r['addr']: r for r in csv.DictReader(open('/tmp/after-registers.csv'))}
print('addresses whose refs move:',
      sum(1 for k in b if b[k]['refs'] != a.get(k, b[k])['refs']))
print('addresses lost:', sorted(set(b) - set(a)) or 'none')
print('addresses gained:', sorted(set(a) - set(b)) or 'none')
bk = {r['cluster_key'] for r in csv.DictReader(open('/tmp/before-clusters.csv'))}
ak = {r['cluster_key'] for r in csv.DictReader(open('/tmp/after-clusters.csv'))}
print(f'cluster keys: {len(bk)} committed, {len(bk & ak)} survive, {len(ak - bk)} new')
names = list(csv.DictReader(open('ec/annotations/xdata-cluster-names.csv')))
print(f'hand names: {len(names)}, '
      f'{sum(1 for n in names if n["cluster_key"] in ak)} survive, '
      f'{sum(1 for n in names if n["cluster_key"] not in ak)} break')
for addr in ('0x0843', '0x0844', '0x06D6', '0x0706', '0x08A8'):
    print(f'  {addr}: refs {b[addr]["refs"]} -> {a[addr]["refs"]}, '
          f'functions_touched {b[addr]["functions_touched"]} -> '
          f'{a[addr]["functions_touched"]}')
PY
addresses whose refs move: 228
addresses lost: none
addresses gained: none
cluster keys: 430 committed, 395 survive, 37 new
hand names: 10, 5 survive, 5 break
  0x0843: refs 168 -> 4, functions_touched 42 -> 1
  0x0844: refs 168 -> 4, functions_touched 42 -> 1
  0x06D6: refs 148 -> 4, functions_touched 37 -> 1
  0x0706: refs 160 -> 4, functions_touched 40 -> 1
  0x08A8: refs 170 -> 6, functions_touched 44 -> 3
```

That last block is also §1's table, §4's "the defect really is fixed" sentence
and §5's renumbering cost, all from one pass. The `functions_touched` column
is the whole column, which is why `0x08A8` reads 44 rather than 42: its
touchers include `bank0:0xA139=FUN_CODE_a139` and
`bank0:0xA1A8=set_state_bytes_then_0xa1c8`, which are not in the 42-file run.

## The main-EC `refs` row, the one no oracle-asserted table catches

The refusal-contract page's re-measured table prints total `refs` and `read`
and **no main-EC row**, so a reader who reconciles the page against that table
alone fixes two of the three columns and leaves `main-EC refs` contradicting
`ORACLE` and `OWNERSHIP`. Nor can it be inferred from the totals: the PD half
is unmoved by #267, but that is a fact about #267 rather than arithmetic, and
inference is not a derivation.

It does not need one, though. `write()` prints per-group totals on the way out
(`xdata_register_map.py:2448-2452`), and both runs above show the line:

| | `main-ec` distinct | `main-ec` references | `pd` distinct | `pd` references |
|---|---:|---:|---:|---:|
| default (`--out-registers`…) | 1,062 | **13,964** | 157 | 858 |
| `--export-ownership` | 1,062 | **8,546** | 157 | 858 |

That is the row the page had at 13,961 / 8,543, and it is read off each run's
own stdout rather than reconstructed. `--self-test` asserts
`ORACLE["main_refs"]` 13,964 but not `OWNERSHIP["main_refs"]`, and
`OWNERSHIP`'s own comment says so at the point where it matters: `main_refs` is
"not asserted by --self-test (only `distinct`, `refs` and the buckets are); it
is re-derived rather than carried forward, so it is not left stale beside a
total that moved." The above is that re-derivation.

## The two `main-ec-002` rows, and why a lookup on `cluster_id` is the wrong recipe

These are the page's §4 rows "the 43 addresses of `main-ec-002`" and
"`main-ec-002` cluster `refs`", and they appear in **no** oracle — not in
`ORACLE`, not in `OWNERSHIP`, not in `export_ownership.py`'s
`OWNERSHIP_ORACLE`. They are a page measurement, and #267's read-only symbol
rename is no reason to assume they held: the whole question of this issue is
whether a page's figures still hold, and assuming is what left seven cells
stale.

The recipe is the trap. **Looking up `cluster_id == "main-ec-002"` in the after
census is wrong**, because the pass renumbers `cluster_key` on 35 of the 430
clusters: after the pass, the cluster that carries the id `main-ec-002` is a
*different membership* (28 of the 43 addresses, key `k22aecb4dc595` against the
committed `k733222e83898`). The correct recipe is to take the 43 addresses from
the committed row and read them back **by address**:

```console
$ python3 - <<'PY'
import csv, collections

# the 43 addresses, taken from the committed main-ec-002 row by name
want = next(r['addrs'].split() for r in
            csv.DictReader(open('ec/annotations/xdata-clusters.csv'))
            if r['cluster_id'] == 'main-ec-002')
for side in ('before', 'after'):
    reg = {r['addr']: r for r in csv.DictReader(open(f'/tmp/{side}-registers.csv'))}
    cls = {r['cluster_id']: r for r in
           csv.DictReader(open(f'/tmp/{side}-clusters.csv'))}
    missing = [a for a in want if a not in reg]
    total = sum(int(reg[a]['refs']) for a in want if a in reg)
    hold = collections.Counter(reg[a]['cluster_id'] for a in want if a in reg)
    print(f'{side}: {len(want)} addresses, missing {missing or "none"}, '
          f'sum of refs {total}')
    print(f'  over {len(hold)} clusters: ' +
          ', '.join(f'{c} x{n}' for c, n in sorted(hold.items())))
    print(f'  the clusters the committed id lands on: ' +
          ', '.join(f'{c} refs {cls[c]["refs"]} key {cls[c]["cluster_key"]}'
                    for c in sorted(hold) if c == 'main-ec-002'))
PY
before: 43 addresses, missing none, sum of refs 4988
  over 1 clusters: main-ec-002 x43
  the clusters the committed id lands on: main-ec-002 refs 4966 key k733222e83898
after: 43 addresses, missing none, sum of refs 460
  over 12 clusters: main-ec-001 x3, main-ec-002 x28, main-ec-003 x3, main-ec-004 x1, main-ec-118 x1, main-ec-192 x1, main-ec-194 x1, main-ec-240 x1, main-ec-243 x1, main-ec-262 x1, main-ec-263 x1, main-ec-268 x1
  the clusters the committed id lands on: main-ec-002 refs 280 key k22aecb4dc595
```

**A recipe that does not reproduce the default side first is the wrong recipe,
and is reported as such rather than used.** This one reproduces 4,988 and
4,966 exactly on the side the page already had, which is the test of whether it
is the right one; the after side then reads 460 and 280, and those are what the
page already said too. So both of the page's `main-ec-002` rows **held** —
they are the two rows of §4 that a `cluster_id` lookup would have got wrong on
the after side, and the reason this is a re-derivation rather than a hand-edit.

Note also what the after side says that the page does not: those 43 addresses
no longer live in one cluster. 28 of them stay together under the id
`main-ec-002`, and the other 15 scatter into eleven other clusters. §5's "which
is `main-ec-002`'s own key and does not survive as a single cluster at all" is
a weaker statement of the same fact, and still true.

## What re-derived and did not move: the `export_ownership.py` family

The page's §3 and its first §4 table are `ec/tools/export_ownership.py`'s own
figures, not the census tool's, and #267 changed the symbol table rather than
any `.c` file — so they should not have moved. They are re-derived anyway,
because a figure nobody looked at is a figure nobody can say held.

`ec/tools/export_ownership.py --self-test` is the derivation, and it is green:

```console
$ python3 ec/tools/export_ownership.py --self-test
export_ownership.py --self-test
  ok    an overlapping pair folds into the larger body
  ok    a genuinely distinct pair does not fold
  ok    a one-statement fragment folds into a big body, never the reverse
  ok    and at the default floor of 3 a one-statement body is not compared at all, so it stays its own owner
  ok    equal bodies are each their own owner under strict containment
  ok    and --fold-equal collapses them to the lowest address
  ok    a cross-program pair never folds
  ok    an empty-after-normalization body folds into nothing
  ok    one row per index.csv row (2714), at threshold 0.9 and floor 3
  ok    56 containment classes, 146 non-owner rows
  ok    the 42-file class is owned by bank1/8001.c, the run's own start address
  ok    the body floor is load-bearing: 7 chained classes with it, 13 without it, and at the committed threshold a floor of 1 giving 28 classes with a 562-member flood
  ok    1276 of the 2714 bodies are too short to carry a containment claim, so the floor is not a rounding boundary
  ok    every non-owner records its own containment score against the owner, so a chained member is visible in the CSV rather than hidden by the grouping (29 are below the threshold)
  ok    the committed CSV is a fresh derivation from the committed tree
all checks passed
```

That covers §3's body-floor table in both rows (floor 1 → 28 classes / 13
chained / 562 largest; floor 3 → 56 / 7 / 42), §3's "seven classes", "29 of the
146 non-owners", and §4's first table (2,714 rows, 56 classes, 146 non-owner
rows, largest 42 owned by `bank1/8001.c`, 1,276 bodies too short, 29 chained
non-owners). **All held.**

The 4,642 of §2's prose is the counter-sweep case in the *other* tool's
`--self-test`, which prints it against the cluster's own 4,966:

```console
$ python3 ec/tools/xdata_register_map.py --self-test | grep counter-sweep
  ok    and the cluster named `counter-sweep` is the one whose references are dominated by the 42-file group -- main-ec-002 is 4642/4966 = 93%
```

The page's §3 *prose* numbers are not in that oracle, so they get their own
derivation:

```console
$ python3 - <<'PY'
import sys
sys.path.insert(0, 'ec/tools')
import export_ownership as eo

rows = eo.load_rows()
bodies = eo.load_bodies(rows)
one = [r for r in rows if len(bodies[r['out_file']]) == 1]
flood = max(eo.classes_of(rows, bodies, eo.THRESHOLD, False, 1).values(), key=len)
rest = {r['out_file'] for r in flood if len(bodies[r['out_file']]) > 2}
sub = [c for c in eo.classes_of(rows, bodies, eo.THRESHOLD, False,
                                eo.MIN_BODY_STMTS).values()
       if {x['out_file'] for x in c} & rest]
big = sorted(flood, key=lambda r: len(bodies[r['out_file']]), reverse=True)[:2]
print(f'bodies {len(rows)}, two statements or fewer '
      f'{sum(1 for r in rows if len(bodies[r["out_file"]]) < eo.MIN_BODY_STMTS)}, '
      f'a single statement {len(one)}, naming return '
      f'{sum(1 for r in one if any("return" in s for s in bodies[r["out_file"]]))}, '
      f'exactly "return" '
      f'{sum(1 for r in one if "return" in bodies[r["out_file"]])}')
print(f'floor-1 flood {len(flood)} members, programs '
      f'{sorted({r["program"] for r in flood})}, of them fragments '
      f'{sum(1 for r in flood if len(bodies[r["out_file"]]) <= 2)}, '
      f'non-owners dropped if folded {len(flood) - 1}')
print(f'the two largest members '
      f'{[len(bodies[r["out_file"]]) for r in big]} statements, containment '
      f'{eo.containment(*sorted((bodies[big[0]["out_file"]], bodies[big[1]["out_file"]]), key=len)):.4f}')
print(f'the {len(rest)} left after the fragments come out: '
      f'{sum(1 for c in sub if len(c) > 1)} classes of more than one, '
      f'largest {max(len(c) for c in sub)}')
PY
bodies 2714, two statements or fewer 1276, a single statement 495, naming return 427, exactly "return" 112
floor-1 flood 562 members, programs ['bank1'], of them fragments 155, non-owners dropped if folded 561
the two largest members [78, 67] statements, containment 0.0149
the 407 left after the fragments come out: 17 classes of more than one, largest 42
```

1,276, 495, 427, 112, 562, 155, 561, 78, 67, 1.5%, 407 and 42 — §3's whole
prose paragraph, and **all of it held**.

One reading note, because the last line is a filter the page does not spell
out: the 407 members do not fall into *17* classes, they fall into 343, of
which 17 hold more than one member. The page counts the classes that assert
something, and the largest is 42 either way. It is the same filter
`export_ownership.py --self-test` applies to the 56 above the page's §4 table
(`real = [m for m in comps.values() if len(m) > 1]`), and it is stated here so
a reader who runs either count without it does not think the page is wrong.

## The reconciliation, every cell against every oracle

| page figure | page said | re-derived | `ORACLE` / `OWNERSHIP` / `BUCKET_TOTALS` | verdict |
|---|---:|---:|---|---|
| §1 prose, census total | 14,819 | 14,822 | `ORACLE["refs"]` 14,822 | **corrected** |
| §2, Reading A before and after | 14,819 → 14,819 | 14,822 → 14,822 | as above | **corrected** |
| §2, Reading B before and after | 14,819 → 9,401 | 14,822 → 9,404 | `ORACLE["refs"]`, `OWNERSHIP["refs"]` | **corrected** |
| §2, the 43 addresses (A and B) | 4,988 → 4,988 / 460 | 4,988 → 4,988 / 460 | in no oracle; by address | held |
| §2, addresses that move | 0 of 1,171 (A) / 228 of 1,171 (B) | same | `OWNERSHIP["moved"]` 228 | held |
| §2 prose, `co_reading_refs` | 4,642 of 4,988 | 4,642 and 4,988 both reproduce | `--self-test`'s counter-sweep case, which prints 4,642/4,966 | held |
| §3, body floor table | 28/13/562 and 56/7/42 | same | `OWNERSHIP_ORACLE` | held |
| §3 prose (1,276 … 407 in 17) | as printed | as printed | in no oracle; re-derived above | held |
| §3, chained classes and non-owners | 7 and 29 of 146 | 7 and 29 of 146 | `OWNERSHIP_ORACLE["bridged"]` | held |
| §4, CSV rows / classes / non-owners | 2,714 / 56 / 146 | same | `OWNERSHIP_ORACLE` | held |
| §4, largest class, tiny bodies, chained | 42, 1,276, 29 | same | `OWNERSHIP_ORACLE` | held |
| §4, distinct addresses | 1,171 | 1,171 | both oracles | held |
| §4, total `refs` | 14,819 → 9,401 | 14,822 → 9,404 | both oracles | **corrected** |
| §4, main-EC `refs` | 13,961 → 8,543 | 13,964 → 8,546 | `ORACLE`/`OWNERSHIP` `main_refs` | **corrected** |
| §4, `read` | 8,341 → 4,920 | 8,344 → 4,923 | `BUCKET_TOTALS` read, `OWNERSHIP` read | **corrected** |
| §4, `write` | 3,195 → 2,707 | 3,195 → 2,707 | both | held |
| §4, `read+write` | 2,482 → 1,018 | 2,482 → 1,018 | both | held |
| §4, `passed-to-call` | 534 → 500 | 534 → 500 | both | held |
| §4, `address-taken` | 267 → 256 | 267 → 256 | both | held |
| §4, the 43 addresses | 4,988 → 460 | 4,988 → 460 | in no oracle; by address | held |
| §4, `main-ec-002` cluster `refs` | 4,966 → 280 | 4,966 → 280 | in no oracle; by address | held |
| §4, clusters | 430 → 432 | 430 → 432 | `OWNERSHIP["clusters"]` | held |
| §4, addresses that move / lost | — / 228 / 0 | — / 228 / 0 | `OWNERSHIP["moved"]`, `["lost"]` | held |
| §4 prose, the five addresses | 168→4, 168→4, 148→4, 160→4, 170→6 | same | `--self-test` pins `0x0843`'s 168 and 4; the other four from the derived block | held |
| §4 correction prose, "measures N with nothing lost" | 9,401 | 9,404 | `OWNERSHIP["refs"]` | **corrected** |
| §5, keys that move / survive / new | 35 / 395 / 37 | 35 / 395 / 37 | `OWNERSHIP["cluster_keys_kept"]` | held |
| §5, hand names that break | 5 of 10, `counter-sweep` among them | 5 of 10, and it is | `OWNERSHIP["hand_names_kept"]` 5 | held |
| §5, `main-ec-002` `refs` and the cluster count | 4,966 → 280, 430 → 432 | same | by address / `OWNERSHIP["clusters"]` | held |

**Seven cells corrected, twenty-one re-derived and held.** Every corrected
cell is the census pair and the `read` bucket, on both sides; the shape of the
correction is uniform, which is what #267's own block says it should be —
three addresses, each re-spelled rather than re-counted, each of the three a
read, so `read` takes +3 and `refs` +3 and the other four buckets do not move
at all.

Against the refusal-contract page's own re-measured table, the page now agrees
on every column it prints — total `refs` 14,822 / 9,404, `read` 8,344 / 4,923,
`write` 3,195 / 2,707, `read+write` 2,482 / 1,018, `passed-to-call` 534 / 500,
`address-taken` 267 / 256, distinct addresses 1,171 / 1,171, clusters 430 /
432 — and the one column that table omits, main-EC `refs`, agrees with both
oracles by its own derivation above. **The deferral sentence at the foot of
that write-up is satisfied**, and a correction sits beside it rather than
replacing it.

## The escape hatch this change did not need

The rule this page works under is that a figure which cannot be traced to a
re-derivation is recorded as **unverified on this tree**, and the page says so
where the reader would meet it, rather than the page being edited to a number
taken from memory.

Nothing had to be recorded that way. Every figure on the page traced to one of
the derivations above or to a green `--self-test`, including the two rows and
the one oracle-omitted column that were most at risk of being taken on trust.
The page needed no unverified marker, and none was added — which is itself the
result worth recording, since the alternative finding (a figure on this page
that cannot be re-derived) would have been a different issue.

## What this does not establish

- **It is not a census change.** Neither run wrote a committed file; the
  `md5sum` pair and an empty `git status` are above. The census totals in
  `ORACLE` and `OWNERSHIP` were already correct for this tree — the page was
  the only stale artifact, which is the same shape
  `docs/findings/xdata-census-totals.md` found for
  `ec/annotations/xdata-register-map.md`.
- **It is not a function boundary, and it does not flip the default.** §6 of
  the page is unchanged and still right. The flip is §5's own separate PR,
  after the export-boundary fix, and this change does not move toward it.
- **The figures are not behavioural claims.** Every number here is a count in
  decompiled text, or a count of files, and both are lower bounds on the
  machine code. Nothing was read back from hardware and no register's
  `status:` moved.
- **The `lost` = 0 result is a measurement of one detector's grouping on one
  tree**, not a proof the pass can never lose an address, and it stays worded
  that way. It is pinned in `OWNERSHIP["lost"]` so a re-export that made it
  non-empty would fail a check rather than shorten a census quietly.
- **The same pre-#267 pair on other pages is not fixed here.**
  `ec/annotations/xdata-06c2-06db-timers.md` §6a and §8,
  `ec/annotations/xdata-register-map.md`, `ec/README.md:226` and the rest of
  `docs/findings.md`'s census prose still carry it. Each is a separate long
  shared document, and #583 already owns a checker for the class.
