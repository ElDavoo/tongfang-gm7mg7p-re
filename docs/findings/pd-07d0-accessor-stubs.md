# The six `pd 0x07D0` accessors that were not functions, and what naming them did to the census (issue #1101)

[`walk-flow-follow.md`](walk-flow-follow.md) §2 records that the seven `0x07D0`
cells that stay `none` are the `mov dptr` at entry+3 of a byte-identical 7-byte
unit, and that a byte scan finds fourteen `lcall` sites reaching them. The same
§2 records that `ec/annotations/call-graph-callees.csv` carries one row for the
family. **The two statements are still both true, and they are still both
about the same fourteen sites — but the reason the census carries one row has
moved.** Before this change six of the seven units were not functions at all;
now all seven are, and the census still reads one row, for a different reason
entirely.

**Nothing here is a behavioural claim and no live test ran.** Every figure is a
static measurement over the committed firmware, the committed `.asm` listings
and the committed CSVs. No hardware is reachable from a GitHub-hosted runner and
nothing in this change needs any.

---

## What the six were, and what they are now

The seven entries are the same seven the byte scan found, and each is the same
seven bytes:

```console
$ python3 -c "
import sys; sys.path.insert(0, 'ec/tools')
pd = open('ec/firmware/GMxMGxx_11.800','rb').read()[0x20000:]
unit = bytes([0x12,0xF7,0x39,0x90,0x07,0xD0,0x22])
print(' '.join('%04X' % o for o in range(len(pd)-6) if pd[o:o+7] == unit))"
4C12 4C19 4C20 52EF 531F 7B0D 856F
```

Six of those seven had no `ghidra-functions.csv` row, so they were not
functions in the project, so `ec/decompiled/index.csv` carried no row for them
and `ec/decompiled/pd/` held no listing. Each is now one `forwarder` row at
`hand-decoded` / `code-shape`, seeded in the **default** `export-only` mode, and
each has a seven-byte listing and a decompile beside it. `4C20` already had all
of that; it is unchanged, and the family is seven near-identical rows rather
than one plus six strays.

The seven are the tail of a larger family, which is where the "seven" comes
from and not an arbitrary cut: the PD image holds **37**
`lcall 0xF739 ; mov dptr,#<addr>` units across **13** distinct addresses, and
exactly **7** of the 37 end in `ret` — and all 7 are the ones loading `0x07D0`.
The other 30 fall through into whatever the caller wrote next, which is why no
`ret` is what makes this one a handoff rather than a fragment.

**A byte-identical family is why the six names are suffixed rather than
reused.** `call_f739_then_return_dptr_07d0_4c12` and `..._7b0d` say the same
thing seven times over, and that is the honest reading: nothing in any of the
seven listings distinguishes it from the other six. The file already carries
suffixed duplicates for this reason (`set_dptr_0a4b_after_call_445e_08_b02f`
beside `set_dptr_0a4b_after_call_445e_08`), and the pattern is the same one.

## What the regenerated census says, and why it is not fourteen rows

The issue's second "done when" asked for a row per stub with real inbound
counts. **That is not reachable by naming the targets, and the reason is worth
more than the rows would have been.**

`call-graph-callees.csv` is a *callee-reached* census, not an inventory.
`call_graph.scan()` adds an edge only where a committed `.asm` listing carries
a transfer that resolves to the callee, and `build()` writes one row per key
`edges` produced. A callee no committed listing reaches therefore gets **no
row at all** — not a row reading `inbound=0`. Seeding six more *callees* adds
callers to `0xF739` and adds nothing to the seven stubs themselves, because
the seven stubs contain exactly one transfer each and it is a call *out*:

```console
$ grep -c . ec/decompiled/pd/4C12.asm && sed -n '7,9p' ec/decompiled/pd/4C12.asm
3
4C12     12 f7 39 lcall    0xf739
4C15     90 07 d0 mov      DPTR, #0x7d0
4C18     22 - -   ret
```

So the committed diff is **one line**, and it is not one of the seven:

| row | before | after |
|---|---|---|
| `pd,F739` `inbound` / `lcall` | 18 | 24 |
| `pd,F739` `callers` / `named_callers` | 10 | 16 |
| `pd,4C20` `inbound` / `lcall` | 1 | 1 |
| the other six stubs | no row | no row |
| `call-graph-callees.csv` rows | 1,841 | 1,841 |

`0xF739` is the number a reader would otherwise quote for the family, and it
moved by exactly six because the six new listings each contribute their one
`lcall 0xf739` to it. `0x4C20` is unmoved, and the six others still hold no row
— for the reason above rather than because they are not functions any more.
`call_graph.py --check` reproduces the file byte for byte.

