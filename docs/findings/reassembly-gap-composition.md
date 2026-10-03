# What is in the instructions sdas8051 declines, derived rather than recalled

`docs/findings.md` §14g closes with its own remaining question: "What is *not*
claimed for it: no committed check recomputes it. `--check` prints the 143 and
not what is in it, so this is a measurement made while writing the
correction." The composition it measured — 74 `ajmp`, 36 `acall`, 19 `mov
<bit>,CY` (0x92), 13 `cpl <bit>` (0xB2), one `djnz A` — was carried forward as
prose into §11, §14g, `ec/ghidra/README.md` and a docstring in this tool,
none of which recomputes it. It is now derived by
`python3 ec/tools/verify_reassembly.py --check`, which needs no assembler and
no Ghidra, and the number it prints is compared against the committed report's
own column rather than trusted.

```
$ python3 ec/tools/verify_reassembly.py --check
  listing bytes: 45661 instruction(s) checked against the firmware, 0 disagreement(s)
  unchecked 143, by the rule that declined each:
    GAP_MNEMONICS ajmp             74  ajmp
    GAP_MNEMONICS acall            36  acall
    BIT_UNSUPPORTED 0x92           19  mov
    BIT_UNSUPPORTED 0xB2           13  cpl
    GAP_FORMS "djnz a,"             1  djnz
  and the refusal rules no instruction here reached: GAP_FORMS "addc c,#", GAP_FORMS "anl c,#",
  GAP_FORMS "mov c,#", GAP_FORMS "orl c,#", GAP_FORMS "subb c,#", GAP_FORMS "xrl c,#",
  BIT_UNSUPPORTED 0xC1, branch displacement out of range, CJNE direct operand
  which is the same total as the report's instructions_unchecked
```

## §14g's sentence was close to true, and the difference matters

§14g says no committed check recomputes the composition. A committed tool did:
`ec/tools/verify_gap_text.py` walks the same listings through the same
`to_sdas()` and prints the same five figures under different labels — grouped
by *predicate* alone, so `GAP_MNEMONICS ajmp 74` rather than `74 ajmp`. Its
`--check` prints the total and the form count; `--report` prints the
breakdown. **Nothing that runs calls either.** Its wiring into a gate is the
prepared patch `docs/ci/agent-gates-gap-text-check.patch`, which is a human's
`cp` and stays unlanded.

So the finding was not "no tool can compute this" but "the tool that computes
it is not in a gate, and the tool that is in a gate does not compute it". That
is what decides where the replay goes: `verify_reassembly.py --check` is in
`.github/scripts/agent-gates.sh` already, so putting the derivation there costs
no gate edit at all. It also means the composition and the count it is printed
beside come from the same walk, which is the property that makes the comparison
below mean something.

Grouping by predicate rather than by mnemonic is the discriminator the tool
actually decides on, and the two group differently here: `clr 0x8e` is `CLR
direct` and `CLR bit` depending on the byte in front of it. Both halves are
printed, so the grouping does not hide a mnemonic behind a rule.

## One enumerator of the decision order, not two

`verify_gap_text.why()` was a second implementation of `to_sdas()`'s predicate
order, kept beside the collections it read (`GAP_FORMS`, `GAP_MNEMONICS`,
`BIT_UNSUPPORTED`) rather than beside `to_sdas()` itself. It is now a
delegation to `verify_reassembly.refusal_reason()`, which lives directly after
`to_sdas()`. A second enumerator of a decision order is how two files come to
disagree about which instructions are refused; the reason strings themselves are
unchanged, so `ec/ghidra/gap-text-check.csv` is byte-identical and that file's
`--check` and `--self-test` are unaffected.

`refusal_reason()` returns the rule names `verify_gap_text.py` has always
written into the CSV's `reason` column, so the move did not have to rename
anything. `refusal_rules()` enumerates that vocabulary from the same
collections, so a form added to `GAP_FORMS` is in the "no instruction here
reached" line the moment it is there rather than whenever someone remembers.

**`reserved \`da A\`` is not one of those rules, and the distinction is not
cosmetic.** `to_sdas()` *translates* the 8051's reserved no-op (`da A`,
opcode 0xD4) into `da a` and emits `D4`; it is the one form the tool repairs
rather than declines. `refusal_reason()` can still name it, because the
predicate sits in `to_sdas()`'s order, but a rule no refusal can carry must not
be enumerated as one — the "rules with no instance" line would then report the
reserved no-op as a gap in the firmware, which is the inverse of the truth.
Both halves are asserted in `--self-test`.

