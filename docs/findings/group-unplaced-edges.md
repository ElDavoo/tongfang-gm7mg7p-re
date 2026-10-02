# The third decision the call-graph walk makes, and the edges it could not place (issue #488)

`group_functions.py --report` prints the A/B/C call-edge census and then the
population the banking rule discarded, and no two of those lines added back to
the census. The missing remainder is the third thing `cluster()` does with an
edge: **leave it unplaced**, because the target address has no annotated row
for the caller to be joined or proxied onto. It is counted here and in
`--report`.

This is a reporting change. **No join logic changed, no group moved, `--check`
and `cross_bank_groups` are untouched, and neither `function-groups.csv` was
regenerated** — the same scope discipline
[`group-proxy-populations.md`](group-proxy-populations.md) declared.

---

## The problem, stated precisely

`cluster()`'s walk makes one of **three** decisions per edge, and until now
only the second had a line in the report:

1. **joined** — the target has a row in the caller's own scope, so the union
   takes it as an endpoint. Counted nowhere in the report, because it is the
   population that was expected.
2. **proxied** — the target has a `common` row and the caller is a bank, so the
   endpoint is that bank's proxy node. Reported as
   `bank->common edges cut by the per-bank proxy rule`.
3. **unplaced** — the target has neither. There is nothing to join the edge onto
   and nothing to proxy it onto either, so the edge ends at nothing. In no
   figure, anywhere.

The third is not a remainder of some other printed number. It is a term of the
same partition, and the partition **closes against `bucket_populations()`**
exactly, on every run:

```
    every edge in that census ended one of those four ways: 2962 joined + 124 proxied + 202 unplaced + 85 cut by the split mode = 3373. The cross-region count below is not a fifth term: it is counted before the join decision, so it covers some of the joined edges and some of the unplaced ones rather than adding to either.
```

**Four terms, not three, and the fourth is this tool's own edit.**
`bucket_populations()` reads every committed listing, while the clustering walk
`continue`s past a shape-matched bank-select trampoline before reading that
row's targets — so those edges are in the census and in none of the three
decisions. They are reported separately already, as `trampoline_edges`, because
attributing this tool's own edit to the banking rule is the conflation
`proxy_edges` was split out of `cross_region` to stop, one edit later.

**`cross_region` is deliberately not a term.** It is counted *before* the join
decision, so it covers some edges that were joined as well as some that were
not. Adding it to the four would count some of them twice. That is the same
reason the other-bank sub-population below is printed as an **overlap** rather
than as an extra addend.

---

## The two ways an edge lands unplaced

The split is by the branch that fell through, not by what the issue could have
named, and the difference is not cosmetic — see the `0x2A6C` note below.

| branch | condition | edges | distinct targets |
|---|---|---|---|
| below the bank base | no row in the caller's own scope, and none in `common` | 128 | 103 |
| at or above the bank base | no row in the caller's own scope, and none in the other bank | 72 | 59 |
| at or above the bank base | no row in the caller's own scope; the **other bank** has one | 2 | 1 |
| | **total** | **202** | **163** |

By caller scope: `bank0=50, bank1=42, common=62, pd=48`. Those four add to the
202, and the three rows add to the 202 as well — the caller scope says who
could not place the edge and the branch says what was missing, and neither is a
subtotal of the other.

**The third row overlaps `cross_region` and the first two do not.** Both of
those edges are bank-base edges whose target exists in the other bank, and
`cross_region` counts a bank-base edge whose target exists in the other bank
*whether or not it was joined*. So they are already inside
`cross-region edges counted, not joined`, which is not the rule's whole
accounting any more either. `unplaced_other_bank` is a counter of its own
rather than a test on the by-target breakdown so that the report can say this in
words; the two populations overlap and are not additive.

**Why the first two rows are labelled by the branch.** The issue asked for the
split between "no row in any scope" and "row only in the other bank". The first
term is labelled by what the code actually tests, and on this firmware the two
labels are not the same sentence. Exactly two of the unplaced target addresses
carry a row somewhere the branch does not look: **`0x2A6C`**, whose `common`
caller's single edge lands unplaced although the address carries a `bank0` row
*and* a `bank1` row and no `common` row — the branch consults the caller's own
scope and `common` and nothing else — and **`0xBBA4`**, which is the other-bank
term above. Every other unplaced target carries no row at all, so on this tree
the two readings nearly coincide; that is a measurement, not a guarantee, and
the branch-defined label is the one that stays true when a row lands at an
address another program happens to use.

---

## The figures

Measured statically over the committed listings by
`ec/tools/group_functions.py`, at `c453a273`, and reproducible with:

    python3 ec/tools/group_functions.py --report

