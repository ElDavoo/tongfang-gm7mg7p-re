# The listing instruction census, and the readers that have to agree on it

Issue #775 was filed against a red `verify_gap_text.py --self-test`, and the
cause was `EXPECT_CHECKED` — a hand-kept count of the whole instruction stream
in that tool's own source. The count it quoted had not moved with the listing
set, so `--self-test` had been red since the export at #229's base without any
gate noticing; `verify_gap_text.py` says so of itself beside the comment that
explains the constant's removal, and that is where the history is recorded
rather than re-derived here.

Two things about that turned out to be settled before this write-up was
written, and one was not. The pin is gone: `#1498` removed `EXPECT_CHECKED`
and derived the re-encode's reach from the committed report instead, which is
why both modes exit zero now. What was still missing was the thing underneath
the pin — a test that runs the two modes, so a listing edit that moved either
of them is red on the commit that moved it rather than on the next human who
remembered to look. `ec/tools/test_verify_gap_text.py` is that test.

## The finding: the committed listings hold 45,661 instructions, and the readers of them agree

`verify_reassembly.parse_listing()` and `opcode_coverage.parse_listing()` are
two implementations of the same rule, written for different purposes and
sharing no code. Both find a listing's byte column the same way — walk the
fixed-width slots, stop at the `-` padding or at a token that is not a byte —
and then part company. `verify_reassembly.parse_listing()` goes on to read the
mnemonic after the padding and drops a row that has bytes but no text;
`opcode_coverage.parse_listing()` never looks at the text and keeps the row.
So the two could disagree on a listing shaped like that, and there is none.

They are the two the census figures rest on, which is not the same as being the
only two that read a `.asm` file, and this write-up does not claim they are.
More than one other module reads the same column by a rule of its own:
`merge_annotation_shards.parse_listing()` slices the three columns at fixed
offsets instead of walking the slots; `counter_sweep_entry.read_listings()`
takes the byte column out of a single `LINE_RE` and keys it by address, and the
two `pd` tools each carry their own copy of that regex, in
`pd_entry_forms.read_listings()` and `pd_no_ret_fallthrough.read_listings()`;
and `citation_callers.transfers()`, which `call_graph.parse_listing()` reaches
for, is a fourth grammar again, though it yields transfers rather than
instruction rows and so has no whole-listing sequence to be compared on.

`opcode_coverage.listing_rows()` exists precisely because a reader that quietly
reads a third of a file reports no disagreement and looks like a pass, and that
is the reason to name the others rather than their number: none of them feeds
the census, and every one of them could disagree about how many instructions a
listing holds, which is the disagreement that would move a figure.

On the committed tree they agree on every listing, on every row: the same
addresses, the same bytes, in the same order. That is 45,661 instructions
across the listings `ec/decompiled/listing-index.csv` names.

```
$ python3 ec/tools/opcode_coverage.py --coverage --summary | grep 'instruction starts'
  instruction starts              45661
$ python3 ec/tools/verify_reassembly.py --check | head -1
  listing bytes: 45661 instruction(s) checked against the firmware, 0 disagreement(s)
```

`opcode_coverage.py`'s docstring said 45,643 — 18 short, the growth of listings
seeded since. Its own tool prints 45,661 while carrying 45,643 in the
docstring describing it, which is the shape of the bug the issue is about: the
figure a reader checks is not the figure that moved.

`test_verify_gap_text.py::CensusTests` holds each whole-listing reader to the
census reader, comparing full `(address, bytes)` sequences per listing rather
than counts, so a reader that dropped a row and invented another could not pass
it. The shard reader is compared on `(address, mnemonic)` instead, because it
reports no byte column and pretending to a three-column agreement it cannot
make would be the same overclaim in a test. The three `LINE_RE` readers are held
to each other as well as to the census, because
`pd_no_ret_fallthrough`'s docstring claims they cannot disagree and nothing had
ever compared them.

## Why a percentage hid all of it

45,500 of 45,643 and 45,518 of 45,661 are both 99.69%. Every coverage sentence
in the tree rounds to the same two decimal places at either end of the chain, so
a reader who checks the percentage sees nothing wrong at any point along it.
This is the general shape CLAUDE.md's calibration rule is about, in a place
where it is easy to forget: the number that gets read is the one that was
chosen to be robust, and the one that goes stale is the one underneath it.

