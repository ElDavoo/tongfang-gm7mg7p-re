# A `pd` caller's edge was attributed to a `common` row it never reached (issue #471)

The write-up for [issue #471](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/471),
which is the `pd` half of the program-versus-address conflation that
`docs/findings/group-proxy-populations.md` recorded as a follow-up.

It is a one-line behavioural change to `cluster()`'s `reach` bookkeeping plus
the fixture that catches it. **The strongest thing that can be said for it is
that no published figure moves**: `--report` is byte-identical before and after,
both group CSVs regenerate byte-identical, and `--check` still passes. What
changes is *which branch is allowed to say a row was reached* — the defect was
that a branch which did not target the `common` row was allowed to say so.

**"Latent today" is the claim, and it is the one to preserve.** This is not a
fix that corrects the 26; it is a fix that stops the 26 being wrong for a reason
the current annotation state happens not to expose. Do not read the figures
holding steady as evidence the bug was harmless.

`docs/findings/name-basis-and-groups.md` has the grouping layer and
`group-proxy-populations.md` has the proxy accounting this is a correction to;
this file has the one remaining place where a `pd` edge and a `common` row were
treated as the same thing.

*** CORRECTION 2026-09-25 (issue #470), leaving this file's own measurements as
they were written.*** **Three figures below have moved, and one conclusion is
withdrawn.** "There is **no `pd` row at 0x11C2**" is no longer true:
`pd 0x11C2` `dispatch_code_table_2byte_key` was added, so the shared-address
count is **ten, not nine** (`0x11C2` is the tenth), the unannotated `pd`
population is **37 listings, not 38**, and the "The `11C2` case that must keep
its attribution" section below describes a case that no longer exists on the
committed tree. **Everything this file measured about the bug is unchanged** —
the six same-scope joins, the ordering fix, the 26/36/196 figures at the time,
and the fixture — because the row that landed was at an address no bank caller
reaches. The conclusion about 0x11C2 does not survive: the deferred
program-boundary question is answered, and the answer is that the edge was a
missing annotation rather than a question `region_of()` could not express. See
[`pd-common-address-spaces.md`](pd-common-address-spaces.md).

---

## The bug, stated precisely

`cluster()` walked each caller's `lcall`/`ljmp` edges, and for a target below
`BANK_BASE` it recorded the caller's scope against the `common` row at that
address **before** it decided which branch the edge took:

```python
if taddr in by_addr.get("common", {}):
    reach[taddr].add(scope)          # <- recorded unconditionally
if taddr in by_addr.get(scope, {}):
    union(caller, (scope, taddr))    # same-scope join
elif taddr in by_addr.get("common", {}):
    ... proxy ...                    # bank (or pd) caller's edge to a common row
```

Recording before the decision was right for the case it documented and wrong for
the rest. A `common` caller reaching a `common` row is joined directly rather
than proxied, but it still means the row was reached from outside the banks, so
it must be recorded — that is the 26-figure definition and it is pinned by the
`mixed` fixture.

It is wrong when the first branch wins. An address carrying both a `common` row
and a row of the **caller's own scope** is two different functions:
`ec/decompiled/pd/0C7A.asm` (`mul_r7_r5_r4_into_r6r7`) is not
`ec/decompiled/common/0C7A.asm` (`clear_low_nibble_of_1304`), because the
ITE8850-PD image is a separate program with its own address space. A same-scope
`pd` join takes the **`pd` row** as its endpoint, and the `common` row at that
address is not an endpoint of that edge at all — yet the reach was recorded
against it, and the caller scope it recorded (`pd`) is one that
`reached_only_by_bank` would then have to exclude.

This is the same conflation the `pd` grade rule and the dominant-scope naming
rule exist to prevent, and it shows up here in the bookkeeping rather than in
the grouping. The fix does not introduce a second program-boundary rule — it
stops recording a reach against a row the edge never touched.

---

## The nine shared addresses

Nine addresses carry a `common` row *and* a `pd` row. Both row names are given
because which row the name belongs to is the whole question here.

| address | `common` row | `pd` row | `pd` callers | bank callers |
|---|---|---|---|---|
| `0003` | `int0_vector_forwarder_to_052f` | `ljmp_0056` | 0 | 0 |
| `000B` | `timer0_vector_forwarder_to_0530` | `ljmp_0094` | 0 | 0 |
| `0013` | `int1_vector_forwarder_to_0556` | `ljmp_00b2` | 0 | 0 |
| `001B` | `timer1_vector_forwarder_to_05b6` | `ljmp_00f0` | 0 | 0 |
| `0023` | `serial0_vector_forwarder_to_05e6` | `ljmp_010e` | 0 | 0 |
| `0C7A` | `clear_low_nibble_of_1304` | `mul_r7_r5_r4_into_r6r7` | **1** | 0 |
| `0EF3` | `write_internal_ram_init_constants` | `or_32bit_r0r3_r4r7` | **2** | 0 |
| `10F1` | `zero_xdata_200b` | `read3_code_to_r3r1` | **3** | 0 |
| `383A` | `set_direct_bit_0c_3` | `unresolved_0x383A` | 0 | 0 |

The first five are the PD's interrupt-vector table on one side and the EC's on
the other — the same role, independently written in two images. `0x383A` is
coincidence: one image's `set_direct_bit_0c_3` and the other's
`unresolved_0x383A` have nothing to establish about each other, and nothing
here says they do.

The three with callers are the rows the ordering bug misattributed. Their edges
are `pd 0x36CB` → `0x0C7A`; `pd 0xC62B` → `0x0EF3` (twice, from two `lcall`s in
one listing); and `pd 0x0050`, `pd 0x10FD`, `pd 0x9850` → `0x10F1`. Every one of
those six edges joined the **`pd`** row. The `common` rows at the same three
addresses carry `ungrouped` / "Not found by this method" comments, and **this
change does not reclassify them** — it removes a reason they could have been
counted on, and no new reason is supplied.

The column that matters is the last one. **No `common` row reached by a `pd`
caller is also reached by a bank caller**, on any of the nine. That is the whole
of why the bug is latent: `reached_only_by_bank` only diverges between the two
behaviours when a bank reach and a spurious `pd` reach land on the same row, and
today no row has both.

---

## Two corrections to the issue's own numbers

Both are recorded here rather than repeated, because the issue text is quoted
elsewhere and the wrong figures travel with it.

**1. The unannotated `pd` population is 38 listings, not 81.** There are 535
`.asm` files under `ec/decompiled/pd/` and 497 annotated `pd` rows, so **38**
`pd` listings have no `ghidra-functions.csv` row. Every one of the 535 has a
matching `.c`, so counting both extensions gives the same 38 addresses, not 76.
(The issue's "81" counts something else; the number here is the one measured.)

**2. The three rows carry *zero* proxied edges and are not in the 81-edge
bucket.** `0C7A`, `0EF3` and `10F1` take the same-scope join branch, so no proxy
is built for them and none of the 196 proxied edges targets them. They are not
among the 10 rows in the 81-edge population. What the ordering bug did to them
was keep them *out of* the 26 by a spurious `pd` reach — which, since no bank
caller reaches them either, changed nothing observable. The issue's conclusion
("attributed by the wrong branch") is right; the bucket it said they sit in is
not.

**Both figures matter for the same reason: the population is defined by what is
annotated today, not by anything the rule controls.** 38 `pd` listings have no
row at all, so the set of addresses carrying both a `common` and a `pd` row can
grow as they are annotated, and the set of shared addresses with a bank caller
alongside a `pd` caller is a property of the current tree rather than a rule.
"Latent" describes this tree, not the logic.

---

## The fixture in the issue's literal shape cannot fail

The issue asks for "a `pd` caller and a `pd` row at the target address,
asserting the `common` row at that same address is not attributed a `pd`
reach". That fixture was built and run against the **unfixed** tool. **It
passes.** It cannot fail, because

```python
reached_only_by_bank = {t for t, s in reach.items() if s and s <= set(BANKS)}
```

is a subset test that already discards any non-bank scope. A `pd`-only reach is
invisible to it whether it was recorded spuriously or not. A green fixture of
that shape is the exact failure mode this issue exists to prevent, repeated one
level down — and shipping it would have closed the issue with a test that
certifies nothing.

**The `pd` reach becomes observable only when a bank reach is on the same row**,
because then the subset test is what separates them:

| `reach` for the shared address | `scopes <= BANKS` | in `reached_only_by_bank` |
|---|---|---|
| `['pd']` — bug or fix | False | no |
| `['bank0', 'pd']` — **the bug** | False | no |
| `['bank0']` — **the fix** | True | **yes** |

So the fixture is: a `common` row at the target address, a **`pd` row at the
same address**, a `bank0` caller reaching it, **and** a `pd` caller reaching it.
The bank0 caller's edge really does target the `common` row (there is no bank0
row at that address) and is proxied; the `pd` caller's edge joins the `pd` row
and is not. Asserting `reached_only_by_bank == {target}` **fails on the
unfixed tool** (`[]`) and **passes on the fixed one** (`['06A0']`). That is
pinned in `--self-test` and, in the same shape, as a `unittest` in
`ec/tools/test_group_functions.py`.

A second fixture pins the case that must **not** change, below.

---

## The fix, and the guard that is load-bearing

`reach[taddr].add(scope)` moved from before the decision onto the two branches
whose edge actually ends at the `common` row:

- the same-scope join branch, **but only when `scope == "common"`** — the
  `common`→`common` case the existing ordering documented and the `mixed`
  fixture pins, and where the join really does target the common row;
- the proxy branch, where the edge reaches the common row and the proxy
  replaces its endpoint;
- **not** the same-scope join when the scope is `pd` or a bank, because that
  edge joined the *other* program's row at the address.

**The `scope == "common"` guard is not cosmetic, and this was measured rather
than assumed.** The naive variant — relocate the call, drop the guard — loses
the 30 `common`→`common` same-scope joins on the committed tree, and the
consequences are all visible: the existing `mixed` fixture fails, and
`reached_only_by_bank` goes **26 → 35** with the 115/81 edge split moving to
**195/1**. That is the overcorrection the suite already catches, from the
opposite direction: it would have taken nine rows that a non-bank caller
genuinely reaches *into* the found-then-cut population.

---

## Measured: no published figure moves

Against the real tree, before and after, with `python3 ec/tools/group_functions.py`:

| figure | before | after |
|---|---|---|
| `reached_only_by_bank` | 26 | **26** |
| `proxy_edges` | 196 (bank0=126, bank1=69, pd=1) | **196 (same split)** |
| distinct `common` targets | 36 | **36** |
| proxied edges by row population | 115 / 81 | **115 / 81** |
| `ungrouped` | 456 (440 + 16) | **456 (440 + 16)** |

`--report` output is **byte-identical** between the two tools. `--apply` in a
throwaway copy produces **byte-identical** `function-groups.csv` for both
components from either tool, so **no CSV is regenerated and `--check` still
passes**, including that no `callgraph` name misstates its scope.

The three rows named above keep their existing `ungrouped` comments. Their
`group_basis` does not change and the `group_basis` vocabulary is not extended:
`ungrouped` asserts *no membership*, which is what `cross_bank_groups` relies
on, and the reason lives in the comment and the report.

**One pre-existing drift was found while checking this and is deliberately not
absorbed.** A fresh `--apply` rewrites the `evidence` cell of `bank1 0x8096`,
adding `ec/decompiled/bank1/1984.asm; ec/decompiled/bank1/198A.asm;
ec/decompiled/bank0/C0C9.asm; ec/annotations/xdata-06c2-06db-timers.md` to the
two paths the committed row carries. It reproduces **identically with and
without this change**, so it is unrelated to it, and folding a one-row CSV
rewrite into a change that is otherwise a no-op on the CSVs would hide it. It
wants its own issue.

---

## The `11C2` case that must keep its attribution

*** SUPERSEDED 2026-09-25 (issue #470).*** This section is kept because the
fixture it describes is still the one that guards the overcorrection, and
because the reasoning that produced it is what found the answer. But its
premise is gone: **`pd 0x11C2` has a row now**, the edge joins it directly, and
the `['common', 'pd']` attribution this section says `common 0x11C2` keeps is no
longer a live case — `pd` is no longer among its caller scopes, so it drops out
of the "reached from outside the banks" reasoning entirely. The fixture below it
is what still runs.

`pd 0xCB2A` (`store_0803_0805_then_jump_c808`) targets `common 0x11C2`
(`load_dptr_bf57_tail_jump_1100`), and there is **no `pd` row at 0x11C2** — the
`pd/11C2.asm` listing is one of the 38 unannotated ones. So the `pd` caller's
endpoint genuinely *is* the `common` row, the reach is real, and the edge is
genuinely proxied. It is the one real program-boundary edge in the 196, and the
single `pd=1` in the report's per-caller breakdown.

`common 0x11C2` therefore keeps a `['common', 'pd']` attribution and keeps its
`['common', 'pd']` exclusion from the 26. The fix preserves it, and the second
fixture pins it: a `common` row with **no** `pd` row beside it, reached by both
a `bank0` caller and a `pd` caller, must **not** land in `reached_only_by_bank`.
The bank caller is what makes that observable — a `pd`-only reach is invisible
to `reached_only_by_bank` for the same reason as above — so this fixture guards
against a `pd` reach being dropped rather than recorded wrongly, which is the
overcorrection on this side.

**What remains a follow-up, unchanged:** a `pd`→`common` edge is a question about
two separate programs, and `region_of()` has no vocabulary for a program
boundary, only for a bank one. The edge is counted and broken out by caller
scope so it is visible rather than hidden inside `bank->common`, and that is the
whole of what the edge population can honestly say about it. Recording that
limit is not settling it.

---

## What this does not establish

**Nothing here is a behavioural claim, and no live test ran.** Every figure is a
static measurement over committed `.asm` listings, reproducible with
`python3 ec/tools/group_functions.py --report`. No hardware is reachable from a
GitHub-hosted runner, and nothing in this change needs any.

**A reach that was recorded wrongly and is now not recorded is not a claim that
the row is unreached.** The 26 is "found by this method **and** reached only
from bank callers" — a statement about this tool's graph and its banking rule.
Removing a spurious reach makes that statement narrower and more accurate; it
does not turn any row into a subsystem, and it does not make any row *absent*
from any real grouping. `ungrouped` remains a result rather than a failure.

**Annotating the 38 unannotated `pd` listings is what would turn "latent" into a
live figure change**, and that is new annotation work rather than a consequence
of this change. Until it is done, the honest summary of this issue is the one it
was opened with: the misattribution is real, it is confined to the branches
that did not target the `common` row, and **no published figure depends on it
today**.
