# §4.4's identity figures, re-run against the committed census (issue #582)

`ec/annotations/xdata-register-map.md` §4.4 opens by promising that "Every
number below is a command re-run over the committed tree" and then quotes a
census the tree no longer holds. This is the record behind the correction that
landed with it: the commands and their real output, every superseded figure
beside the tree it was measured against, the numbers issue #582 proposed and
which of them a re-run confirms, and the stale figures this change deliberately
left for the next pass.

**Nothing here is a live observation.** The census is a static measurement of
committed decompiled C, and every figure below comes off the committed tree by
a command a reader can paste. **The CSVs are inputs, not outputs** — §4.4's
own argument is that a name is a human addition and an id is a rank, so a
regeneration that rewrote the committed census to match the prose would invert
the thing the section is about. Every run below writes to `/tmp`, and that is
structural rather than a promise this file makes:
`ec/tools/xdata_register_map.py:4606-4611` refuses `--no-eq-guard` with the
committed output paths.

## What the committed census holds, with a parser rather than a summary

```console
$ python3 - <<'PY'
import csv
rows = list(csv.DictReader(open('ec/annotations/xdata-clusters.csv')))
print(len(rows),
      sum(1 for r in rows if r['cluster_key']),
      sum(1 for r in rows if r['cluster_name']),
      sum(1 for r in rows if r['named_addrs'].strip()))
PY
439 439 9 59
```

439 rows, 389 `main-ec` and 50 `pd`; all 439 carry a `cluster_key`; **nine**
carry a `cluster_name`; 59 have a non-empty `named_addrs`. That last figure is
a different question — "at least one address in this cluster carries a name",
which is a property of the symbol table and not of the names file — and it is
not what any "key and no name" sentence in §4.4 counts.

**The 430 the issue keeps quoting is not a row count.** It is the tool's own
`with no name 430` line, printed on a guard-on `--check`:

```console
$ python3 ec/tools/xdata_register_map.py --check
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
```

`--check` is green, and it is the one command here that is wired into
`.github/scripts/agent-gates.sh`. Two of the three numbers on its first line —
9 names, 430 unnamed — are census facts about the committed CSV; the 439 on
the second is the row count, and the 430 on the first is 439 − 9.

## The regeneration, and the report

The recipe is `--no-eq-guard`: the `==` guard issue #178 added, taken back out
by the flag that now exists for it, into scratch outputs. This is
`xdata-06c2-06db-timers.md` §6a's measurement on the committed tree, and it
reproduces byte for byte across runs.

```console
$ rm -rf /tmp/reg && mkdir -p /tmp/reg
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/reg/registers.csv --out-clusters /tmp/reg/clusters.csv
wrote /tmp/reg/registers.csv: 1326 rows
wrote /tmp/reg/clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
  names: seeded 8, exact 0, carried by overlap 1, tied, not carried 0, with no name 436
    main-ec-002 carries mode-oem-init by overlap, Jaccard 0.97 from kefb63d82f8c7 -- re-key annotations/xdata-cluster-names.csv if the name moved
```

§4.4's transcript was a copy of the tool into `/tmp` with a Python
`str.replace` deleting the guard, because when the block was written no flag
did that. It does now, and the copied tool was one rename away from silently
regenerating the guard-on census — which is exactly what
`ec/tools/test_xdata_cluster_names.py` has been doing, below.

**439 committed clusters become 445**, and `--map` says where each committed id
went. Rows to stdout, summary to stderr, so the report redirects without the
prose ending up in it:

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/reg/registers.csv --out-clusters /tmp/reg/clusters.csv \
    --map ec/annotations/xdata-clusters.csv > /tmp/reg/map.csv
439 rows: 15 whose cluster_key changed, 15 whose membership changed, 5 with no
match at 0.50, 10 carrying a name
```

Every cell of §4.4's four-row table is a projection of `/tmp/reg/map.csv`
(`MAP_COLUMNS` at `xdata_register_map.py:390-393`), and this is the command that
reads them off:

```console
$ python3 - <<'PY'
import collections, csv
rows = list(csv.DictReader(open('/tmp/reg/map.csv')))
matched = [r for r in rows if r['match'] != 'none']
intact = [r for r in rows if r['old_cluster'] == r['new_cluster']
          and not r['added'] and not r['removed']]
