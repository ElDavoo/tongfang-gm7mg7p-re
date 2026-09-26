# The `--swept` summary's second-holder count was taken over one generation, and the rows were over both (issue #886)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over files: the self-test over synthetic censuses in a
`tempfile`, and §5's re-derivation over two committed censuses and two
regenerations of committed trees, with every scratch output under `/tmp` and
`git status --porcelain` printing nothing but this branch afterwards. Same
framing as [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):3.

This is a correction to the tool [`ec/tools/xdata_moved_ranks.py`](../../ec/tools/xdata_moved_ranks.py)
#852 added — a bookkeeping defect in one summary line, and nothing in that
write-up's measurement.

## 1. The defect, quoted

`swept_report()` builds each address's rows from the **union** of the two
generations' holder indexes — `index_a` first, then any `index_b` key not
already held:

```python
held = index_a.get(addr, [])
rows = [(k, a[k], b.get(k)) for k in held]
rows += [(k, None, b[k]) for k in index_b.get(addr, []) if k not in held]
```

and the summary line's second-holder count read **one** of them, with `or`
making that a silent choice:

```python
second = sum(1 for addr in addrs
             if len(index_b.get(addr) or index_a.get(addr)) > 1)
```

`index_b.get(addr) or index_a.get(addr)` falls through to A only when B's list
is empty or missing, so the count can only ever be **B's** count. An address
that generation A holds twice and generation B holds once therefore prints two
rows above the summary and counts as one. The two expressions are quoted here
rather than at a line number because this change moves the lines, in the same
commit that would make the pin stale.

**The other numbers on that summary line are union-based and were already
right.** `keys` is accumulated from the rows inside the loop, so
`len(keys) - len(pd_keys)` counts `main-ec` holders across both generations
while `second` did not. One line, one number wrong.

## 2. The disagreement is one-directional, which is why the fixture shape is forced

The defect needs `|B holders| <= 1 < |A ∪ B|`. The **reverse** asymmetry —
generation A holding the address once and B twice — is invisible to it, and
measured on the fixtures both ways:

| A holds | B holds | rows printed | `second` before | `second` after |
|---|---|---|---|---|
| twice | once | 2 | **0** | 1 |
| once | twice | 2 | 1 | 1 |

`or` reads B's two-element list in the table's second case and gets it right.
So the fixture that can go red is a census pair where generation A holds one
address under a `main-ec` and a `pd` key and generation B under the `main-ec`
key alone — not a case chosen for tidiness but the only shape the bug reads.

## 3. The fix, and why it is derived from the rows

The set union spelled out in the issue is equivalent and was available:

```python
len(set(index_a.get(addr, [])) | set(index_b.get(addr, []))) > 1
```

Keys are unique within a census (`test_xdata_cluster_names.py::TheContentKey`
holds that), so that is exactly `len(rows)` for the address. What was taken
instead is the form that leaves **one** definition of "the rows for this
address": the loop appends each address's `rows` to a list as it makes them,
and the summary counts the entries with more than one row. A count computed a
second time from the indexes is the shape the bug was — two places that know
how the rows are built, free to drift apart — so removing the second place is
worth the two lines.

It is a **list**, not a `{addr: rows}` map, because the loop is over
`sorted(addrs)`: an address passed twice is printed twice and is counted once
per visit, where a map keyed on the address would collapse that to one. On the
shape the committed pair actually has — the address held twice by both
generations — `--swept 0x0E 0x0E` prints **4 rows and reads `2` before and
after**, so that edge is not moved by this change. The only case where the
figure moves is the §2 shape, which is the defect: 4 rows, `0` before, `2`
after.

The docstring says so in one sentence: the count is over the rows the loop
makes, "the union of both generations' holders", so the summary cannot
disagree with the rows above it. The claim the docstring already made — "the
second row per address is not noise, and the summary counts the `pd` holders
separately" — is now true by construction rather than incidentally.

## 4. The fixture, and that it can go red

A **dedicated third census pair** in `self_test()`, three rows in total,
reached through a direct `flip_table()` call — the function `across_report()`
itself calls — so no new `across` run and no new table shape. Each census is
passed as its own guard-off, so nothing moves and every row reads `intact in
both`: the flip table is not what this check is about.

**The A/B pair above it cannot be the fixture.** Its `0x0E` is held by
`k000000000001` and `k000000000008` in *both* generations, so `index_a` and
`index_b` both have two entries and `or` picks either without consequence —
and no existing check reads the `second` figure at all, so nothing about that
pair can go red by itself. Measured: moving the B fixture's guard-off `pd` row
to a different address leaves all 15 checks green. Re-measured twice on the
merged tree, where the self-test was then 34 checks (see §4's merged-tree note),
the
same mutation is still green against all 34. *(The self-test is 39 on the tree
this now sits in; the mutation result is left as the record of the run that
produced it rather than re-run here, because the fixture it moves is named in a
sibling's merged-tree note and not in this one, and a re-measurement of a
mutation this section does not restate would be a second claim rather than a
correction.)*

The issue's own alternative — give the B generation's `pd` row a different
address — is real, but it is more than a one-cell edit, and the write-up above
first said otherwise. `b_committed` is written from `committed_rows`, the same
list object generation A is written from, so B's `pd` row cannot move without
generation A's moving with it; the row has to be un-shared first. With that
done and a new `second`-reading check pointed at the A/B sweep, the pair does go
red — 2 rows above a summary reading `0` — and the fix turns it green, as
measured. A dedicated pair buys that same red state with **no existing line of
the self-test changed** and nothing to correct in #852's 577-line write-up,
whose §9 transcript at
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):622 prints the
existing check text verbatim.

