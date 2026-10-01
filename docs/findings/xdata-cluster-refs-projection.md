# A cluster's `refs` is the sum of its members' `refs_<program>`, and not of their `refs` (issue #343)

**Issue #343, 2026-10-01.** `ec/annotations/xdata-clusters.csv` and
`ec/annotations/xdata-registers.csv` sit next to each other and both have a
column called `refs`, and they are not the same quantity. Neither the tool's
header nor the map page's tables said so, and the census's own prose reads as
though the clusters file were a projection of the registers file column for
column. It is a projection, but a **per-program** one.

This is a report about two files that already exist. No register `status:`
moved, no CSV was regenerated or edited, `registers.yaml` and
`ec/ghidra/xdata-symbols.csv` were not involved, and nothing here needed a live
run: every figure below re-derives from the two committed CSVs and the tool's
own source. The sibling page,
[`xdata-per-program-counts.md`](xdata-per-program-counts.md), is the one that
put the columns this page reads on the registers side.

## What the two `refs` columns are

`ec/annotations/xdata-registers.csv`'s `refs` (column 6) is one address's whole
reference count. On a `program=both` row that is the **sum** over the two
programs — which is what #713 kept it as, deliberately, so a reader who reads
the unsuffixed column still gets the census. The twelve columns #713 appended
at 22–33 split it, and `refs_main_ec` / `refs_pd` are the two halves.

`ec/annotations/xdata-clusters.csv`'s `refs` is **neither of those sums**. It is
the sum of its members' *`refs_<cluster's own program>`*:

```python
refs = sum(group[a]["refs"] for a in members)
```

in `xdata_register_map.py`'s `cluster_rows_build()`, where `group` is the
**per-program** group — `group` is `groups[g]` for the cluster's program `g`, and
an address in `groups["main-ec"]` carries only the references the main EC image
makes. So a `both` address inside a `main-ec` cluster contributes only its
main-EC half, and the pd half of that same address lands in whichever pd cluster
holds it, if any.

**So a cluster's `refs` cannot be added up out of the registers CSV's `refs`
column, and the reason it looks like it can is that the two halves sum back to
the same total** — §"The oracle that could not see it" below is about that.

The definition is now written down where both CSVs' columns are introduced: one
sentence under `xdata-register-map.md` §5's cluster table, one in §4.2, where
the clustering and the clusters CSV's rows are described, and one in an
end-of-file note in `xdata_register_map.py` — there rather than in the module
docstring for the reason the next paragraph gives. Each carries no figure,
because §5's figures move with the census and a number in a moving file is a
merge conflict with extra steps.

**The tool's note is at the end of the file rather than in the module docstring,
and that placement is the tool's own rule rather than a preference.**
`check_eq_guard_citations.py` resolves its anchors inside
`xdata_register_map.py`, and every one of them lands above the note that sits at
the end of that file — so a paragraph inserted in the module docstring shifts the
whole set at once, and turns a one-sentence addition into an edit to every
document holding one of them. `docs/findings.md` is one of those documents and
is frozen. How large the set is today is the tool's to report, not this
write-up's to carry: `python3 ec/tools/check_eq_guard_citations.py` ends with the
citations it resolved and the files they are in, and the number belongs to that
line, because the next citation added moves it. The tool's own end-of-file note
makes the same argument about itself, and keeps its count there too rather than
in a document that would have to be edited with it: *"a paragraph inserted in
the ORACLE comment block shifts all ... this is the pin saying why, placed where
saying it costs nothing."* Re-pinning them instead was
the alternative, and CLAUDE.md's rule on citing by name rather than by line
number is what that runs into: the pins are a hand-kept set of numbers spread
across shared files, which is the shape this repository has already had to
retract from more than one document. So the note moved rather than the pins.

## The measurement, on the committed tree

**`refs == Σ over members of refs_<program>` holds on every committed cluster
row.** Re-derived from the two CSVs and nothing else:

```console
$ python3 ec/tools/check_cluster_refs_projection.py
439 cluster(s) recomputed: every cluster's `refs` is the sum of its members' `refs_<program>` in ec/annotations/xdata-registers.csv -- the per-program share, not the unsuffixed `refs` -- and `size`, `addr_range` and membership agree with it
```

The check reads the **named** input — `refs_main_ec` / `refs_pd`, columns 22
and 23 — and not a freshly generated census. That is the whole of what the
issue's "Done" asks for, and it is worth being explicit about why it has to be
that: a check that re-ran `xdata_register_map.py` could only ever compare the
census with itself. The fresh generation and the committed CSV would agree by
construction, and a change to the apportionment would move both together and be
caught by nothing.

The three invariants the issue measured as intact hold too, and are asserted
beside the rule so a change that breaks one is caught next to the change that
broke it rather than rediscovered later as a mystery:

| | measured on the committed tree |
|---|---|
| `size == len(addrs)` | every row |
| `addr_range == min-max(addrs)` | every row; bare when `min == max`, which is how the 225 single-address clusters are written — a rule, not a discrepancy |
| every member present in the registers CSV | every member, and no non-`both` member's `program` differs from its cluster's |
| `refs == Σ members' refs_<program>` | every row |