The gap-text tool's own figures are unchanged by any of this, and are worth
restating as the live pair rather than as a chain:

```
$ python3 ec/tools/verify_gap_text.py --check
  gap text bytes: 143 instruction(s) compared against the firmware
  gap text: 143 instruction(s) in 84 row(s), 5 form(s); 45518 of the 45661 instructions translated to sdas8051 source
  and the re-encode reached at most 44816 of those 45661 against the firmware
  image -- a ceiling, not a measurement: 702 instruction(s) sit in rows whose assembled listing
  carried no entry at all, and a further 4 row(s) stopped part-way through, so the
  real figure is lower again and this file cannot say by how much.
  gap text verdicts: 143 agree
  all checks passed
```

143 of the stream are instructions `to_sdas()` declines — five forms
(`ajmp`, `acall`, `mov <bit>,CY`, `cpl <bit>`, `djnz A,`) that `sdas8051` either
refuses or encodes differently from the manual — and those are cross-decoded
from the firmware image by `disasm8051.py` instead. The re-encode's *reach* is a
lower and different number again: at most 44,816 reached a byte comparison,
which `reassembly_checked_bound.py --check` prints as a ceiling rather than a
measurement, and which is the figure a coverage claim should quote.

## What the issue asked for that was already done

Recorded so the next reader does not re-derive it, and so the diff is not read
as having done it:

- **`EXPECT_CHECKED` re-derived.** Not applicable: `#1498` deleted the constant
  and the comment beside it says why. The reach is now derived from the
  committed report by `reassembly_checked_bound.py`, which is the fix the issue
  was reaching for and the right one — a hand-kept total of a corpus that every
  seeded listing moves is a figure that is wrong between the seeding and
  whoever notices.
- **`--check` green.** It was not, at the base this was planned against: one
  `row_name` cell in `ec/ghidra/gap-text-check.csv` still named
  `FUN_CODE_0d7b` for a function the listing index had renamed to
  `divide_down_scheduler_counters_44_45_47`. It has since been regenerated and
  is green. `test_verify_gap_text.py::ReportJoinTests` now drives that failure
  deliberately, in both directions, so the check is known to have teeth rather
  than known to pass.

## Every committed site still quoting a figure from this chain

Two numbers move together in this chain and the sites below quote one or the
other, which matters because the reason each stands is not the same for both.
**45,661** is the listing instruction census, printed by
`opcode_coverage.py --coverage --summary` and by `verify_reassembly.py --check`.
**45,518** is how many of those `to_sdas()` accepts, printed by
`verify_gap_text.py --check`. Files already at the live pair are not listed
here, having nothing stale left to say. A site is listed once, against the live
claim it makes: §11's row below covers the chain narrative that explains how
45,537 became 45,643 as well as the 45,500 the section states, because that
narrative is a record of a movement rather than a claim about the tree as it is
now.

| site | reads | live | disposition |
|---|---|---|---|
| `ec/tools/opcode_coverage.py` docstring | 45,643 | 45,661 | corrected here |
| `ec/README.md`, the `--divergence` sentences | 45,643 | 45,661 | corrected here |
| `ec/tools/verify_gap_text.py` `check()` comment | 45,537 | stated without a number | corrected here |
| `docs/findings.md` §11 | 45,500 of 45,643 | 45,518 of 45,661 | translation count |
| `docs/findings.md` §11a | 45,481 of 45,624 | 45,518 of 45,661 | translation count |
| `docs/findings.md` §13 | 45,481 of 45,624 | 45,518 of 45,661 | translation count |
| `README.md` | 45,481 of 45,624 | 45,518 of 45,661 | translation count |
| `ec/README.md` | 45,481 of 45,624 | 45,518 of 45,661 | translation count |
| `ec/ghidra/README.md`, outside its transcripts | 45,500 of 45,643, and a bare 45,643 | 45,518 of 45,661, and 45,661 | translation count |
| `docs/findings/disasm8051-self-test-gate.md` | 45,394 | 45,518 | translation count |
| `docs/findings/opcode-table-coverage.md`, its prose | 45,643 | 45,661 | census figure |
| `docs/findings.md` §14h and §19 | 45,624 | 45,661 | census figure |
| `ec/annotations/subsystems.md` | 45,624 | 45,661 | census figure |
| `ec/annotations/xdata-register-map.md` | 45,624 | 45,661 | census figure |
| `ec/ghidra/README.md`'s `--report` and `--check` transcripts | 45,500, 45,643 and 45,537 | — | dated transcript |
| `docs/findings/opcode-table-coverage.md`'s `--coverage`, `--divergence` and `--check` transcripts | 45,643 | — | dated transcript |
| `docs/findings.md` §14f, §14g and §14h — the assembler-comparison table and the accounts of the race | 45,394 of 45,537 | — | dated record |
| `ec/tools/verify_reassembly.py`'s version-comparison docstrings | 45,394 of 45,537 | — | dated record |
| `evidence/ec-reencode/2026-09-23-sdas8051-versions.md` | 45,394 of 45,537 | — | dated record |
| `08b72e2`'s own commit message | 45,394 | — | dated record |

