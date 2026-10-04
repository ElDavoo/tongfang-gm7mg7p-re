# The working page's cluster count, both sides of the pass, and what the added addresses have to do with it (issue #903)

**Nothing here is a hardware claim.** No register was read back, no firmware
image was opened, and no laptop, EC or Windows machine is involved. Every
figure below is the output of a command over two committed CSVs and one
historical commit; the tool reads those files and writes nothing, so a run
leaves `git status --porcelain` exactly as it found it. Same framing as
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):3.

The note on `mode-oem-init` in
[`ec/annotations/xdata-cluster-names.csv`](../../ec/annotations/xdata-cluster-names.csv)
ends *"which merged three of the page's clusters into one"*. That was the
unmeasured half of what #884 settled; §5 of
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) measured the
other half and left this one standing. This measures it.

**The short answer, and it splits the note's sentence in two.** The page holds
**109 page clusters before the pass and 116 after**, and the merge half of the
sentence is true: `k462303ed5f86` took in three earlier page clusters whole and
none of their keys survives, so **a three-into-one merge of the page's clusters
did happen** and the note's count of three is not invented. The *"which"* is a
separate claim — that the 155 addresses are what did it — and **this pair of
censuses cannot support it in either direction**. The test that looks as though
it settles the question comes out zero *by construction* rather than by
measurement, and the 151 on-page additions landed inside the merged clusters
themselves. §4 has the counts; §5 has the last two sentences and why the causal
half is out of reach from two clusterings.

## 1. The two sides, and that the tree has not moved under them

The far side is commit `e169a0e4`, reached the same way
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) §1 reaches
it; the near side is the committed pair. `--check` says the near side is a
faithful generation of the committed tree, so the two are comparable.

```console
$ git cat-file -e e169a0e4a736956f35af5ffff65e997154c76bdd^{commit} && echo present
present
$ git worktree add --detach /tmp/xdata-old e169a0e4a736956f35af5ffff65e997154c76bdd
$ python3 ec/tools/xdata_register_map.py --check
ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
$ python3 ec/tools/xdata_page_clusters.py \
    --old-clusters /tmp/xdata-old/ec/annotations/xdata-clusters.csv \
    --new-clusters ec/annotations/xdata-clusters.csv \
    --old-registers /tmp/xdata-old/ec/annotations/xdata-registers.csv \
    --new-registers ec/annotations/xdata-registers.csv \
    --label e169a0e4 --label-new committed
```

The added set is `set(registers_b) - set(registers_a)` over the two **guard-on**
registers CSVs, which is the pair
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) §5 defines
the 155 over, so the two write-ups count the same set the same way. The guard-off
generation is deliberately not a third side; see §7.

## 2. The count, and the rule that makes it a count

```console
$ python3 ec/tools/xdata_page_clusters.py ... (as above)
page 0x0300-0x05FF
  old  e169a0e4: 430 rows, 109 on the page, 274 distinct page addresses
  new  committed: 439 rows, 116 on the page, 425 distinct page addresses
  page clusters: 109 -> 116 (+7)
  distinct page addresses are a union over the rows holding them, not a sum over rows: an address both programs touch is indexed under a main-ec row and a pd row, and summing would count it twice

  old: every cluster_id is one row, so nothing is keyed twice
  new: every cluster_id is one row, so nothing is keyed twice

```

**The 425 is a published figure and this reproduces it.**
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) §6 says "the
439-row pair's 425", and a set union reproduces it exactly. A naive sum over
per-cluster membership gives **427**, because `0x0300` is indexed under both
`main-ec-001` and `pd-004` and `0x04A3` under both `main-ec-130` and `pd-046`.
An address both programs touch is one address; the tool prints that rule on its
own output line rather than leaving two disagreeing numbers for a reader to
reconcile, and `--self-test` holds a fixture where the two differ.

Membership is counted over the `addrs` column and never over `addr_range`. The
`addr_range` column is a min-max span — `main-ec-043E`'s is `0x043E-0x300E` — so
counting over it would invent every address in between as a member.

## 3. Where the added addresses went, and the four that are not on the page

```console
  added addresses: 155
    on the page     151
    off the page      4  0x060E 0x060F 0x0646 0x0647
  page clusters the 151 on-page added address(es) landed in: 22
```

This reproduces §5's *"151 of the 155 are on that page and 4 are not"* from
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md), derived
here from the CSVs rather than quoted. The four off-page addresses land in two
clusters that **already held page addresses** — three each — so they joined
existing page clusters and changed no page membership. That is a distinction
worth keeping: it separates "the 151 spread across the page" from "four landed
somewhere new", and it is why the page's address count moves by exactly the 151
and not by 155.