**`refs` is the one counted column this comparison cannot reproduce**:
`size`, `addr_range` and membership all fall out of `addrs` and the two
per-program columns, and this one does not — which is what made the other three
worth asserting, as the counter-examples that make this one the exception rather
than the rule. What makes it more than a fifth instance of the same thing is
that the registers CSV carries a column of the same name, so `refs` reads as
reproducible from the file beside it and is not. The columns built from the call
graph and the symbol table rather than from either CSV — `functions_touched`,
`shared_functions`, `callees`, `named_addrs`, `co_reading`, `co_reading_refs` —
are outside the comparison, which is why it is stated over `addrs` and the two
per-program columns rather than over the registers CSV alone.

## The oracle that could not see it

`xdata_register_map.py --self-test` already asserts that *"the clusters CSV is
a projection of the registers CSV, not a separate count"*, and its predicate is:

```python
check("the clusters CSV is a projection of the registers CSV, not a "
      "separate count",
      sum(int(r["refs"]) for r in cluster_rows) == total_refs)
```

**One number for the whole file.** It holds on the committed tree, and it would
hold just as well if every cluster's `refs` were the raw sum of its members'
`refs` — because the `both` split sums back to the same total:

```console
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{s+=$6} END{print "registers `refs`", s}'
registers `refs` 15696
$ tail -n +2 ec/annotations/xdata-clusters.csv | awk -F, '{s+=$4} END{print "clusters `refs`", s}'
clusters `refs` 15696
$ tail -n +2 ec/annotations/xdata-registers.csv | awk -F, '{m+=$22;p+=$23} END{print "the two per-program halves", m, "+", p}'
the two per-program halves 14838 + 858
```

15696 = 15696 = 14838 + 858. **The identity cannot distinguish a per-program
projection from a raw one, and it says nothing about any individual cluster** —
a cluster that over-counted by exactly what its neighbour under-counted would
leave it untouched. So the census's prose was reading as a stronger guarantee
than anything asserted, and the new check asserts the stronger claim while
keeping the total as the weaker one it is.

`check_cluster_refs_projection.py` reproduces that limit in its own suite, in
`TheCorpusTotalCannotTell`: one cluster's `refs` is moved up by one and
another's down by one, the corpus total still agrees, and the check is still
red. That is what the total cannot do, shown rather than argued.

## The issue's figures, and how they have moved

**The shape of the finding reproduces exactly; the numerals have moved with the
census.** The issue's numbers were measured against an earlier tree, and a
write-up that copied them would be asserting figures about this tree that it
does not have. Recorded as a measurement in time, not as a correction of a
living claim:

| | issue #343 says | committed tree |
|---|---:|---:|
| clusters | 427 (377 main-ec / 50 pd) | **439** (389 main-ec / 50 pd) |
| clusters where `refs` ≠ Σ members' `refs` | 55 (29 / 26) | **58** (31 / 27) |
| `both` register rows | 48, 1,093 refs | **49**, 1,202 refs |
| both CSVs' `refs` total | 14,792 | **15,696** |
| `main-ec-001` refs | 1,136 | **873** |

Same offenders, same shape, and the gap is the same fixed per-member cost: a
`both` member's count minus its own program's share. The `pd-002` row is the
sharpest instance on the committed tree, and it is the one §5 mentions:

| cluster | `refs` | Σ members' `refs` | Σ members' `refs_<program>` |
|---|---:|---:|---:|
| `pd-002` (size 20, `0x07F3`-`0x080C`) | 54 | 527 | **54** |
| `pd-033` (size 1, `0x080D`) | 8 | 137 | **8** |
| `pd-049` (size 1, `0x0852`) | 1 | 17 | **1** |
| `main-ec-002` (size 92) | 1,130 | 1,207 | **1,130** |
| `main-ec-001` (size 152) | 873 | 875 | 873 |

The right-hand column is the point: it equals the cluster's own `refs` on every
row, which is what "per-program share" means and what the check asserts. The
middle column is the number a reader gets from the obvious arithmetic, and it is
dominated by the `both` members — invisible on a large cluster, everything on a
singleton.

**`xdata-register-map.md` §5's `pd-002` sentence is deliberately not
edited.** It states a size and a range — "`pd-002` (20, `0x07F3`-`0x080C`)" —
and no reference figure, so nothing in it is wrong today and there is no
number there for the definition to contradict. Its silence is not an oversight,
and it is recorded here so a later reader does not read it as one.