**The three corrected here** are the two sites this diff was already editing —
the docstring of the tool whose figure it is, and the README sentence that
describes that tool — plus this tool's own comment. That comment lost its
figure rather than gaining a fresh one: it said what `check_listing_bytes()`
covers, which is every instruction in the listings, and the tool's own docstring
already says that without a number.

**Translation counts stand** because each one is superseded on its own terms
before this diff reaches it. They count what `to_sdas()` translated and handed
to `sdas8051`, which is not what reached a byte comparison, and every site in
that group either carries #229's correction beside it or is superseded by the
one §11 does carry. `docs/findings.md` §11 is the canonical statement and its
correction chain already runs 45,537 → 45,624 → 45,643 in the file's own
parenthetical style; appending a fourth link is the correction chain CLAUDE.md
forbids, a number in a document nobody can edit appended at one spot by every
branch, which is what makes the file a merge conflict as well as a stale one.
What is bounded instead is the ceiling `reassembly_checked_bound.py --check`
prints, and `verify_reassembly.py` already says in its own docstring that the
committed CSV "is the one to read for the tree as it is now". Restating the
figure in another place would re-arm exactly the trap `#1498` removed the pin to
close. `docs/findings/disasm8051-self-test-gate.md` is the one site in the
group with no correction beside it: it asks whether twelve particular
instructions are inside the number, which the ceiling does not answer, so
correcting it is a separate piece of work and naming it here is what stops a
reader concluding it was checked and cleared.

**Census figures stand** for the other reason: correcting them coherently is a
tree-wide migration across several shared files, and it goes stale again on the
next seeded listing row. That is the `tools/README.md` failure mode CLAUDE.md
documents, and `docs/findings/opcode-table-coverage.md` is the sharpest case —
it is the write-up for the very tool whose docstring this diff edits, and its
lead claim is the same stale number the diff corrects three files away.

**Dated transcripts stand** because the other figures in the block come from
the same run. Editing two digits inside one produces a transcript of no run at
all.

**Dated records stand** because they were true when measured: the 2026-09-23
assembler comparison, and the text of `08b72e2`'s own commit message.

## What this suite holds, and what it does not

It runs `--self-test` and `--check` as subprocesses over the committed tree, so
what is tested is the exit code a reader gets rather than the functions behind
it; drives each of the five decline predicates through `cross_listing()`, the
path `--check` uses, on a synthetic listing and a synthetic image; checks that
an exclusion no predicate explains reaches `unclassified` and is given no
verdict; drives the `row_name` join and the dropped-row case so a failure is
shown to happen before one is shown not to; and holds the readers of a listing
to the census reader, one case per reading rule, so the agreement above is
checked on every commit instead of being a sentence.

It does not hold `citation_callers.transfers()`, which is named above as the
fourth grammar. It yields transfers rather than instruction rows, so there is
no whole-listing sequence to compare and the honest check would be a subset
test that says less than the other three do.

It does not add `--self-test` to the cheap gate. `.github/` is copied from
`ElDavoo/agent-pipeline` and a change to it is an upstream edit and a re-copy,
so a gate call is a human's; `docs/ci/agent-gates-gap-text-check.patch`
(prepared by #745, not landed) wires `--check` only, and
`docs/findings/prepared-gate-patches.md` is where a `--self-test` arm belongs.
Until that patch is applied, `tools/run-tests.sh` is the route that needs no
`git apply` and no human, which is why the suite carries both modes.

No assembler, no Ghidra, no hardware and no network: both modes need none of
them, and the synthetic listings are decoded by `disasm8051.py` rather than by
anything installed.