The check is written as the invariant rather than as a number: it groups the
report's rows by address, reads the figure back **out of the tool's own summary
line** rather than recomputing it beside the output, and requires the two
equal. The concrete `2` rows and `1` second holder are asserted in the same
check, so a loosening that made both sides vacuous still fails.

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test
  ...
  ok    an address both programs touch is reported once per committed cluster holding it, not once
  ok    a cluster that flipped is labelled FLIPPED, one that did not is not, and the summary counts the `pd` holders separately
  ok    the second-holder count is over both generations' holders, so it equals the number of addresses that printed more than one row: 2 rows for 1 address, counted once
  ok    whether the two generations perturb the same addresses is reported on its own, not inferred from two matching counts
  ok    two runs can agree on a count and disagree on which addresses, and an address a re-derivation adds can be outside the guard's reach entirely
  all checks passed
```

15 checks, where there were 14, and the other 14 print verbatim. The fixture
report itself, over the same pair, with the old `second` line and the new one:

> **Merged-tree note (2026-09-26, issue #884).** The counts above — 14 before,
> 15 after — are what this write-up's own change made of the self-test, and they
> are left as the record of the run that produced them, for the reason the
> `xdata-moved-ranks-fall.md is not edited` bullet below gives. On the merged
> tree the tool prints **39** checks, and the 25 this note first recorded is
> where it stood after one of the two merges beside it: #884's `cause` mode
> ([`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md)) added ten
> of its own to the same fixture block, and they print after check 20, so the
> console block above, which used to be the run's tail, is not any more. #891
> then added nine more after those — the rank-shift block of
> [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §9, whose own §9
> transcript is re-recorded at 39 — and #889 added five more
> ([`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md)),
> which print at 10–14, between the two halves of the first fifteen rather than
> after anything, so `25 + 9 + 5 = 39` is the whole story and the tail is
> unchanged at those 19 lines and `all checks passed`. *(The 34 this note first recorded is the
> same tool without #889's five beside it; the count is re-run on the merged
> tool rather than carried over, and 39 is what it prints.)* **The check this
> section is about is unchanged and still
> passes**, printed verbatim as it reads
> above: it is the 18th `ok` of the 39, and the 14 lines this change left alone
> print in the same order as they did — 12 of them ahead of it and 21 after (2
> of the original 15, then the 19 the two later blocks added), with #889's five
> interleaved ahead of it and changing neither its position within the first
> fifteen nor its text. The
> block above is the last two of the first group, this check, and those last
> two. §63's summary in [`../findings.md`](../findings.md)
> carries the same note. Nothing else here moves because of either merge: #884
> adds a mode, and #891 adds two rank columns and a `--cell` to `across`'s
> per-key table, and **neither touches `swept_report()`** — it is byte-identical
> across the base commit, `main` and the merged tree, which is the function this
> section is about.

```console
=== the old `second` line, over the new fixture ===
  swept addresses: 1
  address  cluster_key    program  rank A       rank B       verdict
  0x0E     k000000000001  main-ec  main-ec-001  main-ec-002  intact in both
  0x0E     k000000000002  pd       pd-001       -            intact in both
  2 committed cluster(s) hold at least one of the 1: 1 main-ec, 1 pd; 2 hold all of them; 0 address(es) have a second holder
  of those 2, 0 flipped; 0 moved in A and 0 moved in B

=== the new `second` line, over the new fixture ===
  swept addresses: 1
  address  cluster_key    program  rank A       rank B       verdict
  0x0E     k000000000001  main-ec  main-ec-001  main-ec-002  intact in both
  0x0E     k000000000002  pd       pd-001       -            intact in both
  2 committed cluster(s) hold at least one of the 1: 1 main-ec, 1 pd; 2 hold all of them; 1 address(es) have a second holder
  of those 2, 0 flipped; 0 moved in A and 0 moved in B
```

**Two rows above a summary that reads `0`.** The red state was reproduced by
restoring the one `second` line into a copy of the tool with the fixture in
place, and the check reads:

```console
  FAIL  the second-holder count is over both generations' holders, so it equals the number of addresses that printed more than one row: 2 rows for 1 address, counted once
  ...
  FAILED (1)
```

## 5. The committed pair, re-derived: the figure does not move

This is the point that has to be measured rather than presumed, and §7 of
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):490 is the recipe —
`git worktree add --detach /tmp/xdata-old e169a0e4a736956f35af5ffff65e997154c76bdd`,
two `xdata_register_map.py --no-eq-guard --out-clusters/--out-registers` runs
(one in the worktree, one in this tree), then the `across --swept` command over
the 43 addresses. Run once with the old `second` line and once with the new
one, on the same re-derived censuses:

**48 rows for 43 addresses, and `5 address(es) have a second holder` both
times** — `diff` over the two 86-line reports is empty. The committed line is
byte-for-byte the one at [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):567,
because on this pair the two `pd` holders, `kedee1182bba5` (`pd-002`) and
`ke928434f6676` (`pd-033`), are present in **both** generations, so B's count
and the union's are the same five. This is a latent disagreement, not an
observed wrong figure, and it is now a figure that cannot go wrong.

*(The two citing lines above were `:458` and `:535`, and this file's four have
now been repointed twice: to `:469` and `:546` at the #888 × #891 merge, and to
the merged tree's `:490` and `:567` here. The same treatment #889's and #891's
insertions into that file got, and for the same reason — #888 added two
`cluster_key unique …` lines and a nine-line note to the fall file's §1–§2
blocks, so everything below them moved down eleven, and #890 had already moved
them before that. **All four of this file's citing lines that moved are moved**
— `:564` → **`:596`** at `:289` and `:590` → **`:622`** at `:128` — while `:3`
at `:9` is still above every insertion any of those merges makes and has never
moved. Each of the four was re-opened against the merged file and still names
what its sentence names: the §7 heading, the `across --swept` console line, the
"No gate is wired" bullet and the second-holder check line respectively. That is
a citing line rather than a pin, which is why no tool in this tree can catch the
drift: the point
[`test-line-pin-census.md`](test-line-pin-census.md)'s merged-tree note makes
about its own table.*

`git worktree remove /tmp/xdata-old` afterwards; `git status --porcelain`
printed nothing but this change's own three files.

## 6. The two sibling `or` reads, examined and left

The same summary line reads `b.get(k) or a[k]` twice more, at the `pd_keys`
and `complete` figures. **These are not the same defect, and they are left
alone deliberately** rather than tidied:

- `cluster_key` is a content hash over the program and the sorted membership
  (`xdata_register_map.py`), so a key carried by both censuses has the same
  membership and the same `program` in either — which is why `keyed_by()`'s and
  `flip_table()`'s own docstrings already lean on it, and why
  `across_report()` prints `shared keys whose committed membership differs
  between the two censuses: 0 … by construction and is printed rather than
  assumed`.
- So there is no disagreement there to fix. Rewriting them would be a claim the
  content-hash property does not support.

They are named here so the next reader knows the line was read end to end and
the two reads were a decision rather than a miss.

## 7. What this does not do

- **No firmware claim, and no live run.** Both censuses are files, no image is
  opened, no register is read back, no EC, laptop or Windows machine is
  involved. §5's recipe is a worktree plus two CSV writes into `/tmp`.
- **No CSV, YAML, threshold or `status:` moves.** `xdata-clusters.csv`,
  `xdata-registers.csv`, `xdata-cluster-names.csv`, `registers.yaml` and
  `ec/ghidra/xdata-symbols.csv` are byte-untouched. The re-derivation's census
  runs wrote only to `/tmp` — the tool refuses the committed output paths in
  any case — and `xdata_register_map.py` is not touched at all.
- **The `> 300` floor does not move**, and no guard-off threshold does. Nothing
  here touches the measurement
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) is about.
- **No `test_*.py` is added**, so `tools/README.md`'s suite table gains no row
  and the runner's totals are unmoved **by this change**: **34 suites / 1033
  tests** on the tree it merged into, and **35 / 1076** on the tree it lands on,
  the additions being #887's `ec/tools/test_census_test_line_pins.py` at 41 and
  #850's two cases in `ec/tools/test_xdata_cluster_names.py` —
  `1035 + 41 = 1076`. The first is the arithmetic its seventh merged-tree note
  closes over and the second is what `tools/README.md`'s ninth carries. *(The
  `1033 + 41 = 1074` this first recorded is the tree before #850's two cases
  were beside it, and is left visible here rather than edited out.)* The new
  self-test lives inside the tool, as `xdata_register_map.py`'s and
  `grade_0751_isolation.py`'s do.
- **No gate is wired**, for the reasons
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):596 gives: the tool
  is a read-only investigation aid and adding two census runs to every push
  would cost more than the gate gets. `CLAUDE.md` separately says
  `agent-gates.sh` is a copy from the `agent-pipeline` template this repository
  should not edit casually. The self-test is the tool's own, run by hand.
- **Nothing is opened in another repository.** There is no upstream deliverable
  in this change to send to `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers`.
- **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) is not edited.**
  Its §9 transcript is 14 `ok` lines and the tool now prints 15; that file is
  left reading as the record of the run that produced it, which is the pattern
  `docs/findings.md` §62's numbering note and the merged-tree notes in
  `tools/README.md` both use. The 15-line transcript is in §4 above.
- **The duplicate-address edge** (`--swept 0x0E 0x0E`) is not moved: on the
  shape the committed pair has, 4 rows and `2` before and after. §3 says why
  the fix was written to leave it alone.
