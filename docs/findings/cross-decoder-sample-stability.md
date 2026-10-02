# The cross-decoder sample's stride half is selected by content, so an annotation stops re-phasing it (issue #648)

`ec/ghidra/cross-decoder.csv` records, per sampled function, whether Ghidra's
exported C names the XDATA addresses `disasm8051.py` finds in that function's
opening straight-line instructions. Half of those rows are the **backbone** —
every function someone has read and annotated — and half are the **stride**, a
sample of what nobody has read yet.

That second half used to be chosen by position: `rest[::CROSS_DECODER_STRIDE]`
over the unannotated remainder in sorted `(program, addr)` order. The backbone
is a subset of the same list, so **adding one annotation removed one element
and shifted every later index by one**. The report changed wholesale — rows
moved to different addresses and changed verdict — and nothing in the file's
shape signalled it, because the row count did not change. That is the whole
of issue #648.

This measures the churn, changes the selection to a content-derived key, and
says what a `stride` row's verdict is a statement about. The sample's *size* is
reported by the run and is not written down here; what follows is the mechanism
and the measurement of it, on the committed tree at `9d711752`.

## The measurement

Both halves are derived from the committed listing index and annotations, and
the comparison is over the two stride halves rather than the two samples — the
annotated row leaves the stride half by becoming a backbone row, which is
correct and is what the `sample` column means. So the question per candidate is
"how many rows that annotation did *not* name stop being sampled":

```
$ python3 ec/tools/test_cross_decoder_sample.py            # Stability, via sample_over()

before:  positional   96 stride rows   common 77, bank1 12, bank0 7, pd 0
         keyed        80 stride rows   common 60, bank1 15, bank0 5, pd 0

one annotation, over every currently-unannotated row
         positional   median 47 stride rows lost, max 94
         keyed        0 stride rows lost, every time
```

The keyed rule loses exactly one row when it loses any: the row that was
annotated, which correctly stops being `stride`. Excluding that row, the loss
is zero for every candidate. The positional rule's median is roughly half its
own sample.

Two facts make the positional churn worse than a single row being retired, and
both are properties of how the sample is *proportioned* rather than of the
stride constant:

- **The stride half is dominated by one program.** The remainder is 620
  `common`, 84 `bank1`, 55 `bank0` and no `pd` at all, and both rules hand most
  of their rows to `common` — a positional slice over a globally sorted list
  takes every eighth of that combined list. So one annotation in `common`
  retires rows that were standing in for `bank0`.
- **`pd` contributes no stride rows and cannot have any.** All 541 `pd`
  listing rows are already annotated, so its remainder is empty, and the
  per-program "first row" fallback lands on `pd 0000`, which is annotated too,
  so the fallback never fires for it. That is a fact about how complete the
  `pd` annotation layer is — a real and separate question, not a defect the
  sampler can fix — and it survives this change. It was never stated anywhere;
  it is now in `cross_decoder_sample()`'s docstring and held as a property in
  the suite.

## The change

`cross_decoder_sample()` now selects on `cross_decoder_bucket()`: a CRC-32 of
`"%s:%s" % (program, addr)`, modulo `CROSS_DECODER_STRIDE`. Membership is a
function of the row's own content, so an annotation anywhere in the tree can
only affect itself.

**CRC-32, not Python's `hash()`.** `hash()` is salted per process, so a
sample keyed by it would differ between two runs of the same committed inputs
and fail `--check` for no reason at all. The old docstring gave exactly
that as the reason to avoid a hash — *"Sorted, and never ordered by a set or a
hash, because `--check` compares the committed report's rows against this
list"* — and it was right about determinism and wrong about which kind. The
sampler already returns `sorted(kind)` regardless, and `cross_decoder_problems()`
keys both sides on `(program, addr)` and compares cells, never order. What
`--check` needs is a *membership* that is stable across runs, which a stable
hash is and a salted one is not. That sentence is deleted rather than
rebutted, because it was the thing a later reader would otherwise cite as the
reason not to make this change.

`CROSS_DECODER_STRIDE` keeps its name and its value; what it selects changes
from "every eighth in sort order" to "one bucket in eight of the address
hash". The comment above it claimed "927 rows over four programs at this
value" — stale in both halves, since `pd` contributes none — and now states
the fraction and names where the size is reported instead.

## What a `stride` verdict is about

**A `stride` row's verdict is a property of the sample, not of the function at
that address.** The row was sampled because a content-derived key put it in
bucket zero, which says something about how complete the annotation layer is
and nothing about what the two decoders make of those bytes. Backbone rows are
the ones a person or an agent has read; a `stride` row is "nobody has read
this one yet", and it stops saying that the moment the annotation arrives.

This is why the churn was worth fixing rather than documenting. Under the
positional rule an unrelated annotation could silently retire a row that was
carrying evidence — a disagreement nobody would see retired. Under the keyed
rule the only row that moves is the one the annotation is about.