claimed = collections.Counter(r['new_cluster'] for r in matched)
print('rows                      ', len(rows))
print('rank intact               ', len(intact))
print('rank changed              ', len(rows) - len(intact))
print('cluster_key unchanged     ', sum(1 for r in rows if r['key'] == 'unchanged'))
print('key, else overlap >= 0.50 ', len(matched))
print('claimed by >1 old row     ', sum(1 for n in claimed.values() if n > 1))
PY
rows                       439
rank intact                124
rank changed               315
cluster_key unchanged      424
key, else overlap >= 0.50  434
claimed by >1 old row      0
```

`124` and `315` are the same split the map's own issue-#279 correction already
quotes ("of the 439 committed clusters, 315 change what their `main-ec-NNN`
names and 124 do not"), so this re-run confirms that paragraph rather than
replacing it. The `claimed by >1 old row` cell is 0 for a reason worth keeping:
`--map` counts a claim only for a row that actually matched
(`xdata_register_map.py:4396-4398`), so a sub-threshold best guess cannot be
reported as a collision. The tool prints that cell's non-zero form itself, as
`a new cluster claimed by more than one old row`, and printed nothing.

### The clusters a key cannot carry

```console
$ python3 - <<'PY'
import csv
rows = list(csv.DictReader(open('/tmp/reg/map.csv')))
changed = [r for r in rows if r['key'] == 'changed']
over = sorted(r['jaccard'] for r in changed if r['match'] == 'overlap')
none = sorted(r['jaccard'] for r in changed if r['match'] == 'none')
print('a key cannot carry       ', len(changed))
print('  reach one on overlap   ', len(over), over)
print('  reach none at all      ', len(none), none)
PY
a key cannot carry        15
  reach one on overlap    10 ['0.50', '0.50', '0.50', '0.75', '0.88', '0.88', '0.91', '0.94', '0.97', '0.97']
  reach none at all       5 ['0.02', '0.03', '0.17', '0.25', '0.33']
```

The two the passage is about are the two largest clusters in the committed
census, and both are in it: `main-ec-001` (152 addresses) carries by overlap at
0.94 and `main-ec-002` (92) at 0.97. `main-ec-002` is the cluster
`mode-oem-init` names, the one §4.7's pair-accessor pass re-keyed, and the one
seven pages in this tree cite a membership for —
`grep -rlE 'main-ec-002\b' --include=*.md .` names seven files, and every one
of them makes a membership claim about the cluster.

### The names, and the margin

```console
$ python3 - <<'PY'
import csv
old = [r for r in csv.DictReader(open('ec/annotations/xdata-clusters.csv'))
       if r['cluster_name'].strip()]
new = [r for r in csv.DictReader(open('/tmp/reg/clusters.csv'))
       if r['cluster_name'].strip()]
def jaccard(a, b):
    a, b = set(a.split()), set(b.split())
    return len(a & b) / len(a | b)
best, runner = [], []
for n in new:
    scores = sorted((jaccard(n['addrs'], o['addrs']), o['cluster_name'])
                    for o in old)
    best.append(max(s for s, name in scores if name == n['cluster_name']))
    runner.append(max(s for s, name in scores if name != n['cluster_name']))
