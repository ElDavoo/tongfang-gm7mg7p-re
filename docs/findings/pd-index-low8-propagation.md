# The `low8` truncation is in the template; what was left was two summaries that had not been told

(2026-09-27, issue #73. Static reading of committed bytes in
`ec/firmware/GMxMGxx_11.800` plus the tool's own `--self-test`. No capture
opened, no EC, no hardware, no Windows, no `registers.yaml` row touched, no
committed CSV regenerated.)

Issue #73 was filed against a tree in which
`ec/tools/pd_index_geometry.py`'s `a424..f582e434..f583` template printed a
full product, and asked for four things: correct the template and its pinned
expectations, audit other matches, add arithmetic tests below and above
`0xFF` independently of the formatted-string expectations, and correct the
affected equations in `pd-index-geometry.md` plus the summaries linked from
it.

**Three of those four were already done when this was planned, and saying so
is the first result rather than a hedge.** #74 corrected the template, the
pinned expectations, `pd-index-geometry.md` §7.3/§8 and
`ec-0x07d0-sites.md` §4; the five committed CSVs already hold the truncated
form. That was verified here rather than assumed — the template at
`pd_index_geometry.py:160` reads `"=DPTR ← {base} + low8({a}×{b})"`, and
`--self-test` passes with all five CSVs regenerating byte-identically.
Repeating the correction would have duplicated a merged PR and manufactured
the conflict this work exists to avoid.

What was left is what the issue's own last clause asks for and #74 did not
reach: **two downstream summaries still quoted the old expression as if it
were current tool output**, and the arithmetic tests were only *partly*
independent of the formatted-string expectations.

## Which files already carried `low8`, and which two did not

`grep -rn '+ R7×0x5E\|+ A×0x5E\|+ R7×0x77' --include='*.md' .` finds
**eleven** lines outside this file and the summary that links to it (the
table below and `docs/findings.md` §96 add eight more, all of them this
write-up quoting the pattern it is classifying). Nine of the eleven are
correct as they stand and two were not; the classification is below, because
"it matched the grep" is not the same as "it was wrong".