**So the honest statement of the census is still "1 of the 14", and the reason
recorded is the census's shape.** §2's own text — "the other 13 sites have no
committed listing that spells them" — was already the correct reason and
survives unchanged. What has changed is that the six *targets* are functions
now, so the remaining thirteen are purely a missing-*caller* problem rather
than a missing-*callee* one.

## How many of the fourteen a committed listing spells: one

**One**, and the other thirteen are still byte-scan only. That is the figure
`ec/tools/test_pd_07d0_accessor_stubs.py` prints on every run, and it is the
number both write-ups now carry.

The reason thirteen caller addresses are in no listing is not that they are
hard to find, and an address span is not where they are hiding either.
**Measured against the `pd` listings' own spans, exactly one of the thirteen
falls inside a listing that does not spell it**, so the parse test and the
span test disagree by one:

- `pd/4D6F.asm` runs `0x4A12`–`0x4E58`, which covers two of the fourteen:
  `0x4B1D` (spelled, at `4D6F.asm:13`) *and* `0x4AE9` (not spelled).
- It does not spell `0x4AE9` because its `ajmp 0x4b12` at `0x4A12` skips the
  block holding it. A listing spanning an address is not a listing containing
  an instruction, and treating the first as the second is the whole error.
- The other twelve are outside every `pd` listing's span entirely.

Run the span test across *all* programs instead of `pd` alone and nine of the
fourteen are inside some listing's span, seven of them inside a `common`,
`bank0` or `bank1` listing and none of those seven at a `pd` instruction.
That larger number is an address-space conflation rather than a finding:
`pd`, `common` and the banks are separate programs, as every `pd` listing
header says and as
[`pd-common-address-attribution.md`](pd-common-address-attribution.md)
measures the cost of reading across them. The figure this page carries is the
`pd`-only one, and it is a count of spans, not a count of instructions.

That is also why the test asks `call_graph.parse_listing()` rather than
comparing addresses: the parse is what distinguishes *spelled* from *covered*,
and the suite holds `0x4C20` alone as the only entered stub so the distinction
cannot quietly rot.

**The census's silence is a property of the export, not a dispute about the
bytes.** Every one of the fourteen sites is in the firmware; one of them is in a
committed listing; the other thirteen are not found by this method.

## Two corrections to the issue's own text, recorded rather than repeated

- The issue says "the remaining **twelve** caller addresses" and then lists
  **thirteen**. Fourteen total minus `0x4B1D` is 13, which is what
  `walk-flow-follow.md` and `static-refs-audit.md` already say. This write-up
  uses 13.
- The issue says "Expect them uneven — the byte scan found two `lcall`s per
  stub". Those two claims are in tension, and the resolution is that they are
  about different things: **the byte scan is even** (2 per stub × 7 = 14) and
  **the census is uneven** (one row, `inbound=1`). Both are true; they are
  measurements of different populations, and the census's is a lower bound.

## What moved, and what did not

Every figure below is a count of the tree, which is the merge hazard CLAUDE.md
names, and each was moved with the delta recorded in the file that pins it
rather than edited silently:

| figure | before | after | pinned in |
|---|---|---|---|
| `index.csv` / `listing-index.csv` rows | 2,714 | 2,720 | `build_ec_decompile.py --self-test` |
| `ghidra-functions.csv` records | 1,951 | 1,957 | `build_ec_decompile.py --self-test` |
| `pd` functions / `annotations_applied` / `functions_named` | 535 | 541 | `ec/ghidra/manifest.csv` |
| `functions_named` total | 1,972 | 1,978 | `build_ec_decompile.py --self-test` |
| export-ownership `rows` | 2,714 | 2,720 | `export_ownership.py --self-test` |
| export-ownership `tiny_bodies` | 1,276 | 1,282 | `export_ownership.py --self-test` |
| `callgraph_pd_0003` component size | 499 | 505 | `function-groups.csv` |
| shape census `call_` / total | 92 / 283 | 98 / 289 | `subsystems.md` |

**`xdata_register_map.py` and `rank_common_runtime.py` did not move at all**,
which is the expected result and worth saying: a `pd` stub that names only
`0x07D0` and `0xF739` cannot reach the EC-side register census, and
`rank_common_runtime.py` walks `common`. `ec/annotations/registers.yaml` is
untouched — **no register's status changed, and `check_register_counts.py` is a
no-op**, because naming six functions establishes nothing about a register's
behaviour. `docs/findings.md` is not opened.