print('names file / census / this run:', len(old), len(new), len(new))
print('best match  %.2f..%.2f' % (min(best), max(best)))
print('next name   %.2f..%.2f' % (min(runner), max(runner)))
PY
names file / census / this run: 9 9 9
best match  0.97..1.00
next name   0.00..0.00
```

**Nine, not ten.** `ec/annotations/xdata-cluster-names.csv` holds nine rows, the
committed census holds nine `cluster_name` cells, and this regeneration carries
all nine — eight `seeded` and one, `mode-oem-init`, by overlap at 0.97. The
margin is as far from a cliff as §4.4 says it is: for every one of the nine the
best match against the nine committed named rows scores 0.97-1.00 and the best
*other* name scores 0.00, so any `CARRY_MIN_JACCARD` between 0.01 and 0.97
gives the same nine answers.

The `--map` summary's "10 carrying a name" is not a tenth name. It counts
*old rows* landing on a named new cluster, and one old row — `main-ec-145`, a
two-address row at Jaccard 0.02 — is printed with `mode-oem-init` in its
`cluster_name` cell while its `match` is `none`. It is a report cell showing
the best guess, not a carry, and `--map`'s own rule is the one that says so.

## The transcript this supersedes

§4.4 held one run of this experiment and this change re-ran it, so there are
two. The superseded one is reproduced here in full — the `rm -rf /tmp/census`
heredoc through the two `main-ec:`/`pd:` lines, as
`git show origin/main:ec/annotations/xdata-register-map.md` lines 1146-1173
give it — because the correction beside the map's block points here for it, and
that record should exist rather than sit in history. The map keeps the current
run alone, so its block still reads as one experiment.

```console
$ rm -rf /tmp/census && mkdir -p /tmp/census/ec/tools
$ cp ec/tools/xdata_register_map.py /tmp/census/ec/tools/
$ for d in decompiled annotations firmware ghidra; do
>   ln -s "$PWD/ec/$d" /tmp/census/ec/$d
> done
$ python3 - <<'EOF'
p = '/tmp/census/ec/tools/xdata_register_map.py'
s = open(p).read()
guard = '''    if stripped.startswith("=="):
        return False
'''
assert guard in s
open(p, 'w').write(s.replace(guard, ''))
EOF
$ python3 /tmp/census/ec/tools/xdata_register_map.py \
    --out-registers /tmp/census/registers.csv \
    --out-clusters /tmp/census/clusters.csv
  names: seeded 6, exact 0, carried by overlap 4, tied, not carried 0, with no name 429
    main-ec-002 carries mode-oem-init by overlap, Jaccard 0.96 from k5be7031564f8 -- re-key annotations/xdata-cluster-names.csv if the name moved
    main-ec-004 carries level-block-086x by overlap, Jaccard 0.64 from k2d9004f7707b -- re-key annotations/xdata-cluster-names.csv if the name moved
    main-ec-013 carries user-clear-bytes by overlap, Jaccard 0.90 from k76e75f349ea7 -- re-key annotations/xdata-cluster-names.csv if the name moved
    main-ec-022 carries page-0300 by overlap, Jaccard 0.78 from k3fdd14ddea2e -- re-key annotations/xdata-cluster-names.csv if the name moved
wrote /tmp/census/registers.csv: 1171 rows
wrote /tmp/census/clusters.csv: 439 rows
  main-ec: 1062 distinct addresses, 13957 references, 388 clusters at threshold 0.5
  pd: 157 distinct addresses, 861 references, 51 clusters at threshold 0.5