| file | what it is | verdict |
|---|---|---|
| `ec/annotations/pd-index-geometry.md:71,74` | quoted `--self-test` console transcript | historical — the block is introduced as superseded, and §7.3's prose above it already prints the `low8` form |
| `ec/annotations/pd-index-geometry.md:602,639` | quoted `--sites`/`--helpers` listings | historical — §7.3's prose says in as many words that these are "not the unrestricted products printed below" |
| `ec/annotations/pd-index-geometry.md:75,731` | `0x578E` listed as `R2:R1 ← 0x089B + A×0x77` | historical on the destination (it is A:R1, §8.1's row has it right); the *product* is correctly untruncated |
| `ec/annotations/pd-index-geometry.md:728` | `not 0x0800 \| low8(0x70 + R7×0x77)` | a refutation already written against the wrong form |
| `ec/annotations/pd-index-geometry.md:843` | §8.1 table's `0x578E` row | correct — see below |
| `docs/findings/pd-callers-status-intersection.md:118` | `A:R1 ← 0x089B + A×0x77` | correct — see below |
| `docs/findings/walk-window-terminators.md:117` | `0x08F8 + R7×0x5E` | **stale — corrected in place** |
| `docs/findings.md:7824` (§57) | `0x08F8 + R7×0x5E` | **stale — corrected in place** |

The two stale lines are one step further out than the files #74 edited: each
is a summary *about* `pd-index-geometry.md` that quotes its decode from
memory rather than copying it, so a template corrected upstream leaves them
sitting on the old string. Both are retracted in place with the superseded
wording left visible, per the `docs/findings.md` §4a-4d pattern. **Neither
retraction changes its file's conclusion.** `walk-window-terminators.md`'s
finding is that a `read x1, write x1` cell is a miscount because `0x2C30C`
reads an R7-derived address, and it reads one under either spelling: the
discarded product byte and the carry out of the low base addition are
independent of each other. §57's is the same refusal of the budget-64
reading, for the same reason. That is why these are one-expression
corrections and not re-arguments.

## `0x578E` is exempt because its last instruction is a different instruction

The exemption is a fact about four bytes, not a judgement that one pattern is
safer than another. The two forms differ only in how the high half reaches
the high byte:

```
DPTR form   a4 24 lo f5 82 e4 34 hi f5 83   mul ab ; add a,#lo ; mov dpl,a ;
                                           clr a ; addc a,#hi ; mov dph,a
A:R1 form   a4 24 lo f9 74 hi 35 b0         mul ab ; add a,#lo ; mov r1,a ;
                                           mov a,#hi ; addc a,0xf0
```

`clr a` does not touch the carry flag on an 8051 and neither does `mov a,#hi`,
so the DPTR form's `addc a,#hi` adds the base's high byte to the carry out of
`add a,#lo` and **B is never read**. The A:R1 form's `addc a,0xf0` adds B
instead, so the full product lands in A. Nothing in the A:R1 form needs a
`clr a` because `mov a,#hi` has already replaced the accumulator.

So `A:R1 ← 0x089B + A×0x77` at `pd-callers-status-intersection.md:118` is
**correct and must not be "fixed"** — it is the one committed term whose
product is genuinely unrestricted. It is called out here because it reads like
the same defect as the two lines above it and is not, and a later sweep that
matched on the missing `low8` rather than on the template would have
corrupted 21 census rows.

That exemption is now a property of the file rather than a note in a
paragraph. Of the 977 rows in `pd-index-accesses.csv` — 956 `DPTR` and 21
`A:R1` — **21 carry an untruncated product and they are exactly the 21
`A:R1` rows**; no `DPTR` row does. (669 rows carry a `low8(…)` addend, all of
them `DPTR`; the rest are the forms that never multiply.) The self-test
asserts the first half of that, so a re-widened template that was *also*
propagated into the committed CSVs — the one drift the regeneration checks
cannot see, because they would have been regenerated to match — fails on it.

## The arithmetic pins, and what they do and do not catch

`access_self_test()` already executed each template's opcodes
(`byte_address()`) and compared the result against the term string evaluated
symbolically. That proves the two agree. It does not make either of them
right: two wrong strings in agreement sail straight through. The six new rows
in that self-test close the gap by comparing the executed bytes against
**addresses worked out by hand from the opcodes**, each paired with the
address the row exists to rule out:

| site | arithmetic at | index | builds | not | what the pair is about |
|---|---|---|---|---|---|
| `0xC2FA` | `0xC302` | 2 | `0x09B4` | `0x08B4` | product below `0x100`; the carry out of `0xBC + 0xF8` |
| `0xC2FA` | `0xC302` | 3 | `0x0912` | `0x0A12` | product `0x011A`; B discarded |
| `0x34D9` | `0x34DD` | 3 | `0x0916` | `0x0A16` | product `0x011A`; B discarded |
| `0xDA9B → 0x5950` | `0x5950` | 2 | `0x095E` | `0x085E` | suffix entered with `2×0x77` in A:B; base-low carry |
| `0xDA9B → 0x5950` | `0x5950` | 3 | `0x08D5` | `0x09D5` | product `0x0165`; B discarded |
| `0x578E` | `0x5792` | 3 | `0x0A00` | `0x0800` | the contrast: B *is* added, so the full product stands |

`0x5950` is the add-only suffix, entered with the product already in A:B
rather than carrying its own `mul ab`, so its `a` and `b` are the halves of
`R7×0x77` — `0xEE`/`0x00` and `0x65`/`0x01` — not the index and the
multiplier. The `0x0800` in the last row is what `0x5792` would build if it
dropped B the way the three DPTR rows do, which is what makes the row a
contrast rather than a fourth instance.

**What these pins catch, measured rather than asserted.** Swapping the
`0x0912` expectation for the pre-#74 `0x0A12` fails exactly one check, and it
is the pin: the committed bytes still build `0x0912`. That is the failure
mode they exist for — an expectation "corrected" to match a string rather than
to the opcodes.

**What they do not catch, stated so nobody relies on them for it.** They read
the image, not the template, so re-widening the template leaves all six green.
That is deliberate — it is the independence the issue asked for — but it means
they are not a re-widening detector. The term-string checks and the CSV
regeneration are: re-widening the template in place fails 15 checks, and
re-widening it *and* regenerating `pd-index-accesses.csv` to match fails 16,
the extra one being the census property above. The pins and the string checks
cover opposite directions and neither substitutes for the other.

`0xFFFC` for 16-bit wrap and the `0xB2D6` low-add-carry/high-byte-discard
pair were already in the self-test, so neither is duplicated here.

## What this does not establish

- **No index range is recovered.** Nothing here bounds `R7` or `A`, and
  nothing claims an index of 2 or 3 occurs on hardware. Every number above is
  what the bytes compute for a hypothetical index, which is the issue's own
  framing and no more. #26 owns the call-graph work.
- **No register status moves.** This is address arithmetic in a static decode.
  Nothing in `ec/annotations/registers.yaml` was read or edited, and no row
  there asserts anything about these four addresses.
- **No committed CSV changed.** The five CSVs already held the truncated form
  and `--self-test` regenerates all five byte-identically, which is the
  evidence that they were right and that the template's new output is the same
  output. The census count above is read out of the committed file, not
  regenerated into it.
- **A human runs nothing.** Every claim here is static over
  `ec/firmware/GMxMGxx_11.800`; there is no live step to defer.

## Reproducing

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
  ok  0xC302 at A=0x02 B=0x5E builds 0x09B4, not 0x08B4
  ok  0xC302 at A=0x03 B=0x5E builds 0x0912, not 0x0A12
  ok  0x34DD at A=0x03 B=0x5E builds 0x0916, not 0x0A16
  ok  0x5950 at A=0xEE B=0x00 builds 0x095E, not 0x085E
  ok  0x5950 at A=0x65 B=0x01 builds 0x08D5, not 0x09D5
  ok  0x5792 at A=0x03 B=0x77 builds 0x0A00, not 0x0800
  ok  the census's 21 untruncated products are all the A:R1 form
  ...
  ok  ../annotations/pd-index-accesses.csv: complete CSV bytes/schema/order regenerate
```

The self-test is not in `.github/scripts/agent-gates.sh`'s tool list, and
adding it there is out of scope: that file is part of the copied
`agent-pipeline` template set, which this pipeline's own `CLAUDE.md` says not
to edit casually, and the plan stage's push token has no `workflow` scope to
land such a change. The command above is run by hand and is what CI would need
to grow to hold it. Adding it is a human's change or an upstream
`ElDavoo/agent-pipeline` one.