## The check, and where it runs

`ec/tools/check_cluster_refs_projection.py` reads the two committed CSVs and
exits 0 or 1. Offline: no image, no decompile, no Ghidra, no census pass, two
file reads. `--clusters` and `--registers` point it at another pair, which is
what lets the suite hand it a scratch copy of the committed one with one edit on
it.

**The rule is one line over two files, and a one-line rule is the shape that
cannot tell whether it can fire** — so `ec/tools/test_cluster_refs_projection.py`
is mostly refusals, each built by editing one cell of a `tempfile` copy of the
committed pair rather than by constructing a census from scratch. Three of them
carry the claim:

* **A `both` row's split moved between its two halves, with its `refs`
  untouched.** This is the case that decides whether the check reads the
  per-program columns or the unsuffixed `refs`. It asserts the refusal is
  confined to *exactly* the clusters holding that address — the equality, not
  `assertTrue`, is what discriminates, because a check summing the unsuffixed
  column is red on the committed tree already (58 clusters disagree with a raw
  sum) and would satisfy a weaker assertion for the wrong reason.
* **One cluster's `program` flipped**, so that a rule keyed on nothing cannot
  satisfy it.
* **A balanced move**: one cluster up by one, another down by one, the corpus
  total still agreeing. §"The oracle that could not see it", run.

Both properties were confirmed by mutating the check rather than by reading it:
an implementation that summed the unsuffixed `refs`, and one that always read
`refs_main_ec` whatever the cluster's `program`, are each caught by three of the
suite's cases.

**Discovered by `bash tools/run-tests.sh`, not by a gate line.**
`.github/scripts/agent-gates.sh` is copied from the `agent-pipeline` template
and this branch's token has no `workflow` scope, so a gate line is an upstream
change plus a re-copy — `docs/agent-pipeline.md` records that, and the runner's
own header says so. Every other check in this repository reaches CI that way,
and so does this one.

## What is left on the table, and why

The issue offered two honest resolutions and **this takes the first: keep the
apportionment, and say plainly that a cluster's `refs` is per-program and is not
the sum of the registers CSV's.** The second — putting the program split into
the clusters CSV — is now known to be cheap in derivation and expensive in
blast radius, and that asymmetry is worth writing down:

* **Deriving it is free.** The split is already committed as `refs_main_ec` /
  `refs_pd` on the registers side. Nothing has to be counted twice.
* **Landing it is not.** `xdata-clusters.csv` is generated, so a new column
  means changing `CLUSTER_COLUMNS` and `build()` in `xdata_register_map.py` and
  regenerating the committed clusters CSV — and every consumer reads that file
  *by column name*, so each one is a reader to update rather than a row to
  re-derive:
  `check_cluster_citations.py`, `cluster_name_shape.py`,
  `test_xdata_cluster_names.py`, and `xdata_register_map.py`'s own `--check` and
  `--map`. `check_cluster_refs_projection.py` prints the population it
  recomputed, which is where that count is read from.
* **A reader who wants the other program's share today gets it in one
  `cut -d, -f22-33` on the registers CSV.**

So the deferral costs a sentence rather than a schema change, and the enabling
measurement is the table above: the per-program column that reproduces a
cluster's `refs` exactly is already in the tree.

**Also out of scope, with the reason.** Editing `check_cluster_citations.py`: it
carries the count rule this issue is about and #292's work is open against the
same tree, so a second PR in that file is a guaranteed conflict — the new
assertion is a separate file reading the same two CSVs. Widening `--self-test`'s
oracle from corpus-total to per-cluster: it belongs with whoever owns #292, and
the new checker asserts the stronger claim today, so nothing is unheld in the
meantime. Changing either CSV in any way, including regenerating them.

## What the shared-file edits cost, measured

Two of this change's three edits are into files other branches also touch, and
both moved committed line numbers. Recording what moved, because the sentence
that follows each is short and the number underneath it is not:

* **The two `xdata-register-map.md` sentences push two citing lines down**, and
  `check_pin_table_rows.py` is red until `docs/findings/test-line-pin-census.md`
  re-registers them. Both rows are re-registered in this change, with the
  re-anchor chain each already carried extended by one step — the same shape
  #1425's is in, for the same reason: an insertion above a cited line is a move
  and not an edit, and the cited text is byte-identical at every step.
* **`xdata_register_map.py` cannot take a docstring paragraph at all**, which is
  §"The definition is now written down…" above. This is the more expensive of
  the two and the reason the note is where it is: every anchor that tool
  resolves in that file sits above the note, and one of the files holding those
  citations is the frozen `docs/findings.md`.

Neither is a reason not to make the edits — they are one sentence each, at a
named anchor, in a change whose subject is exactly these columns — but both are
a merge conflict waiting to happen, which is why this write-up exists as its own
file rather than as a section appended to anything shared.