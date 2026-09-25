# What the banking rule discards, and how much of it (issue #455)

The write-up for [issue #455](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/455),
which asked `group_functions.py` to account for the edges its own banking rule
throws away. It is a reporting and attribution change: **no join logic changed,
`cross_bank_groups` is untouched, and no group moved.**

`docs/findings/name-basis-and-groups.md` has the grouping layer itself — the
seeds, the naming rule, the proxy correction that created this question. This
file has what the proxy costs, and why the tool was reporting one of its two
discard populations and presenting it as the whole thing.

---

## The problem, stated precisely

`cluster()`'s no-cross-bank rule cuts edges in **two** ways, and until now only
one of them had a line in `--report`.

**1. Bank↔bank (`cross_region`, the one that was reported).** Nothing in an
`lcall` names a bank — bank0→bank1 and bank0→bank0 are the same three bytes, and
both banks are mapped at base 0x8000. So a bucket-B edge whose target also
exists in the *other* bank is genuinely ambiguous, and the tool counts it and
never merges on it. **27 edges.**

**2. Bank→common (`proxy_edges`, the one that was not).** A `common`-scoped row
is one function both bank images carry, so a bank0 caller and a bank1 caller
that both reach it are two halves of *one* node, and that node joins the banks
however sound each edge is. `PROXY_SCOPE` gives each bank its own endpoint
instead, so the callers sharing a helper stay connected inside their own bank
and the banks are not joined. **195 edges.**

So the rule that reads in the report as "cross-region edges counted, not
joined: 27" was in fact discarding **195 + 27** edges, and the 27 is the smaller
of the two by a factor of seven. Nothing was wrong with the clustering: the
report was offering a partial accounting as a complete one, which is the same
class of error as the overclaims `CLAUDE.md` §4 is about, one layer up.

**The second consequence is sharper, and it is about a claim in a file.** 478 EC
rows are `ungrouped`, and every one of them carried the identical comment:

> No typed seed and no connected component at or above the minimum size. Not
> found by this method.

For **16 of those 478**, that sentence is false. The method found them, and the
tool's own banking rule is what cut the edges. "Not found by this method" is a
statement about the method, and for these rows the method is not what happened
to them.

The edge count and the row count are different populations, and 195 is not the
number for these 16. The 195 proxied edges reach **35** distinct `common` rows,
and **70** of those edges land on these 16. The other 125 edges reach 19 more
rows in the same population: the 10 `reached_only_by_bank` rows that stayed
grouped (45 edges), and 9 rows a `common` or `pd` caller also reaches (80
edges), which are not found-then-cut at all — a non-bank caller's edge to one of
them is joined directly rather than proxied, though the bank edges to those same
rows are proxied like any other. So 195 is the population the rule discarded, 70
is the part of it that reaches these 16, and quoting the 195 for them would
repeat the error this note exists to correct.

---

## The figures

All measured statically over the committed listings by
`ec/tools/group_functions.py`, and reproducible with:

    python3 ec/tools/group_functions.py --report

| population | count | what it counts |
|---|---|---|
| `cross_region` | **27** | bucket-B edges whose target also exists in the other bank |
| `proxy_edges` | **195** | edges a caller had to an annotated `common` row, replaced by a per-bank proxy |
| ↳ `bank0` callers | 126 | |
| ↳ `bank1` callers | 69 | |
| ↳ `pd` callers | **0** | was 1 — an annotation gap, closed by #470; see the correction below |
| ↳ distinct `common` rows reached | **35** | the rows those 195 edges land on — *not* the same number as the 195 |
| ↳ edges to `reached_only_by_bank` rows | 26 rows / 115 edges | 16 are `ungrouped` (70 edges), 10 stayed grouped (45 edges) |
| ↳ edges to rows a non-bank caller also reaches | 9 rows / 80 edges | joined directly, so not found-then-cut |
| `reached_only_by_bank` | **26** | annotated `common` rows whose caller scopes are a non-empty subset of `{bank0, bank1}` |
| of those, `ungrouped` | **16** | reached by the method, then cut by the rule; 70 of the 195 proxied edges |
| `ungrouped` total | **478** | 462 not found by this method + 16 found then cut |

The `proxy_edges` block reconciles the same way the `ungrouped` line does: 115 +
80 = 195 edges, and 70 + 45 = 115. Nothing in it is an unexplained remainder,
which is the point — an edge total offered without the rows it lands on is the
partial accounting this file is about, just one level down from the one the 27
used to stand for.

Three definitions are load-bearing, and all three are pinned by `--self-test`:

- **`proxy_edges` counts edges; `reached_only_by_bank` counts rows.** They are
  not the same population, and neither is a subset of the other: the 195 edges
  reach 35 rows, 26 of which are reached only by bank callers and 9 of which a
  non-bank caller also reaches. So the 195 is the accounting for the *edges the
  rule cut*, and the 26 and the 16 are the accounting for *rows* — attaching the
  edge total to a row count is what this pass corrected, and `--report` prints
  the edges' per-target breakdown so the two can be reconciled by hand.
- **`reached_only_by_bank` is a non-empty subset of the banks.** At least one
  bank caller, and nobody outside them. A `common` row a `common` caller also
  reaches is *excluded*: that edge is joined directly rather than proxied (both
  ends are `common`, so no bank is implicated), but it still means the row is
  reached from outside the banks, and calling it "reached only by bank callers"
  would be a claim about its callers that the edge list contradicts. A row with
  no caller at all is excluded by the non-empty half — it is unreached, which is
  a different thing again.
- **The two populations do not overlap.** Every proxy edge targets an address
  below `BANK_BASE`, so none of them is a bucket-B edge. A caller scope reaching
  an annotated `common` row is recorded in the same walk as the union, before
  the join/proxy decision, so the common→common direct join is counted too and
  the figures cannot drift from the clustering that produced them.

  *** CORRECTION 2026-09-25 (issue #471), leaving the clause above as it was
  written.*** "**before the join/proxy decision**" described the ordering this
  issue removed, and it was too broad: recording the reach before the decision
  also recorded it when the decision was a same-scope join to a row of the
  *caller's own* program, which is a different function at the same address —
  `pd/0C7A.asm` is not `common/0C7A.asm`. The common→common direct join the
  clause was written for is still counted, and still on the same walk as the
  union; what no longer happens is a `pd` or bank caller marking a `common` row
  reached when its edge joined the other program's row. Every figure in this
  file is unchanged and byte-identical under the corrected rule, because no
  `common` row that a `pd` caller reaches is also reached by a bank caller on
  the committed tree — see
  [`pd-common-address-attribution.md`](pd-common-address-attribution.md).

The 16 rows, for a reader who wants to look:

```
common 05EF  critical_section_exit_05ef          common 3C0A  read_0a49_then_index_iram_by_plus_97
common 1114  bl51_bank_select_1                   common 3F9D  store_r7_to_iram_bb_then_set_68_0
common 2896  clear_iram_6d_7f_then_xdata_b00_bfe  common 3FA4  store_r7_to_iram_31
common 2990  advance_bfe_counter_publish_at_bfd   common 4A4D  code_word_to_dptr_4a4d
common 2BC1  clamp_iram_80_up_to_r7               common 4A69  code_word_to_dptr_4a69
common 2DE3  mask_1106_then_clear_18_34           common 4A76  mov_a_from_r1_4a76
common 3894  set_iram_ad_88_clear_33              common 5597  write_009f_4f_or_0f_by_r7
common 3B4E  read_dptr_into_r6_then_r7_3b4e
common 3B70  dph_from_a_dpl_from_code_3b70
```

`group_basis` stays `ungrouped` on all 16 — and the CSV was **regenerated** with
`--apply`, never hand-edited. The basis is not extended: `ungrouped` asserts *no
membership*, which is what `cross_bank_groups` relies on when it skips the name.
The reason lives in the comment and in the report, where it is a statement about
a row rather than a new entry in the closed vocabulary.

Note that 26 rows are found-then-cut but only 16 are `ungrouped`. The other 10
have a seed, or a component of their own that clears the minimum size; the
proxy population is about which *edges* were cut, not about which rows ended up
grouped.

**The BIOS side is inert by construction.** It has no `bank0`/`bank1` scopes at
all — every row is a module — so proxy = 0 and cross = 0 there, and
`--apply` leaves `bios/annotations/function-groups.csv` byte-identical.

---

## What is now in the report

Every line states the edges it covers and why they are cut, so no figure can be
read as the rule's total cost:

```
    cross-region edges counted, not joined: 27
    bank->common edges cut by the per-bank proxy rule: 195 (bank0=126, bank1=69). A bank caller's endpoint for a common target is that bank's proxy, not the common row, so the two banks are not joined through it. Those 195 edges reach 35 distinct common target(s): 115 land on rows reached only by bank callers, 80 on rows a non-bank caller also reaches.
    annotated common rows reached only by bank callers: 26. The method found these and its own banking rule then cut the edges, which is a different reason from not being found.
    ungrouped: 478 (462 not found by this method + 16 found then cut by the proxy rule, reached by 70 of the 195 proxied edges, never 'absent')
```

The two ungrouped reasons sum to the headline, so neither is an unexplained
remainder. `'absent'` stays on the line in the sense CLAUDE.md requires: these
are not-found-by-this-method results, whether the not-finding came from the
graph or from the rule the tool applies to it.

`--self-test` asserts these **printed strings**, not just the numbers behind
them, and that is the part worth keeping. The existing fixtures check that the
edge is proxied and the endpoint is not a row; every one of them passes against
a report that says nothing about any of this, which is exactly how 27 came to
stand for the whole cost. Pinning the refusal is not pinning the accounting.

The same applies to the edges-versus-rows split, and it is why the report prints
it rather than leaving the reader to infer it. The fixture has four callers
reaching one `common` row, so it pins `4` edges, `1` distinct target, `4` edges
attributed to the found-then-cut row — and then repeats the report for the same
graph with a `common` caller added, where the same four edges must be attributed
to the *other* population instead. A report that attributed every proxied edge to
the found-then-cut rows would fail the second fixture.

---

## One qualification the note needed

The report's connected-components note said the graph "says these functions
are mutually reachable". That was stronger than the groups now are, for a
reason the proxy created: **a path between two members of a `callgraph` group
can run through a proxy node that is not a member.** A common helper shared by
two members of `callgraph_bank0_0EA2` is reached through `bank0#common`, and
that node is not in the group. So "mutually reachable" is a property of the
graph the union walked, not of the set of rows carrying the name. The note now
says so.

The alternative — making a group carry its proxy-shared common rows as members
— was available and was **not** taken. It would change group membership, sizes
and names across the whole committed CSV to make a claim that a qualified note
already makes honestly. Recorded here so the choice is visible rather than
invisible in a diff.

---

## A follow-up this surfaced, not one it fixed

**The single `pd` proxy edge is a program-boundary question, not a banking one.**
`pd 0xCB2A` (`store_0803_0805_then_jump_c808`) targets `common 0x11C2`
(`load_dptr_bf57_tail_jump_1100`), and the bank proxy rule is what handles it.
But `pd` is the **separate ITE8850-PD program** with its own address space — the
two rows are not two endpoints of one call, they are one row in each of two
firmware images, and the question "which bank ran this" is the wrong question
for them. `region_of()` has no vocabulary for a program boundary, only for a
bank one.

It is **counted and broken out by caller scope** so it is visible rather than
hidden: `--report` prints it as `pd=1` *within* the 196, under a `bank->common`
label, and itemises the caller scope so the one program-boundary edge can be
told apart from the 195 bank ones. That is the whole of what the edge
population can say about it — `region_of` has no word for the question. It is
not fixed here.

For scale: there are 7 `pd` → annotated-`common` edges in the committed
listings, and only 1 becomes a proxy. The other 6 target addresses that exist as
`pd` rows too (`0x10F1`, `0x0C7A`, `0x0EF3`), so the direct same-scope join
runs first and no proxy is built. That ratio is a property of how the two images'
address spaces overlap, not a filter — worth knowing before anyone reads the 1
as "the PD program barely calls the common area".

It also shows up in the table above, which is the consistency check worth
making. `common 0x11C2` is reached by one `pd` caller and one `common` caller
and by **no bank caller at all**, so it is one of the 10 rows in the 81, reached
there by that single `pd` edge — and it is not one of the 26
`reached_only_by_bank` rows, because one non-bank caller is enough to take a row
out of that population, exactly as one `common` caller is.

**What issue #471 later corrected is the *attribution* of those other 6, not
the rule.** The 7-edges-and-1-proxy ratio above is unchanged and is still the
right reading. But the 6 same-scope joins were also recording a `pd` reach
against the `common` row at the same address — a row their edges never reached
— and `common 0x11C2` kept its real `['common', 'pd']` attribution precisely
because it had no `pd` row beside it. See
[`pd-common-address-attribution.md`](pd-common-address-attribution.md).

---

*** CORRECTION 2026-09-25 (issue #470), leaving the section above as it was
written.*** **The single `pd` proxy edge was a missing annotation, not a
program-boundary question**, and the section above is wrong about which. The
premise survives — `pd 0x11C2` and `common 0x11C2` really are one row in each of
two firmware images and are not two endpoints of one call — but the *reason* the
proxy branch was reached has nothing to do with that.

The branch is reached on one condition: **the target has no row in the caller's
own scope.** For a `pd` caller that means "no `pd` row at 0x11C2", and nothing
more — a statement about `ghidra-functions.csv`, not about the images. The
`pd/11C2.asm` listing was already exported (the function entry came from the
call-target scan) with no row behind it. Adding the row — `pd 0x11C2`
`dispatch_code_table_2byte_key`, the two-byte-key twin of `pd 0x119C`
`dispatch_code_table` — joins the edge directly and the `pd=1` falls out of the
196.

**So `region_of()` never needed a program boundary, and adding one would have
modelled a question the code does not ask.** The counting was never wrong; the
`pd=1` was read as a banking result because it sat inside a `bank->common`
parenthetical under a `bank->common` label. What was missing was a row and a
reader who could tell a gap from a region.

Four figures move, and nothing else does: 196 → **195** (bank0=126, bank1=69
both unchanged), the distinct `common` targets 36 → **35**, the 81-edge
non-bank-reached bucket → **80**, and the `callgraph_pd_0003` component 413 →
**414**. `reached_only_by_bank` stays 26, `cross_region` stays 27, and the
`callgraph_pd_0003` rows carrying the name stay 303 — the new row takes a
`type=dispatch` seed into `dispatch-tables` instead, and a seed outranks a
cluster. "A listing with no row" is **not found by this method**, never absent
from the PD program; 37 `pd` listings still have no row, and each is ordinary
annotation work. Full write-up, the byte comparison and the reproduction are in
[`pd-common-address-spaces.md`](pd-common-address-spaces.md).

**The two 32 KiB low areas are not interchangeable, which is what the premise
above was reaching for and did not have.** `firmware[0x00000:0x08000]` and
`firmware[0x20000:0x28000]` agree on 503 of 32768 bytes (1.54%), and all ten
addresses now carrying rows in both scopes differ. That is a comparison of two
images, not a behavioural claim, and it is why the two rows must not be merged.

---

## Boundary: this is not #445

[#445](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/445) splits the
**residual** 440 `ungrouped` rows by why the method did not group them — "no
`lcall`/`ljmp` edge at all" versus "a component of 2 or 3". Its 576/516/60
figures are from the **pre-proxy** clustering, so they are not a competing count
of the same population and the two cannot be added together.

This is a **third** population, the one the proxy created, and it is different in
kind: those 16 rows *were* reached. The method found them, and the tool's own
rule is what discarded the edges. Not blocked on #445 and not duplicating it.

---

## What this does not establish

**Nothing here is a behavioural claim, and no live test ran.** Every figure is a
static measurement over committed `.asm` listings, reproducible with
`--report`. A `pd`→`common` edge being counted here says the tool cannot
currently classify it; it does not say what the firmware does at that address,
and no hardware is reachable from a GitHub-hosted runner.

The 26 are "found by this method **and** reached only from bank callers" — a
statement about this tool's graph and its banking rule, not a claim that those
26 routines have no subsystem, and not a claim that they are absent from any
real grouping. `ungrouped` remains a result rather than a failure, and saying
which of the two reasons applies costs nothing because the word is in the
vocabulary.