The 151 landed in 22 page clusters, and the concentration is lopsided: one of
them took 84, and the next four took 12, 7, 4 and 4. The mode-oem-init cluster
`kefb63d82f8c7` is not among the 22 — **none of the added addresses landed in
the cluster the note is about.** The 84-holder and the 2-holder are two of the
clusters §4 names as mergers, which is what §5 turns on.

## 4. The correspondence, in both directions, and why one of them cannot be trusted to answer the question

The report prints the correspondence twice, and the duplication is the finding
rather than redundancy.

**Absorption** is the direction the note's sentence is about: how many earlier
page clusters each later one took in, scored by Jaccard membership overlap at
`CARRY_MIN_JACCARD = 0.50`, the threshold `xdata_register_map.py` carries a
name across a re-derivation at. It is matched within a program, because a
shared address number is not a shared byte.

```console
  absorption at CARRY_MIN_JACCARD 0.50 -- how many earlier page clusters each later one took in
    an n-into-one merge of equal-sized clusters scores 1/n per cluster, below the threshold at any setting; an unequal merge's dominant feeder scores max|Ai|/sum(|Aj|) against the feeders' union and can clear it, but this column scores it against the whole later cluster, so everything else that cluster holds dilutes it; a zero here is not evidence of no merge
```

**That column cannot be trusted to count a many-into-one merge, and the reason
is two different things rather than one, so both are given.** The `1/n` bound
is a statement about **equal-sized** merges: three equal disjoint clusters
merging into their union each score `1/3` against it, below 0.50 and below it
*at any threshold a carry rule could use*, because for an `n`-into-one merge of
equal-sized clusters the score is `1/n` however the threshold is set. An
**unequal** merge has no such bound — its dominant feeder scores
`max|Ai| / sum(|Aj|)` against the feeders' union, which rises towards 1.0 as
one feeder comes to dominate.

**What this pair shows is the second mechanism, not the first, and saying so
matters because the first one is the one usually quoted.** The nine feeders
`main-ec-001` took in are unequal — 25, 9, 5, 3, 2, 2, 1, 1 and 1 page
addresses — so their largest scores 25/49 = **0.5102** against the feeders'
union and *does* clear the threshold in principle. Absorption reports zero for
`main-ec-001` anyway, because this column scores each feeder against the whole
later cluster and `main-ec-001` holds **150** page addresses: the same feeder
scores 25/150 = **0.1667** there. The zero is dilution by the target's own
membership, not a structural bound. The three into `main-ec-019` are the equal
shape (2, 2 and 2 page addresses) and score `1/3` against their own union, but
that cluster holds 8 page addresses, so they are reported at 0.25 — the
dilution applies there too, on top of the bound.

So the report prints **feeding** as well, which carries no threshold: an earlier
page cluster is a feeder when at least one of its page addresses is in the
later one. Both directions are printed because a rule that can see some merges
and not others is not one that can be trusted to count them — not because this
column is blind to every merge.

Feeding is the weaker question and is labelled as such. One address landing in a
large cluster is not a merge of anything — a large cluster collects single
addresses by being large. That is why the report prints, beside every feeding
count, how much of each contributing cluster's page membership actually crossed
over.

```console
  verdict: 2 later page cluster(s) took in 3 or more earlier page clusters whole:
    ke794087e13a6 (main-ec-001) took in 9 whole: main-ec-004, main-ec-013, main-ec-035, main-ec-053, main-ec-133, main-ec-167, main-ec-203, main-ec-351, main-ec-352
    k462303ed5f86 (main-ec-019) took in 3 whole: main-ec-118, main-ec-164, main-ec-165
  count check: the page holds 109 cluster(s) before and 116 after, +7 net. A 3-into-one merge is one term in that net, not the whole of it -- splits move it the other way -- so neither the sign nor its size decides the verdict above
```

**Two things are true here and they point opposite ways, so both are stated.**

*The page's clusters were not conserved.* Two later page clusters took in
three or more earlier ones whole, and `k462303ed5f86` took in exactly three —
`main-ec-118`, `main-ec-164` and `main-ec-165`, each of which gave up its entire
page membership and none of whose keys survives in the near census. So **a
three-into-one merge of the page's clusters did happen.** The note's count of
three is not invented.

*The `+7` does not refute it and the tool does not claim that it does.* Merges
and splits happen in the same pass and a merge is one term in a net. The
feeding column above shows earlier page clusters whose addresses reach more
than one later one — the shape a split takes from here — so the net is positive
while merges occurred. How many of them there are is not printed and not
counted here: it is a figure no command in the tree produces, so this file does
not assert one. The count check is printed as a check on the correspondence, not
as a third verdict.

## 5. What the added addresses have to do with it, and the test that cannot answer it

This is the part that decides what the note's sentence gets to assert, and it is
also the part where the obvious test turns out to be worth nothing — which is
worth saying first, because an earlier draft of this file rested on it.