```

Every figure in it has moved and the table below names each: 1,171 register
rows against 1,326, `main-ec: 1062 distinct addresses, 13957 references, 388
clusters` against this run's 1218, 14838 and 394, `pd` 861 references against
858, six names seeded and four carried on overlap at 0.96, 0.64, 0.90 and 0.78
against eight seeded and one carried at 0.97, and the tenth name —
`page-0300`, carried at 0.78 from `k3fdd14ddea2e` — which the committed names
file no longer carries, for the reason the correction beside "All nine names
survive" gives. Its `with no name 429` is that cell read off its own run — ten
names against 439 clusters, 439 − 10 — where the guard-on `--check` above reads
430 off 439, and the two figures are the same question asked of two different
censuses rather than a disagreement, for the reasons the two-senses section
below gives.

## Every superseded figure, and what superseded it

Kept visible rather than deleted, per `docs/findings.md` §4a and the rule at
the top of `xdata-register-map.md`. Each row names the tree the figure was
measured against, which is the form that file's own corrections use — "the tree
#238 merged", not a date.

| superseded | by | why it moved |
|---|---|---|
| 427 clusters become 439 | 439 become 445 | the committed census moved under it in two steps, and **neither of them is #256**: 427 → 430 at #327's unnamed-callee pass (`37140548`), then 430 → 439 at #279's pair-accessor pass (`6bf9c234`). #256 regenerated both CSVs and left both counts where they were — 430 rows and ten names either side of it, as its own subject line says. The map's own H1 and §1 already read 439. |
| 48 ranks survive intact / 379 changed | 124 / 315 | same regeneration, re-run on the census as it stands. The map's issue-#279 correction already carried 315 / 124 for a second block, so this is a confirmation of that rather than a new claim. |
| 409 keys unchanged | 424 | same, off `/tmp/reg/map.csv` |
| 420 reach a new cluster by key, else overlap ≥ 0.50 | 434 | same. 439 − 434 = 5 is the summary's "5 with no match at 0.50" |
| 18 clusters a key cannot carry | 15 | same |
| 11 of the 18 on overlap / 7 on nothing | 10 / 5 | same; scores 0.50-0.97 and 0.02-0.33, against the block's 0.50-0.97 and 0.01-0.33 |
| `main-ec-002` (108 addresses) and `main-ec-003` (44) as the pair a key cannot carry | `main-ec-001` (152) and `main-ec-002` (92) | **different ids, not renamed ones.** On the tree §4.4 was written against the pair was the second and third largest; today the second and third are `main-ec-002` (92) and `main-ec-003` (43), and `main-ec-003`'s key did **not** change — it is `counter-sweep`, `seeded` at 1.00. The two the passage means are the two largest, and both are in the 15. |
| ten names, four carried on overlap | nine names, one carried on overlap | the tenth was `page-0300`, whose row issue #279's pair-accessor pass dropped (`6bf9c234`) when the nine-address `0x0300` cluster it named was absorbed into `main-ec-001`; the census's `cluster_name` column followed the file. Eight of the nine are `seeded`; `mode-oem-init` carries at 0.97 where the block's four carried at 0.96, 0.64, 0.90 and 0.78. |
| best match 0.64-1.00 across the ten | 0.97-1.00 across the nine | same re-run; the next named cluster is 0.00 for every one, before and after |
| 417 clusters have a key and no name | **430** | the census is 439 rows with nine `cluster_name` cells. This is also the tool's own `with no name 430` on a guard-on run — see the two senses below. |
| §4.4's write transcript, reproduced in full above | the `--no-eq-guard` transcript at the top of this file, which is the one §4.4 now carries | same experiment, re-run; the superseded block is reproduced here rather than left in history, because the map's correction paragraph points at this file for it. It brings three figures no other row names — 1,171 register rows against 1,326, `main-ec` 1,062 distinct addresses and 388 clusters against 1,218 and 394, and `pd`'s 861 references against 858. Its seeded/carried counts and `page-0300` are the row above. |
| §4.2's "That 479 is the one number … the §4.3 correction does not move" | 507 | the `--threshold-sweep --no-writer-axis` block beside it already read 507; the prose in the sentence after the block was the stale half. Re-derived at 0.50 `touching`: 507 clusters, largest 74, 274 singletons. |

**One figure issue #582 expected to be stale is not.**
`xdata-register-map.md` §4.2's "0.30 collapses 531 of the 1,218 into one
component" reads current on every part, and was left alone. 531 is the sweep's
`0.30,touching+writers` main-EC largest, and 1,218 is the committed census's
main-EC distinct address count — `xdata-registers.csv` is 1,326 rows split
1,169 `main-ec` / 108 `pd` / 49 `both`, and 1,169 + 49 = 1,218, which a plain
regeneration confirms by printing `main-ec: 1218 distinct addresses`. The plan
this change was built from took 1,218 for a pre-#279 relic left over from
"1,063 main-EC addresses" in `xdata-census-totals.md`; 1,063 + the 155 addresses
#279 added is the 1,218 the tree holds now, so the number is current and the
reading of it was not. §4.2's first threshold table is current for the same
reason — 389 clusters, largest 152, 200 singletons at 0.50 is the committed
census row for row, and the plateau sentence above it (273 → 152, 340 → 389, 0.55
adding 159) is current with it.

## The two senses of "a cluster with a key and no name"

Issue #582 asked for this to be said in the cells rather than in a footnote,
and the re-run is why. Two of §4.4's figures are about *the committed CSV* and
two are about *a regeneration of it*, and on the old tree the last of each pair
was the same integer:

- **430** clusters in the committed census carry a key and no `cluster_name`.
  A fact about `ec/annotations/xdata-clusters.csv`, equal to 439 − 9, and the
  same number the tool prints as `with no name 430`.
- **434** committed rows reach a new cluster by key, else best membership
  overlap ≥ 0.50, across the `--no-eq-guard` regeneration. A `--map` fact about
  a census that does not exist in the tree.

The two collided at 420 on the old tree — the table's cell and a prose figure
the issue read as the same one. These figures do not collide, so the specific
trap the issue describes is gone, and the two are still different questions that
happen to be three apart. §4.4 now says which is which in the table header and
in the sentence beside it, because a reader who has met the `with no name 430`
line will otherwise read it into the `--map` cell.

## The numbers issue #582 proposed

The issue is a re-run request that also carries a replacement arithmetic. Four
of its five figures do not survive a check against the committed tree, and the
fifth is the tool's own `with no name` line mistaken for a row count — the
conflation the issue itself warns about a paragraph later.

| what the issue asserts | what the committed tree says | command |
|---|---|---|
| "`xdata-clusters.csv` now holds 430" | **439** rows (389 `main-ec`, 50 `pd`) | the `csv.DictReader` block above |
| "430 rows, 10 with a `cluster_name`" | 439 rows, **nine** with a `cluster_name`, **430** with a key and no name | same, and `--check`'s first line |
| "`main-ec-001`/`main-ec-002` are 109 and 43 addresses" | 152 / 92. The prose's pair is `main-ec-002` (108) and `main-ec-003` (44) — **different ids**, on a different tree | `size` column of `xdata-clusters.csv`, sorted |
| "56 of the 430 clusters have at least one named address" | **59** of 439 | the same parser block, `named_addrs` |
| "the 427s, the table, the 18/11/7, the 417, the `--map` summary, the transcripts" | all re-derived above, to 445 / 124 / 315 / 424 / 434 / 0, 15 / 10 / 5, 430, and two new transcripts | the four commands above |

The 430 the issue keeps citing is the tool's `with no name 430` line, so the
issue and §4.4's own old table were not describing different censuses —
they were reading one cell of a report and calling it a count. The re-run wins,
and the disagreement is written down here rather than pasted into the page: a
reported number is a claim, and a claim that disagrees with a command a reader
can paste is not one to publish.

## Which tree §4.4 was measured against

Issue #433 asked for the census to be regenerated. It was still open when this
was written, and the CSVs the current tree carries are not the ones the block
was measured against — the block was not re-measured as the tree moved under
it. The moves that opened the gap:

- **#327's unnamed-callee pass** (`37140548`) took `xdata-clusters.csv` from
  427 to 430. That is the step #256 did not make.
- **#279's pair-accessor pass** (`xdata-register-map.md` §4.7, `6bf9c234`) added
  155 addresses across the same `0x03xx`-`0x05xx` working page, which merged
  three of the page's clusters into one and re-ranked the block. It took the
  census to **439** rows and dropped the tenth name, `page-0300`, leaving nine.
  **This is the tree the current CSVs came from.**
- **#256's regeneration** (`88a0e0ba`) rewrote both CSVs from the committed
  tree and **left every count where it was** — 430 rows and ten names either
  side of it, which is what its own subject line says it did.

*(Correction, 2026-09-25, issue #582. This section used to read "issue #256
performed it, so the tree the block was measured against is the tree the
current CSVs came from … **#256's regeneration** rewrote both CSVs from the
committed tree. That is what made `xdata-clusters.csv` 439 rows and
`xdata-cluster-names.csv` nine." The counts are right and the attribution is
not. `git show 88a0e0ba^:ec/annotations/xdata-clusters.csv` and
`git show 88a0e0ba:ec/annotations/xdata-clusters.csv` are both 430 rows, and
`xdata-cluster-names.csv` ten rows on both sides, where
`git show 6bf9c234^:ec/annotations/xdata-clusters.csv` is 430 and
`git show 6bf9c234:ec/annotations/xdata-clusters.csv` is 439 with the names file
at nine. #279's own correction in the map already credits it with dropping
`page-0300`. The old wording is kept rather than deleted, per `docs/findings.md`
§4a. The #433 note came from the issue's own premise, and a reported premise
is still a claim: this one disagreed with a command a reader can paste.)*

The gap paragraph §4.4 already carries — "the census committed here is behind a
fresh generation … 427 clusters to 430" — was overtaken by #327, which closed
it, and has a correction beside it. That correction is headed
"issue #256's regeneration", and the committed census it describes is 430 at
`88a0e0ba` either side — so it is not contradicted by the commands above, only
mis-attributed, the closure being #327's. It is another issue's correction in
a block this change was told to keep narrow, so it is recorded here rather than
edited, the same way the `k7497cf885614` row is recorded below. The paragraph
is left as it is: it is the record of a
gap that was real on its tree, which is the same reason the re-key it describes
is the reason the names file's own `Re-keyed 2026-09-24` note cites.

## What the re-run found that is not a figure: the §4.4 test is red

`ec/tools/test_xdata_cluster_names.py` **fails on the committed tree**, before
this change and independently of it:

```console
$ python3 ec/tools/test_xdata_cluster_names.py
................E.....
======================================================================
ERROR: setUpClass (__main__.TheGuardOffRegeneration)
...
AssertionError: the `==` guard is not where §6a's recipe deletes it; the
guard-off census this suite builds is not the one §6a measured
Ran 21 tests in 10.682s
FAILED (errors=1)
```

Twenty cases pass; the twenty-first cannot build its census. The cause is the
same drift §4.4's transcript had: `GUARD`
(`test_xdata_cluster_names.py:54`) is the literal
`'    if stripped.startswith("=="):\n        return False\n'`, and the guard in
the tool is now `if eq_guard and stripped.startswith("==")` at
`xdata_register_map.py:1582` — issue #302 parameterised it so `--no-eq-guard`
could be a flag instead of a source edit. The test's own comment says it is
built this way "rather than quietly regenerating the same census twice", and it
is doing exactly that: six cases want a guard-off regeneration and the
assertion is what stands between them and a guard-*on* one.

**There is a second, independent drift behind the first, and the `setUpClass`
error is hiding it.** `test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key`
(`test_xdata_cluster_names.py:651-666`) pairs `main-ec-001` with
`mode-oem-init` and `main-ec-002` with `level-block-086x`; the committed census
puts `mode-oem-init` at `main-ec-002` and `level-block-086x` at `main-ec-004`.
So repairing the guard alone would trade one red for another. And on the
committed census the case's premise is only half true in any case:
`level-block-086x` is `seeded` there — key and membership both unchanged — and
`main-ec-002` is the one of the two carried on overlap, at 0.97. That is also
what makes §4.4's "the test that settles it" paragraph half stale, and the
correction in the map says so where the sentence is.

**Not fixed here, and the reason is the issue's own scope.** Issue #582 scopes
itself to documentation and says "`--check` and `--self-test` are unchanged";
both are green on this tree. The fix is two changes to the suite — the recipe
becomes `--no-eq-guard` with scratch outputs, which the tool already accepts and
which is the command now transcribed in §4.4, and the two-largest case's id/name
pairs are re-read from the committed census — and both are behaviour changes to
a test, so they are a follow-up rather than lines to move inside a
documentation change. The suite is also not wired into
`.github/scripts/agent-gates.sh`, so nothing has been failing CI over it.

## Deliberately not fixed, with the line a next pass needs

Recorded so the next pass does not rediscover them. Each is a separate block
carrying its own measurement, and none is a census total; the ones that already
carry a correction naming their tree are left as they are.

- `ec/README.md:120-124` — "the 427 committed clusters" and the 425/59/366/413
  figures of its own threshold re-run.
- `ec/README.md:279` — "Ten of the 427 clusters have one"; the names file holds
  nine of 439.
- `ec/tools/test_xdata_cluster_names.py:307` — a third-generation figure in the
  suite's docstring, "427 clusters become 439, 48 … 379", plus the second
  generation beside it at "430 → 439 with 64 ranks intact and 366 changed". A
  guard-on re-run of the committed tree is 439 → 439 with nothing moved, since
  `--check` is green. The suite's *assertions* are threshold-based
  (`assertGreater(len(moved), 300)`) and do not depend on any of it.
  *(Measured, 2026-09-25, issue #852: the second generation re-derives from
  `e169a0e4` and gives 366 / 64 / 439 exactly, and the fall from it to 315 is
  accounted for by 94 named clusters — see
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md). The docstring bullet
  itself stands as written: the figures are the trees they were measured on.)*
- `ec/tools/xdata_register_map.py:2723` and `:2885` — two comments in the tool
  carrying "the committed 427 ids" and "417 of the 427 clusters".
- `ec/tools/test_xdata_cluster_names.py:355-370` — this file's own `:403` cites
  the suite at `:355-370` for
  `test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key`, which
  is at `:459-473`; the cited span is §6a's assertion block, which pairs no ids.
  **Stale before the #852 merge and recorded rather than repointed**, because
  the pin is #582's, written when the suite was that much shorter, and
  `check_citation_lines.py` holds citations into the generated CSVs and the
  decompile rather than into a test file, so nothing turns it red — which is the
  same "not found by this method" the checker prints. The same is true of
  `xdata-census-self-test-gate.md:221`'s
  `xdata-cluster-names-guard-off-recipe.md:406-407`, for a sentence at `:446-447`.
- `ec/tools/check_cluster_citations.py:17-20` — its module docstring carries the
  427/439/48 and the 425/59/366/413 figures. **Not a false claim**: the checker
  is green because it resolves citations against the committed CSV, and the
  docstring's numbers are its own historical measurement. The same 427 is
  quoted by `ec/README.md`, which is where that docstring's text is shared.
- `ec/annotations/xdata-register-map.md:189`, `:360`, `:404` — the H1/§1
  reproduction blocks and their correction paragraphs, which already say in
  place that their figures are the tree they were measured on.
- `ec/annotations/xdata-register-map.md:1909`, `:1917`, `:1992`, `:2001` — §5's
  drift record and its two re-derivation blocks, which carry the "430 against
  the committed 427" contrast and the `k7497cf885614` row under an issue-#256
  correction that already says the gap closed.
- `ec/annotations/xdata-register-map.md:1272` — §4.4's own issue-#256
  correction says `xdata-cluster-names.csv` "carries `k7497cf885614` and its
  eight siblings", in the present tense; issue #279 re-keyed that row to
  `kefb63d82f8c7`. Another issue's correction, in a block this change was told
  to keep narrow, so it is recorded rather than edited.
- `docs/findings/xdata-census-totals.md`'s own totals — 1,171 / 430 /
  `named_in_tree` 162 against a tree that now reads 1,326 / 439 / 175. That
  file is a record of a measurement against a named tree and says so; only its
  follow-up 4 is this change's business, and follow-up 4 is now retired there.

## The gates this change was measured against

| command | reading on this tree |
|---|---|
| `python3 ec/tools/xdata_register_map.py --check` | green — 1,326 register rows, 439 cluster rows |
| `python3 ec/tools/xdata_register_map.py --self-test` | green — all assertions passed |
| `python3 ec/tools/check_cluster_citations.py` | exit 0 — every cluster citation resolves, every hand-typed census count agrees |
| `python3 ec/tools/test_xdata_cluster_names.py` | **red** — one `setUpClass` error, above. Pre-existing, and reported rather than edited around. |
| `bash .github/scripts/agent-gates.sh` | green, including `doc links` |