Two of those figures are worth a second sentence rather than a shrug.
`tiny_bodies` moved by exactly six because all six new bodies are 7 bytes and
every one is below the floor — the same coupling `rows` and `tiny_bodies` have
already recorded once. The `callgraph_pd_0003` component grew by six and no row
changed group, because a connected component absorbs a new member without
re-partitioning; the six were already in that component's region of the graph
through `0xF739`.

## What is left, and is not this issue's

**The thirteen caller functions are the next step, and naming them is what
would take the census from 1 of 14 to 14 of 14.** They are:

```
0x488F 0x4932 0x496C 0x4989 0x4AE9 0x5131 0x51B2
0x51E6 0x51FE 0x79B3 0x7A5A 0x842F 0x844B
```

This issue does not seed them: it is a second tranche over thirteen functions
in one region, against the `dispatch_case_06`-shaped block that
`walk-flow-follow.md` §2 already records no committed listing as spelling, and
it deserves its own issue rather than being folded into a change whose subject
is six callees. The list is here so the next issue does not re-derive it.

**What the callers do with the DPTR they are handed is still open**, and this
change does not touch it. What it settles is narrower and is what §2 needed:
the seven units are named functions with listings, cited to bank and address,
and the census's silence about them is now a fact about the export rather than
about the firmware.

## Three notes on how the artifacts here were produced

Recorded because each is a thing a reader reproducing this would otherwise hit,
and none of them is a claim about the firmware.

1. **The export ran with `JAVA_TOOL_OPTIONS=-Duser.name=dave`.** The committed
   Ghidra project records `OWNER=dave` in `ec/ghidra/project/ec.rep/project.prp`
   and this runner is `runner`, so `analyzeHeadless` aborts with
   `NotOwnerException` before it opens anything. Setting the JVM's `user.name`
   for the run is the whole fix; no committed file is edited, and the export is
   deterministic from committed inputs either way.
2. **23 `bank0`/`bank1` `.c` files differ on *any* re-export of this tree, and
   none of them is this change's.** Re-exporting from a pristine `HEAD` with no
   annotation edit produces the same 23 diffs — `DAT_EXTMEM_07c5` becoming
   `WHMS`, `DAT_EXTMEM_074c` becoming `PDIN`, and six `name_basis: code-shape`
   headers becoming `ec-register`. They are stale against the committed
   `xdata-symbols.csv` (which issue #1059 regenerated) and against the
   committed `ghidra-functions.csv` name grades, and no `.c` re-export has
   landed since. **This branch leaves all 23 at their committed content**, which
   is where `main` is; `index.csv` and `manifest.csv` are byte-identical either
   way, so only the `.c` bodies are affected. That staleness is worth its own
   issue and is not repaired here.
3. **`ec/ghidra/reassembly.csv` carries only the six new rows.** This runner's
   `sdas8051` is `02.00`; the committed report was produced with
   `05.50.4+NoICE+SDCCmods-WIP-R14`. A full `--report` here would rewrite 177
   name cells (the same staleness as above) and re-measure **52 outcomes** with
   the older assembler — every one of them `assembler-gap` under 05.50.4 turning
   into `match` or `partial` here — which would replace a better assembler's
   limits with a worse assembler's. So the six rows are the tool's own output,
   each honestly carrying `sdas8051 02.00` in its `assembler` cell, and the
   other 2,711 are untouched. `verify_reassembly.py --check` is the check that
   matters here and it is assembler-free: it compares every listing byte against
   the firmware and **recomputes all 2,717 `listing_digest` cells** from the
   listing each names, so the six new rows are verified rather than trusted.
   Their outcome is also assembler-insensitive on this shape — `0x4C20` is
   `match` under both — since `lcall` / `mov dptr` / `ret` is not a form
   either version struggles with.

## Reproducing this

```console
$ python3 ec/tools/test_pd_07d0_accessor_stubs.py     # 15 cases, no Ghidra
  a committed listing spells 1 of the 14 byte-scan sites: 04B1D
$ python3 ec/tools/call_graph.py --check
call-graph-callees.csv: 1841 rows, no diff
$ python3 ec/tools/verify_reassembly.py --check
  listing digests: 2717 compared against the committed report, 0 disagreement(s)
```

The suite asserts the *relationship* between the census and the listings — a
stub has a row exactly when a committed listing transfers to it, and that row's
`inbound` is the number of transfer sites — and deliberately asserts no count
of the seven, so that seeding the thirteen callers above moves the measurement
without anyone editing a test.
