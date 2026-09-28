# The call censuses get a framing column, and the tie-break that fills it (issue #1110)

Every row of `bank-call-targets.csv`, `bank-paged-call-targets.csv` and
`bank-relative-branch-targets.csv` now carries an `earlier_record` column: the
record that starts one or two bytes before the site and spans it, as
`0xOFFSET bytes mnemonic`, or empty when the rule finds no such candidate. It
is [#54](paged-trampoline-hits-by-hand.md)'s question made mechanical — that
write-up read all 18 `calls_trampoline` paged rows one at a time and closed
with *"the fix is not 'drop the row' but 'record why'"* — and the rule, the
tie-break that decides between two candidates, and what the column does **not**
settle are below.

Nothing else moves. No register `status:`, no row added to or removed from any
census, no `bucket`/`frame_onto`/`frame_over`/`target`/`in_region` value
changed, no function entry seeded, no Ghidra rebuild, no hardware and no
Windows: nothing here needs either, so nothing is deferred to a human at the
machine. **No claim is made about what the EC executes.** The column is a
candidate generator, and [the blind spots](#the-blind-spots) are the reason.

## The rule, stated precisely

A **candidate** for a site at `off` in region `[lo, hi)` is an offset `j` where:

1. `j ∈ {off-1, off-2}` — one or two bytes earlier, the shape #54 read its 18
   owners into;
2. `j >= lo` — the record is inside the caller's **own** region, the same
   region-relative discipline every loop in
   [`audit_call_targets.py`](../../ec/tools/audit_call_targets.py) already has.
   Reading a candidate out of the neighbouring program would be a different
   claim about a different address space;
3. `j < off < j + OPCODE_LEN[d[j]]` — it **spans** the site strictly, never
   starts at it. The strictness is #54's own and
   [`test_paged_trampoline_framing.py`](../../ec/tools/test_paged_trampoline_framing.py)
   pins it for all 18 owners; and
4. `d[j] & 0x1F` is not in `(0x01, 0x11)` — the **non-circularity skip**, using
   the same predicate `paged_sites()` keys on, for #54's reason: a phantom
   explained by a neighbouring phantom is not an explanation.

The column is built from the committed decoder, not from a new opcode table:
`disasm8051.OPCODE_LEN` for the span, `disasm8051.mnemonic()` for the
rendering. The mnemonic is that function's own output with its column padding
squeezed, because the padding is a rendering choice and the column is the
instruction rather than the layout.

It is **derived per family, not once for all three** — `earlier_record()` is
called from `survey()`, `paged_survey()` and `relative_survey()` rather than
computed in one place. #93 and `bank-call-audit.md` §8 read 170 relative sites
into the shape #54 read 18 paged sites into, and those are separate scans:
neither is evidence for the other, so a single shared computation would assert
a connection the write-ups explicitly decline.

## The tie-break is a choice, and it is the part the issue does not specify

A site can have **two** surviving candidates. At `0x12C0` the owner is `0x12BE
mov dptr,#0xbf81` and the decoy is `0x12BF cjne r7,#0x81,0x12c4` — both span
the site, and #54's negative controls say the wrong framing of those same
bytes also contains a paged call, so "it looks like a paged call" selects
nothing. Something has to choose, and the issue does not say what.

**7 of #54's 18** leave two candidates, so the choice is load-bearing on more
than the one site the issue names. Four rules were measured against the 18
transcribed owners:

| rule | owners re-derived |
|---|---:|
| nearest start (lowest offset) | 14/18 |
| furthest back (highest offset) | 15/18 |
| furthest end (reaches furthest past the site), ties to the lower offset | 12/18 |
| **highest `converges_from()` score, then lowest offset** | **18/18** |

So the rule is: among surviving candidates, take the one with the higher
`converges_from(d, j)[0]`, breaking ties toward the lower offset.

**This is a stated choice among named alternatives, not a verdict.**
`converges_from()`'s own docstring says a site everybody syncs onto is not
thereby real and a site nobody syncs onto is not thereby misframed, and 18/18
does not survive that sentence — it says the rule agrees with one hand reading
on one image, nothing more. The write-up it appears in is
[#54's](paged-trampoline-hits-by-hand.md), and the three alternatives are named
here so a reader who prefers a different rule can see what it costs. Of the
**337 paged rows** that leave two candidates, nearest start would name a
different record on **129** of them, furthest end on **150**, and furthest back
on **208** — so this is not a rule that agrees with its alternatives almost
everywhere, and the ablation is the evidence rather than a formality.
[`test_earlier_record_column.py`](../../ec/tools/test_earlier_record_column.py)
asserts each of the three to *fail* on at least one owner, so a later refactor
cannot swap in a simpler rule that happens to look equivalent.

The rule that needs the ablation most is **furthest end**, and it is named for
what it measures rather than for what it sounds like. Its key is the
candidate's **end offset**, not its length, so it takes the record reaching
furthest *past the site* — which is the same `max` this column uses, with the
score swapped for extent, and is what a reader re-deriving this reaches for
first. At `0x12C0` it lands on the decoy, and not because the decoy is
longer: both candidates are three bytes, and the decoy wins because its edge
sits one byte further past the site. A rule that maximised the record's
*length* would have nothing to separate them there, fall to its own tie-break,
and land on the owner — it is a real alternative, and it is the one this
ablation does **not** measure. The case is named in the suite for the same
reason.

## A column, not a filter

`bank-call-audit.md` §2 already says the anchored half of every count is not
the phantom-free one. A filter that dropped the 3,089 named paged rows would
leave §1's byte-scan upper bounds intact and destroy the ability to say what
they contain; a column that names the alternative framing makes the choice
visible per row and leaves the number a number. So **no row is dropped**, the
row counts are unchanged, and every pre-existing column holds the value the
committed file holds — including `own_bank`/`other_bank`, whose rows are the
two `bank1-e582-entry-framing.md` settled by a byte argument rather than by
these columns, and which the column therefore does not disturb.

## The re-measured figures

Re-measured on the committed image rather than carried from the issue, as
`CLAUDE.md` requires:

| census | rows | with a candidate | without |
|---|---:|---:|---:|
| `bank-paged-call-targets.csv` | 3,481 | 3,089 | 392 |
| `bank-relative-branch-targets.csv` | 9,076 | 4,932 | 4,144 |
| `bank-call-targets.csv` | 5,998 | 2,508 | 3,490 |

The paged figure reproduces the issue's 3,089 exactly, which is the main
evidence that the rule above is the intended one rather than a rule that
happens to be defensible.

**The empty cells are not a finding and are not resolved here.** 392 paged
rows and 4,144 relative rows get nothing. The honest answer for those is an
empty cell: this rule looks one and two bytes back and there is nothing there
to name. What to *do* about them is a separate question, and a name for one
would need the per-row anchor score this issue deliberately left off an
18,555-row file for a tie-break exercised on 7 of 18 sites.

**The tie-break is exercised on 7 of the 18** (#54's) and on 337 paged / 562
relative / 319 absolute rows corpus-wide. That is why there is no fifth
`earlier_frame_onto` column carrying the candidate's anchor score: the evidence
for the choice belongs in the test and here, not on every row.

## The blind spots

The column is a candidate generator, not an adjudicator, and there are three
things it cannot do.

**It fires wherever any byte precedes a paged-shaped byte inside a longer
instruction.** That is the mechanism it is built on, and it is why the column
is populated on 3,089 of the 3,481 paged rows rather than only on the 18
`#54` read by hand: the rule does not know whether the record it found is the
one a human would draw, only that one is available. #54's 18 are a set this
rule re-derives, not a set it was told.

**It cannot see data.** The `0x055DC` case in `bank-call-audit.md` §2 is a
dense table of 16-bit addresses starting at `0x55A8` that converges at 23 of
24 without being framed correctly — a dense table converges because *any* walk
through uniform-length entries resyncs. A candidate can sit inside such a table
and the column will name it without complaint, because the column has no way to
know it is looking at a table rather than at code.

**A name is not a verdict.** No `phantom`/`genuine` column is added, no
`status:` in `registers.yaml` moves, and no sentence anywhere claims the EC
executes any of this. The column says *a record is available here*; whether it
is the right one is what #54 settled by reading bytes, for 18 rows, and what
nobody has settled for the other 3,071 paged rows this column names.

## What was checked, and what it costs

`[ec/tools/test_earlier_record_column.py`](../../ec/tools/test_earlier_record_column.py`)
pins the column against `ec/firmware/GMxMGxx_11.800` rather than against a
regenerated CSV — the reason `test_paged_trampoline_framing.py` gives for not
re-running `audit_call_targets.py`: re-running the scan would assert the tool
against itself and let a regenerated census disagree with the image. It reads
the committed CSVs for the *counting* claims — row counts, the cost of each
alternative rule, the empty-cell case — and never for the column's correctness,
which is re-derived from the image every time. It holds
all 18 of #54's owners, transcribed rather than imported; enumerates the 7
two-candidate sites with both halves named; asserts each of the three losing
rules to fail, and holds the per-family cost of each against the committed
census; checks the non-circularity skip against a real census row (`0x01038`,
whose only candidate is itself an `ajmp`) as well as on a built fixture; and
checks that nothing downstream moved — all three row counts, one known row per
family with every pre-existing cell named, and each writer's own emitted header
run against the committed file's, so a column inserted in the *middle* of a
writer is caught rather than sliding every later column along by one.

`--self-test` in `audit_call_targets.py` gains the three column cases on a
scratch buffer, so the tool is self-checking without a gate. It is not in
`.github/scripts/agent-gates.sh` and this change does not try to put it there:
[issue #1094](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1094) owns
getting `--self-test` into a gate, and `.github/` is out of this repository's
agent reach by construction.

### Two consequences outside the tool, which is why they are named here

Adding a column to `bank-call-targets.csv` is not a one-file change, and
`test_data_regions.py` is where that was written down before this issue ran
into it. `build_ec_decompile.py` holds a hard-coded `CALL_TARGET_COLUMNS` list
asserted by its `--self-test`, which runs in the cheap gate, so the list gains
`earlier_record` too. And `test_bucket_c_codemap.py` builds a census row by
hand to run `write_csv()` against, so its fixture gains the key — it would
otherwise raise `KeyError`, which is the cheap direction to fail in.

Two documents quote a whole row of `bank-call-targets.csv`, and the two are
treated differently because they are not the same kind of thing. The
`sed -n '5766p;4420p'` block in
[`bank1-e582-entry-framing.md`](bank1-e582-entry-framing.md) is a transcript:
it is left as the record of the rows as they were read, which is what a
transcript is, and the surrounding discussion still holds. The quote in
[`citation-gap-scan.md`](citation-gap-scan.md) is prose, and is brought up to
date with the empty `earlier_record` field — a row quoted in prose is evidence
a reader is meant to be able to `grep` for, and one that resolves to nothing
is not evidence.

## Out of scope, and deliberately so

- **Deciding any site.** The column names a candidate; no row is adjudicated
  and §1's upper bounds stand.
- **The 392 empty paged rows** and the relative/absolute equivalents.
- **The `0x055DC` dense-table case**, which the column cannot tell from code.
- **`FUN_CODE_1706`** (#54's other follow-up) and listings for the three gap
  sites. Retiring a function entry needs `--mode rebuild-project`, and two
  branches that both rebuild the 7 MB EC database cannot merge.
- **`.github/workflows/`, `.github/actions/` and
  `.github/scripts/agent-gates.sh`** — the pipeline's token has no `workflow`
  scope.
- **Submitting anything upstream.** That is a human's change under
  [issue #10](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/10), and
  this work does not end at an upstream contribution anyway.