## The regenerated report

Recomputed from `ec/ghidra/cross-decoder.csv` after regeneration, not copied
from a prior write-up:

```
compared 1035 of 2041 functions, 1005 vacuous; 910 agreed, 125 disagreed, 1 no-export
```

| program | sampled | stride | compared | vacuous | disagree | no-export |
| --- | --- | --- | --- | --- | --- | --- |
| bank0 | 700 | 5 | 443 | 257 | 75 | 0 |
| bank1 | 607 | 15 | 346 | 260 | 25 | 1 |
| common | 193 | 60 | 61 | 132 | 5 | 0 |
| pd | 541 | 0 | 185 | 356 | 20 | 0 |

`docs/findings.md` §14i's most recent correction block
(`CORRECTION 2026-10-02 (issue #510)`) was current against the pre-change
report and is now stale on every cell, because the sample moved wholesale.
**It is not corrected here.** §14i is frozen and its correction blocks are the
`§4a-4d` shape — a dated measurement kept visible beside its correction — and
appending a fifth block for a sample that is now stable would be the
hand-kept-total failure `CLAUDE.md` names. What §14i needed was the statement
that the stride half is a sample and not a census, and that is what the
in-place paragraph adds: no figure, and no correction chain.

**The issue's own measured figures are not used anywhere, and do not
reproduce against any state of this tree.** It reports "1,983 rows, 954
vacuous, 707 agree, 321 disagree, 1 no-export". Recomputed over the committed
CSV before this change the split was `2,057 rows / 1008 vacuous / 920 agree /
127 disagree / 2 no-export`, and that matches neither the issue's numbers nor
the pre-`#510` matcher's split (719/328). Its row count matches neither the
CSV's nor §14d/§14f's `1,983`. That is recorded here rather than in the issue
because it is the reason a later reader should re-derive the numbers pasted
into an issue rather than quote them.

## What moving the sample broke, and what it says about pins

Two entries in `cross_decoder_disagreement.KNOWN_ANSWERS` were unannotated
functions — `common 0x1228` and `common 0x4BB0` — and were in the sidecar only
because the stride half happened to reach them. Moving the sample dropped both,
and `test_cross_decoder_disagreement.py` went red on them for a reason that had
nothing to do with the classifier.

That is the same distinction this write-up draws, arriving from the other side:
**a known answer pinned on a `stride` row is a claim about the sample, not
about the function.** Both pins are moved onto annotated functions now, and the
comment above the table says why that is load-bearing rather than incidental —
an annotated function is a backbone row precisely because someone has read it,
so it is carried by the annotation layer rather than by a hash, and it cannot be
re-phased by an unrelated annotation. The replacement rows were chosen to be as
legible as the ones they replace: `bank1 0xB409`'s body is
`cmp_dptr_to_r2r1(6000);`, and 6000 is 0x1770, so the decimal-literal cause is
readable straight off it.

The classifier itself is untouched, and the two sidecars' *methods* are not in
scope here — only which `(program, addr)` keys they carry follows the sample.

## The limits

- **`pd` still has no stride coverage**, and cannot under any key while its
  listing rows are all annotated. Whether that is a gap in the `pd`
  annotation layer is a separate question with its own issue.
- **The sample is still a sample.** A keyed sample is unbiased across runs; it
  is not a census, and no statement here should be read as one. The per-program
  proportions shift, because `common` no longer hands the sample most of its
  rows the way a positional slice over a globally sorted list did.
- **The key is a hash of an address, not of anything about the code.** It does
  not spread *behaviour*: consecutive addresses land in unrelated buckets, which
  is what makes it even, and a region of the image whose openings all name no
  XDATA address will still sample as `vacuous`. The `blind` and `cause`
  sidecars exist for that and are unchanged.
- **A pinned known answer on a `stride` row is still fragile.** The change
  makes it *stable against unrelated annotations*, not permanent: the next
  annotation to the function itself moves it from the stride half by becoming a
  backbone row, and a pin that assumes a `stride` row will keep assuming it.
  The fix is to pin on annotated functions, which is what the disagreement
  table now does — not a guarantee this change can give.
- **The first-row fallback is unchanged** and is not a content-derived rule:
  it is each program's lowest listing address. It cannot re-anchor when that
  row is annotated, which the suite holds as a property, because it was never
  the lowest *unannotated* row.
- **Regenerating moved the sample once, wholesale.** That is the last time it
  moves for an unrelated reason. Both sidecars follow automatically: they read
  the parent's `(program, addr)` rows rather than re-deriving the sample.

## Coordination with #520

#520 is open and records the consequence for an earlier merge — three added
annotations moving most of the stride rows, with §14i's figures not
re-measured. This change does not edit §14i's correction blocks, so the only
overlap is the block it declines to touch. A #520 re-measurement landing
after this one would describe a sample that no longer exists; whoever lands
second resolves by hand and keeps the regenerated report, since it is the one
the tree can reproduce.