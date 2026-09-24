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
and the banks are not joined. **196 edges.**

So the rule that reads in the report as "cross-region edges counted, not
joined: 27" was in fact discarding **196 + 27** edges, and the 27 is the smaller
of the two by a factor of seven. Nothing was wrong with the clustering: the
report was offering a partial accounting as a complete one, which is the same
class of error as the overclaims `CLAUDE.md` §4 is about, one layer up.

**The second consequence is sharper, and it is about a claim in a file.** 456 EC
rows are `ungrouped`, and every one of them carried the identical comment:

> No typed seed and no connected component at or above the minimum size. Not
> found by this method.

For **16 of those 456**, that sentence is false. The method found them — 196
committed call sites reach them — and the tool's own banking rule is what cut
the edges. "Not found by this method" is a statement about the method, and for
these rows the method is not what happened to them.

---

## The figures

All measured statically over the committed listings by
`ec/tools/group_functions.py`, and reproducible with:

    python3 ec/tools/group_functions.py --report

| population | count | what it counts |
|---|---|---|
| `cross_region` | **27** | bucket-B edges whose target also exists in the other bank |
| `proxy_edges` | **196** | edges a caller had to an annotated `common` row, replaced by a per-bank proxy |
| ↳ `bank0` callers | 126 | |
| ↳ `bank1` callers | 69 | |
| ↳ `pd` callers | **1** | not a bank question — see the follow-up below |
| `reached_only_by_bank` | **26** | annotated `common` rows whose caller scopes are a non-empty subset of `{bank0, bank1}` |
| of those, `ungrouped` | **16** | reached by the method, then cut by the rule |
| `ungrouped` total | **456** | 440 not found by this method + 16 found then cut |

Two definitions are load-bearing, and both are pinned by `--self-test`:

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
    bank->common edges cut by the per-bank proxy rule: 196 (bank0=126, bank1=69, pd=1). A bank caller's endpoint for a common target is that bank's proxy, not the common row, so the two banks are not joined through it.
    annotated common rows reached only by bank callers: 26. The method found these and its own banking rule then cut the edges, which is a different reason from not being found.
    ungrouped: 456 (440 not found by this method + 16 found then cut by the proxy rule, never 'absent')
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
hidden inside "bank→common", and the tool says in `--report` that `pd` is not
part of that population. It is not fixed here.

For scale: there are 7 `pd` → annotated-`common` edges in the committed
listings, and only 1 becomes a proxy. The other 6 target addresses that exist as
`pd` rows too (`0x10F1`, `0x0C7A`, `0x0EF3`), so the direct same-scope join
runs first and no proxy is built. That ratio is a property of how the two images'
address spaces overlap, not a filter — worth knowing before anyone reads the 1
as "the PD program barely calls the common area".

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