**The feeder intersection is zero by construction, not by measurement.** The
feeders are rows of the far-side census, the added set is `set(new) - set(old)`
over the two registers CSVs, and on the far side those two files draw their
addresses from the same set: the address union of `e169a0e4`'s
`xdata-clusters.csv` **is** the address set of its `xdata-registers.csv` —
1,171 each, empty symmetric difference. Every address a far-side row holds is
therefore outside the added set before any test runs, and the intersection is
zero for *any* pair of inputs, not for this one. The obvious check confirms it
and carries no information: the twelve whole feeders hold zero added addresses,
and so do all 430 far-side rows, which is the same zero reached more widely
rather than a stronger result.

**What is not zero is where the added addresses actually went, and it is the
opposite of "beside them".** Of the 151 on-page additions, **84 landed in
`ke794087e13a6`** — the cluster that took in nine earlier page clusters whole —
and **2 in `k462303ed5f86`**, the three-into-one merger itself. Both are rows of
§3's holders table. So the merged clusters are *not* made up entirely of
addresses that were in the census before the pass, and the added set is inside
both of them rather than next to them.

**So the note's "which" is left open, and that is what the correction rests
on.** *"The pass added 155 addresses across the same 0x03xx-0x05xx working
page, which merged three of the page's clusters into one"* asserts a causation,
and a causation is not something two clusterings record. The merge half is
confirmed — §4's three whole feeders, none of whose keys survives. The causal
half is neither borne out nor refuted here, because those same 84 and 2 read
alike whether the additions landed in clusters that were already there or
whether they helped make the clusters. An earlier draft of this file put the
weight on the feeder zero; that zero is a property of the input pair and the
§3 table says the opposite of what it was asked to say, so the correction is
made for the limit rather than against a result.

**What this does not show, because it is a limit of the inputs and not a
result.** The two censuses are clusterings, not co-reading matrices, so the
mechanism the "which" needs — whether the added addresses enlarged the clusters
that ended up holding them — is invisible to them. A merge into a cluster that
was already large, and a large cluster that grew afterwards, print the same
way from here. Nothing in this pair rules the added addresses in as the cause of
the re-partition and nothing in it rules them out, and the honest reading of
§4 is that the note's merge clause is right and its *"which"* is a question this
measurement does not answer.

## 6. Why no existing command settles it

The issue points at four. None of them counts a page's clusters, and saying so
by name is more useful than leaving the sentence standing:

- `xdata_register_map.py --threshold-sweep` prints per **program**, never per
  page, and the tool has no address-range flag at all. Its `addr_range` column
  is a min-max span and cannot be counted per page either.
- `xdata_register_map.py --map OLD_CSV` is the closest thing to a merge
  detector — it carries `added`, `removed` and a `jaccard` column and warns when
  *"a new cluster claimed by more than one old row"* — but it is the absorption
  column above, unfiltered by address, and §4 is why that column cannot be
  trusted to answer this question. It also prints no page count.
- `xdata_moved_ranks.py cause --page LO HI` takes `--page` but uses it only as a
  membership filter on rows it has already selected. No mode in that tool counts
  clusters on a page.
- `xdata_moved_ranks.py pair` compares **by rank, not by key**, so it answers a
  different question by construction.

So the tool is new, per the "a new tool is a new file" rule:
[`ec/tools/xdata_page_clusters.py`](../../ec/tools/xdata_page_clusters.py). It
reads CSVs by path, imports nothing from `xdata_register_map.py`, opens no
firmware and writes nothing. It restates `CARRY_MIN_JACCARD` rather than
importing it, and its self-test asserts the two constants are equal — a second
copy of a threshold that had silently drifted would make every absorption figure
here a different rule from the one the rest of the tree uses.

## 7. Out of scope, and named

- **The guard-off pair as a third side.** The note's 155 is defined over the two
  guard-on registers CSVs, so the comparison here is the two committed censuses.
  Measuring the guard-off generation too would be a different question.
- **Re-deriving or re-keying the `mode-oem-init` carry, or renaming anything.**
  The 0.84 is a Jaccard over a membership this file does not re-derive, and the
  note offers the merge as its reason for. §4 confirms a merge happened; whether
  the 0.84 is the score of a membership that came out of one is a question about
  that membership rather than about the page count, and answering it means
  re-deriving the carry — a census-level change, and a follow-up. Nothing in the
  CSV cell asserts either way.
- **`xdata_moved_ranks.py cause`'s hard-coded `of 155` header**, whose cell is
  the row's actual added count. Correct for §5's pair, wrong for any other, and
  it is a shared tool with open work against it.
- **Any live run.** No hardware, no Windows, no image opened.

## 8. The test that proves it