| population | count | what it counts |
|---|---|---|
| the census | 3373 | every `lcall`/`ljmp` the committed listings carry (`A=1252 B=1484 C=637`) |
| `joined_edges` | 2962 | the edge was unioned to a row in the caller's own scope |
| `proxy_edges` | 124 | the edge ended at a per-bank proxy node instead |
| `unplaced_edges` | **202** | the edge ended at no row at all |
| `trampoline_edges` | 85 | the split mode removed the edge before the walk read it |

`unplaced_by_target` is kept beside `unplaced_edges` for the reason
`proxy_by_target` is: the edge total and the address total are two populations,
and 202 edges spread over 163 addresses is not a claim about either alone.

**The BIOS side reads zero.** `bucket_populations()` returns nothing for it —
every row is a module — so the identity there is `0 + 0 + 0 + 0 = 0` and every
new line prints a zero, the same way the existing proxy and cross-region lines
already do.

---

## Neither a join nor a cut

An unplaced edge is **neither a join nor a cut**, and the report says so in
those words. A cut is the proxy rule's decision, and it says something real
about the call structure: that a bank caller's endpoint for a common target
cannot be the common row without joining the banks through it. An unplaced edge
makes no claim about the graph at all. It is the absence of a decision, because
there is nothing to decide.

**It is a statement about `ghidra-functions.csv`, and about nothing else.** A
listing with no row is **not found by this method**, never absent from the
image. Whether the target is a function nobody has annotated yet, or a function
boundary Ghidra has not drawn, or an `lcall` into data, is a question about the
annotation pass — and this pass counts the edges rather than answering it.

`--self-test` pins the **printed strings** as well as the numbers behind them, in
the same `(label, needle)` style the proxy fixtures already use; every refusal
fixture in it passes against a report that says nothing about this population,
which is exactly how a partial accounting comes to stand as a whole one.
`test_group_functions.py` asserts the same classification directly against
`group_rows()`, so it is held even if the report text is rewritten.

---

## Boundary: what this is not

**Not [#445](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/445).** That
issue splits the **row-side** `ungrouped` remainder by why the method did not
group a row. This is the **edge side**, and it is a different population: a
caller with one unplaced edge can still be in a component through its other
edges, and an `ungrouped` row may be `ungrouped` because no caller reaches it
at all. The two counts are not additive and neither is a remainder of the
other. Kept apart deliberately.

**Not [#455](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/455).** That
is the proxy population and its `ungrouped` split — what the rule *did* to an
edge. This is what the rule had nothing to say about. The predecessor is
[`group-proxy-populations.md`](group-proxy-populations.md); cite it by file and
heading.

**Not the annotation half.** Adding `ghidra-functions.csv` rows for unplaced
targets would shrink this population, and the issue defers that to its own
issue. The 28 `pd` addresses it named already carry `pd` rows —
[`pd-unannotated-listings.md`](pd-unannotated-listings.md) (#489) landed after
the issue was written, and `ec/tools/test_pd_unannotated_census.py` holds that
every committed `pd` listing has one. So the deferral the issue asks for has
partly overtaken it, and what is left is a different population from the one
the issue could have sized.

**No listing/row census, deliberately.** "Of the unplaced edges, how many land
on an address that has a committed listing in the caller's own scope?" is the
annotation half arriving inside the accounting, and it is a different question
about a different tool — `pd_unannotated_census.py` already measures exactly
that shape for `pd`. It is the follow-up's sizing input, not this change's.

---

## What this does not establish

**Nothing here is a behavioural claim, and no live test ran.** Every figure is a
static measurement over committed `.asm` listings, reproducible with `--report`.
No hardware is reachable from a GitHub-hosted runner and nothing in this change
needs any. An unplaced edge says the tool cannot currently place it; it does
not say what the firmware does at that address.

**No constant anywhere holds a current-tree figure.** `--self-test` pins the
*identity* — the four terms partition `bucket_populations()` — and the
fixtures' own sub-counts, which are fixture values. The figures in this file are
recorded here, beside the command that re-derives them; no test assertion and no
other file repeats them.

---

## Follow-ups this surfaced

Two, named here and filed nowhere:

1. **The listing-without-a-row population outside `pd`.** #489 left `pd` with
   no listing that has no row, so the `common` area and the banks are the whole
   remaining question, and `pd_unannotated_census.py`'s tool shape is what would
   produce the number. Adding those rows would convert a share of the unplaced
   edges into joins — i.e. into real new `callgraph` structure, which is larger
   than a bookkeeping change.
2. **The blind spot this population sits inside.** An unplaced edge is invisible
   to `reached_only_by_bank`, to `cross_region` (except for the other-bank
   remainder), and to the `ungrouped` split, because all three are defined over
   edges that reached a row. The new line is the first place the partition is
   closed; whether the *row*-side accounting needs a matching statement is a
   question for #445, not for this change.