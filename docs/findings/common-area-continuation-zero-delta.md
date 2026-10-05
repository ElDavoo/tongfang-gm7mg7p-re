# Following the common area moves no banked byte, so the residue is an edge vocabulary

`ec/annotations/bank-attribution.md` §9's first bullet called the reset vector
and the interrupt vectors "the single change most likely to move the residue",
and that bullet was wrong in a way worth keeping. They are seeds now, and
`closure()` follows a call into the common area as a same-bank continuation
rather than only recording it. **Together those two add entry points and zero
banked addresses, and leave all four verdicts exactly where they were.** So
§9's question — is what is left *seeds* or *bounds* — answers to neither. It is
the closure's edge vocabulary, and this write-up names the edge.

**What this is.** A measured negative, with the mechanism behind it and the
edge that would move the number, sized so the next agent does not have to
re-derive it.

**What this is not.** Not "the common area reaches no banked code". The route
exists and is in the firmware; §[The route out](#the-route-out-of-the-common-area-is-a-dptr-immediate)
reads it back from the bytes. It is that *this walk* cannot see it. And not a
verdict on the same-bank assumption: following a common call applies the
convention `offset_for_runtime()` already applies to bucket B, so it **extends**
that assumption rather than testing it, and the standing caveat in
`ec/annotations/bank-attribution.md` survives unchanged.

**And not "the walk is missing these routes" either.** That correction is in
[the route section](#the-route-out-of-the-common-area-is-a-dptr-immediate)
below, and it was this write-up's own error: an earlier draft named `0xD89F`
and `0xD96C` as targets the closure "now walks the code that names and still
does not reach", which its own tool output contradicted. The routes the walk
does not see are **already seeds**, which is why the zero holds — see below for
why that is the stronger reading and not a weaker one.

Everything here is static: Python over a committed `bytes` object. No register
was read, no capture was taken, and no `status:` in
`ec/annotations/registers.yaml` moves — none could.

## The measurement

Both changes are in `ec/tools/bank_attribution.py`. `closure()` gained a
`follow_common` parameter, and `vector_handlers()` reads the vector table's
common-area targets from `build_ec_decompile.vector_seeds()` rather than
re-walking it. The comparison below is between two closures the tool computes,
not between a remembered figure and a new one:

```console
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 | sed -n '/## 8/,$p' | head -12
## 8. The common area, followed: seeds, bounds, and neither

Two changes reach past the bank window, and this section measures
both against the closure without them. A `callee < BANK_FLOOR` is
followed as a same-bank continuation, and the vector table's
common-area handlers (7 of them) seed each bank.

| bank | entry points without | with | addresses without | with |
|---|---:|---:|---:|---:|
| `bank0` | 1010 | 1439 | 14830 | 14830 |
| `bank1` | 669 | 1039 | 12258 | 12258 |

The attributed address set is identical in both banks. The walk
does real work and gains no banked byte: that is the measured
answer, and it is a negative one.
```

and the four verdicts, over both populations:

```console
  all bucket-B pairs: +0 / +0 / +0 / +0 (agreeing / contradicting / still ambiguous /
    unreached), as the delta of the four verdicts.
  both-banks-live pairs: +0 / +0 / +0 / +0 (agreeing / contradicting / still ambiguous /
    unreached), as the delta of the four verdicts.
```

**The three contributions, kept apart.** The issue asked for this so the third
is not read as having done the first two's work. Each row below varies exactly
one thing against the same "without" baseline — the seeds row turns the
continuation off, the continuation row leaves the vector handlers out — so the
three are separately computed rather than one closure printed twice under two
labels:

```console
  vector-table seeds alone: +0 / +0 / +0 / +0 -- adds 7 entry point(s) and 0 banked address(es) in bank0, 7 and 0 in bank1
  common-area continuation alone: +0 / +0 / +0 / +0 -- adds 415 entry point(s) and 0 banked address(es) in bank0, 360 and 0 in bank1
  both (as shipped): +0 / +0 / +0 / +0 -- adds 429 entry point(s) and 0 banked address(es) in bank0, 370 and 0 in bank1
```

Neither change moves the verdicts on its own, so the zero is not the sum of two
cancellations that would partly survive either one alone. Two rows printing the
same figures would instead mean the two changes are *indistinguishable* on this
image, which is itself worth seeing, so the section prints a matching row rather
than collapsing one — the three agreeing here is a measurement, not a default.

**The entry-point deltas are what make the three rows checkable rather than
merely labelled.** The banked figures are `+0` in every row, which is the
finding, so a row that had quietly reused the closure above it would print the
same zeros under a second label and a reader — or a test — would have nothing to
notice. The seeds alone add seven entry points and descend nothing; the
continuation alone does nearly all of the descending. Those two numbers differing
is the evidence that the rows are really three different walks, and the suite
asserts each row's printed figures against a population it computes itself.

The table edges are absent from this comparison by construction — they are in
every population and cancel — which is why §3 and §4 of
[`ec/annotations/bank-attribution.md`](../../ec/annotations/bank-attribution.md)
report them, and why the 398 → 89 they produced is not credited here.

The identity is stronger than the four totals. `--self-test` asserts the
attributed **address set**, the **per-address path counts** and the **verdict
of each individual pair** are unchanged, so a byte that moved from one verdict
to another and another that moved back could not hide behind two totals that
happened to agree. Both committed CSVs regenerate byte-identically from
`--regions-csv` and `--pairs-csv`, which is the assertion the negative rests on:
a pin that had to be relaxed to accept this change was asserting nothing.
`PAIR_PINS`, `CHECK_PINS` and `CUT_RUNS` are untouched, and
[`ec/tools/test_bank_attribution_common_follow.py`](../../ec/tools/test_bank_attribution_common_follow.py)
holds the relations.

## Why: nothing above the floor is attributed from below it

`closure()` gates attribution on `pc >= BANK_FLOOR`. A common-area arm can only
add a banked byte by *decoding* a banked address, and on this image none of them
does — which is why the entry-point count moves and the address count does not.
The suite asserts that directly, from the other side: no address at or above the
floor has a `common`-kind entry point in `who`.

That is a property of this image, not a theorem, and it is why the wording above
is "by this walk" rather than "the common area reaches no banked code". A
rel8 branch from within 128 bytes of `0x8000` reaches above the floor, so the
gate is doing real work; it just does not fire here.

## The route out of the common area is a DPTR immediate

The common area *does* name banked code. It names it the way the linker writes
a cross-bank route — load the address into DPTR, then branch to the stub that
selects the bank:

```console
$ python3 -c '
import sys; sys.path.insert(0, "ec/tools")
from trace_xdata_refs import offset_for_runtime
from disasm8051 import mnemonic
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
off = offset_for_runtime(0x1150, "common")
print("common 0x1150 is `%s`" % d[off:off+6].hex(" "))
print("  = `%s` ; `%s`" % (mnemonic(d, off, 0x1150), mnemonic(d, off+3, 0x1150)))
'
common 0x1150 is `90 bf 1c 02 11 00`
  = `mov  dptr,#0xbf1c` ; `ljmp 0x1100`
```

The reset vector reaches two such routes directly, and `--self-test` pins both
as bytes:

- `0x158E` is `90 d8 9f 02 11 00` — `mov dptr,#0xD89F ; ljmp 0x1100`
- `0x1594` is `90 d9 6c 02 11 00` — `mov dptr,#0xD96C ; ljmp 0x1100`

Both are `lcall`ed from the reset vector at `0x0070`, which is itself one of
the seven handlers now seeding each bank, so the walk descends the reset vector
and descends both routes.

**But it does reach both targets, and that is the correction this section
exists for.** `0x158E` and `0x1594` are themselves entries in
`audit_call_targets.trampolines()`, so `seeds_for()` already makes `0xD89F` and
`0xD96C` bank-0 seeds and bank0's closure reached both *before* this change as
well as after. An earlier draft of this write-up said the opposite — that the
closure "now walks the code that names them and still does not reach them" — and
the tool's own output contradicted it, which is the calibration rule's worst
case: a confident negative about the firmware on the one pair of addresses that
is the counterexample.
[`reset-vector-dptr-targets.md`](reset-vector-dptr-targets.md) had already
recorded both as seeded.

So what these two routes are is **not** an example of an address the closure
misses. They are an example of the *census covering a route the closure
worklist does not have*, which is the opposite claim and is the one the
evidence supports. What is missing is the edge, not the address.

**The edge is not missing from `descend()`. It is missing from the worklist.**
`descend()` records the immediate in `arm.code_immediates` and never in
`arm.callees`, and `closure()`'s worklist is keyed on callees. The stub the
route lands on does not help either: `0x1100` is a 20-byte routine —
`find_banks.find_stubs()` walks the block 20 bytes at a time for exactly that
reason — whose last byte is the `ret` at `0x1113`, so nothing branches onward
to the DPTR's value. Two independent reasons the same edge is invisible, and
`--self-test` pins both halves — the target is in `code_immediates`, is *not*
in `callees`, and the stub *is*.

Measured over the entry points of kind `common` the closure actually reached,
those arms name 103 distinct banked DPTR immediates in bank0 and 108 in bank1 —
**but that is a count of how often the idiom appears, not a count of routes
nothing follows.** The trampoline census already names 102 of the 103 and 107 of
the 108, because the linker writes the route at the trampoline site, which is
where `seeds_for()` reads it. The section 8 of
`ec/tools/bank_attribution.py` prints the overlap next to the total so the two
cannot be read as the same figure.

**And there is no missed code route behind the leftover.** The one immediate no
trampoline names is `0x9000`, at `0x0F95` in the common-area clearing routine at
`0x0F75` — where `mov dptr,#0x9000` bounds the `movx @dptr,a` loop that clears
XDATA `0x9000`-`0x97FF`, and nothing branches to it. It is an XDATA pointer
that merely sits above `CODE_FLOOR`, not a route into banked code, and the
"non-linker DPTR immediate" the census misses is not present in the arms this
walk reached at all.

That is the honest reading of the zero, and it is stronger than the one it
replaces: the closure misses no banked route through the common area **not
because it sees every edge, but because every route it does not see is already
a seed.** Of the immediates in those arms that are not seeds of the bank whose
closure read them, all but that one `0x9000` name a target `seeds_for()` seeds
for the *other* bank — a cross-bank route, which following the common area
could only have attributed to the reading bank by extending the same-bank
assumption past what the standing caveat covers. So the zero is structural
rather than lucky, and the follow-up below has to be sized on the closure as a
whole rather than on an example this image does not contain.

## The answer to §9, and what it costs to act on

§9 asked whether what is left is *seeds* or *bounds*. The reset vectors were
the seeds candidate and they are now seeds; the `bounds` column in the regions
CSV already reports the walks that stopped, and the four verdicts above do not
move when those walks are given more room to stop. So the residue is neither. It
is the closure's edge vocabulary, and this is the edge.

What the correction above adds to that answer is *why* the vocabulary gap costs
nothing here, which is the part a reader deciding on the follow-up needs: the
routes the worklist cannot see are already seeds, so the gap is not a backlog on
this image. That is a statement about the census covering the linker sites, not
about the walk being complete — the edge is genuinely absent, and the DPTR-immediate
sizing below is what it would cost on a closure where something is not already
covered.

**Enabling it is a separate decision and is deliberately not done here.** A
`mov dptr,#imm16` at or above `CODE_FLOOR` is a code-pointer *candidate*, not a
proved entry — `walk_branch_arms.py` records it in `code_immediates` precisely
because it is one candidate among several, and `trace_xdata_refs.classify()`
treats the same bytes as an XDATA-vs-CODE ambiguity elsewhere. Turning it on
would move both committed CSVs and every reading in
`census_closure_functions.py`, so it needs its own calibration rather than
riding in on a finding whose whole result is that nothing changed.

It does move the number, which is why it is worth writing down. **Measured
repeatedly to a fixpoint, not once:** start from the closure as shipped, take
every banked DPTR immediate its entry points carry, add them all to that bank's
seed set, re-run `closure()`, and repeat until the seed set stops growing. Same
bounds, same dispatch edges, same continuation — the DPTR immediate is the only
thing added. The seed sets settle at 413 for bank0 and 239 for bank1, and the
four verdicts over **all bucket-B pairs** become **576 / 76 / 570 / 83**, where
they are 625 / 75 / 510 / 95 today. The residue falls by 12 and
`still ambiguous` rises by 60, which is the same trade issue #1079's table edges
made and in the same direction: more coverage, weaker separation on pairs that
were already ambiguous. Per bank the edge takes bank0 from 14830 to 15002
addresses and bank1 from 12258 to 15331. (Over the narrower both-banks-live
population the verdicts go from 614 / 75 / 510 / 89 to 574 / 73 / 560 / 81.)

The fixpoint is what makes the figure a property of the edge rather than of one
arbitrary round: a single pass stops at 576 / 76 / 569 / 84 and sizes 15001 /
15330, because it seeds what one round of descent finds and not what the next
round would. **This is a measurement of the closure as it stands, not a
proposal**, and it is not reproducible from the tool — `closure()` has no switch
for this edge, deliberately. Re-deriving it means the loop above; the figures
here are the ones it produces against the committed image.

**Two words in that recipe are load-bearing, and both were got wrong once while
checking it**, so the narrower readings are named here rather than left as a trap
for whoever re-derives this next. *Every* banked DPTR immediate means every entry
point in the closure, **not** only the ones of kind `common` — restricting the
sweep to those gives 601 / 71 / 539 / 94 and sizes 14999 / 12582, and those
`common`-kind entries are a different population from the 103/108 census above,
not a subset to iterate. And the seeds stay *seeds* across the rounds, keeping
the `frm is None` meaning `entry_chain()` reads; re-passing the whole entry-point
set as seeds each round is a third measurement again, and a different one. With
both right the seed sets settle at 413 and 239 and the figures are the ones
quoted.

That is the size of the follow-up, and it is *not* a recommendation to take it.
Read it as the number a reader needs before deciding whether a DPTR immediate is
evidence enough, given that taking it would move the agreeing class down.

## The calibration this inherits

Three things a reader should not take from this write-up:

- **"Zero" is scoped to this walk on this image.** Following the common area
  adds no banked address here. That is not a claim about what the common area
  contains.
- **Following a common call extends the same-bank assumption.** The
  continuation treats a shared routine as a continuation of whichever bank
  reached it. Where both banks reach one, both record it and neither claims it:
  the entry-point `kind` is `"common"` and `frm` is the entry point that reached
  it, so `entry_chain()` stops there rather than splicing past an address no
  bank owns. `ec/annotations/bank-attribution.md` §8's "Not a verdict on the
  same-bank assumption" still holds, and holds for a second reason now.
- **Nothing here was measured on hardware.** Every figure is a walk over a
  committed image. No `status:` in `ec/annotations/registers.yaml` moves.