## Why a replay rather than a column on the report

The alternative — `check_one()` recording *every* form it refused, so the
report could be summed — was rejected for three mechanical reasons, not for
style. `check_one()`'s tuple shape is what `write_report()` writes from, so
every refused form on the 84 rows holding the 143 would need a new column or a
widened `detail` cell, naming every affected row. `tools/check_deep_schedule_emit.py`'s
`header_coupling()` holds `emit_csv()`'s header **byte-identical** to the
committed report's, so a new column breaks a hold for no gain. And
`check_listing_bytes()` already parses every listing: the tally is accumulated
in that existing loop, off that existing parse, so the cost is no second walk
of the `.asm` files — the `#138` invariant the function's own docstring names
("a second pass here to collect a hash would give it back") is the reason and
not an afterthought.

The composition is a property of the listings and the rules, not of the report
artifact. `ec/ghidra/reassembly.csv` keeps its columns and its single writer.

## What the cross-check is, and what it is not

The composition is *printed*, not asserted against a literal: the five forms
and their counts move with a listing export, and a hand-kept figure would be a
value every merge has to touch. What is asserted is the **total**, against the
committed report's summed `instructions_unchecked` column — two derivations of
the same listings, one through the decision order and one through the CSV
written from it, that have to agree.

That is the part that can fail, and it fails by naming both sides:

```
  FAIL the replay refuses 143 instruction(s) and the committed report sums to 142.
       One of the two moved: the listings, the rules, or the report. The composition above
       does not describe the report, so do not read it as the report's.
```

A listing edit that changes which forms are refused, a rule added to
`GAP_FORMS`/`BIT_UNSUPPORTED`/the `CJNE` rule, and a stale report each move one
number and not the other. Verified by driving each: decrementing one cell of
`instructions_unchecked` in the committed report fails the check; adding
`0xA2` to `BIT_UNSUPPORTED` moves the replay total to 156 and fails it too, with
`--self-test` going red independently on the vocabulary assertions. Without the
comparison the tool would print a plausible wrong number with a confident tone,
which is the failure §4 is about rather than a solution to it.

`--self-test` pins the arithmetic on a synthetic listing holding one of each of
the five forms *plus* `CLR bit` (0xC1) and a `CJNE` on a direct address — the
two forms the committed image exercises none of, so a change to either moves a
test rather than a paragraph. What that listing does not reach is asserted as
the complement: the carry-with-immediate forms and the out-of-range branch.
Both assertions are about a listing the test builds, so a listing export that
adds a function does not redden them.

## Calibration

**This does not make the 1:1 claim 100%, and it does not narrow any ceiling.**
`sdas8051` still cannot express those five forms, so the 143 are still excluded
from the re-encode; what changed is that what they *are* is now derived instead
of remembered. `verify_gap_text.py` is what covers them, by asking
`disasm8051.py` to decode the same bytes rather than asking the assembler that
declined them to encode them back. Verifying those instructions against
something other than the assembler that declined them is issue #151's subject
and is untouched here.

Two things this write-up does not restate, deliberately. §11 and §14g already
carry the corrected composition and both are frozen by
`check_findings_frozen.py`; they were right and needed no edit, which is
CLAUDE.md's "prose updates follow the number, not the reverse" with the number
not moving. And `check_listing_bytes()`'s docstring still says 143 of them are
unchecked in the committed report — that figure is the point of the sentence,
and it now has a line beside it that derives it.

`ec/tools/verify_gap_text.py --check` and `--self-test` remain the check on the
143's *text*: two decoders reading the same byte column, one of which is
`disasm8051.py` and shares no code with Ghidra's SLEIGH. This change derives
which forms were refused; that one verifies they are written correctly. They
are different questions and neither answers the other.

One stale figure is recorded here rather than corrected in place: §14g and
`ec/ghidra/README.md` both give a row count for
`ec/decompiled/listing-index.csv` that this walk does not reproduce, because the
index has grown since and the walk reads only its usable rows. Fixing prose
inside a frozen section is not this issue's change, and it would put two more
hunks in shared files for a figure that is a census of a file rather than a
property of the firmware. The command above prints what it actually read.