`--self-test` is over a fourth pair of censuses, chosen so each case can go red:
three equal page clusters merged into their union (which the carry rule cannot
see and the whole-feeder count can), five earlier clusters each contributing
one of three addresses to a large later one (which is a large cluster
collecting addresses, not a merge), an address both programs touch, a cluster
straddling both ends of the page, a page neither census touches, an added set
entirely off the page, a pair of identically-shaped rows in different programs,
a `cluster_id` held by two rows, and a census path that is not there.

```console
$ python3 ec/tools/xdata_page_clusters.py --self-test
xdata_page_clusters.py --self-test
  ok    three equal page clusters merged into their union are three feeders and no absorption: the 0.50 carry rule scores each of them 1/3 and cannot see the merge, which is why the report prints both directions
  ok    the verdict line is answered by the threshold-free whole-feeder count, so a merge the carry rule cannot see is still reported as one
  ok    the absorption column states on its own line that the 1/n bound is for equal-sized merges, that an unequal merge's dominant feeder can clear the threshold, and that this column scores against the whole later cluster, so its zero is not read as evidence of no merge
  ok    an address both programs touch is one page address: the union is the set, and summing per-row membership would count it twice
  ok    the report prints the union rule beside the number, and prints the union rather than the sum
  ok    a page neither census touches is named on its own line, so its zeros read as an empty page rather than as a measurement
  ok    an added set that is entirely off the page is reported as off the page with nothing to attribute, rather than as a confident zero on-page
  ok    a correspondence is matched within a program: a main-ec row and a pd row of identical membership do not match each other, because a shared address number is not a shared byte
  ok    a later cluster fed by more than MERGE_CLAIM earlier ones is counted as fed, with how much of each feeder crossed, so the count is a fact about membership rather than a verdict
  ok    five earlier clusters each contributing one of three addresses to a large later cluster is reported as that large cluster collecting addresses, not as a merge of the page's clusters: only a whole feeder counts toward the merge verdict
  ok    the page is an inclusive address range and the report counts what is inside it: 0x02FF and 0x0600 are outside 0x0300-0x05FF and inside 0x0200-0x06FF, so the same cluster counts differently per run
  ok    with no --page the range is 0x0300-0x05FF, the working page annotations/xdata-cluster-names.csv records, rather than the whole address space
  ok    the union is a set union of the per-row page memberships, so the rule the count rests on is the one the code implements
  ok    the carry threshold restated here is the one xdata_register_map.py uses (0.50), so an absorption figure here is the same rule as a --map figure and not a second rule that has drifted
  ok    a cluster_id held by two rows is named, because the report's tables are keyed by it and would otherwise count one page cluster where the census has two
  ok    the same line is printed when there is no collision, so a clean run reports having looked rather than staying silent about it
  ok    a census path that is not there is named with how to reach the far side, rather than surfacing as a traceback from open()
  all checks passed
```

**No check here pins a census figure.** The counts in §2–§5 are a transcript of
a command over committed CSVs, re-derivable by running it, and asserting any of
them here would make a value every merge to this tree has to edit. The checks
hold properties of a fixture pair instead.

**Four mutations were tried against the fixtures** and each turned two or four
checks red: flattening the per-program restriction (2), counting page addresses
by sum instead of union (4), widening the page to the whole address space (2),
and emptying the added set (2). The third of those was red-zero on the first
attempt — every fixture passed `--page` explicitly, so the default was
unreachable from the self-test — and the page-bounds and default-page checks
above are what it bought.

The known-answer run is §1 through §5. The rest of the tree's checks, none of
which this change moves:

```console
$ python3 ec/tools/xdata_register_map.py --check
  ... 1326 register rows, 439 cluster rows, both exit 0 ...
$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
  ... OK
$ python3 ec/tools/check_cluster_citations.py
  ... every checked cluster citation resolves, and every hand-typed census count agrees ...
$ python3 ec/tools/gen_findings_index.py --check
$ python3 ec/tools/check_findings_frozen.py
$ git status --porcelain
```

**This change adds no `test_*.py` and so no row to `tools/README.md`'s table**,
which is why that shared file is not touched either. The tool's own
`--self-test` is the house pattern for a measurement tool, as
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) §9 puts it.
The tool is **not** in `.github/scripts/agent-gates.sh`'s `--self-test` list and
cannot be added by this branch: the pipeline's push token has no `workflow`
scope, so a change under `.github/` fails at the end of the run rather than the
start. It belongs in that file's loop beside `xdata_moved_ranks.py`'s, and a
human adds it.

**This file is written to `check_cluster_citations.py`'s rules**, the same
constraint that shaped
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) §9: the
checker resolves ids, keys and names against the **committed** census only, so a
sentence pairing a 4-hex address with a cluster key is held to today's
membership. Every far-side row here is therefore identified by `cluster_key` in
the first cell with counts only — no addresses, no names — and the verdict names
no rank against an address.
