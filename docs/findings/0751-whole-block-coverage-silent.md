# The whole-block read said nothing when a dump-pair range reached no byte, and a reader copying two `--dump-pair` flags got no warning (issue #218)

(2026-10-03, issue #218. The grader run over the committed fixtures in
`ec/tools/testdata/0751-isolation-run/`. No EC, no hardware, no Windows
machine, no capture opened, no procedure run.)

Issue #218 was opened from #205, which grew §6 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` from two `--dump-pair`
flags to three. The review of the first attempt at it found the change
off-mission: it re-aligned two module docstrings with §6 and added a test that
they agreed, which moves nothing about the firmware. Correct, and not the
mission — the same standard `CLAUDE.md` states, that work is judged by whether
it moves a component closer to understood rather than by whether the issue's
wording was met.

Re-planned onto the question the issue was pointing at. **The docstring defect
was real and load-bearing, and it is not what made it off-mission:** the
grader's `Usage:` block is what `--help` prints (`description=__doc__`), so a
reader who copies the block as it stood got a whole-block read over two of
three ranges — silently, and with a section that read as though it were
complete. This is the finding underneath the docstring, measured and then
fixed in the tool rather than in the prose describing it.

## The defect

`report_dump_pairs` printed `not covered by this pair` for a group one pair
does not reach. That line is right, and it was the only coverage statement
there was. §6's three ranges are three pairs, so a run handed two of them
printed that line for the third range's groups under both pairs it *was*
given — every line true, the section reading whole, and nothing anywhere
saying that a group no pair reached had not been read at all.

The command as §6 writes it, minus one flag:

```
$ python3 ec/tools/grade_0751_isolation.py \
    ec/tools/testdata/0751-isolation-run/2026-01-01-0751-isolation-0700-07ff.csv \
    ec/tools/testdata/0751-isolation-run/2026-01-01-0751-isolation-0f00-0f5f.csv \
    ec/tools/testdata/0751-isolation-run/2026-01-01-0751-isolation-0400-045f.csv \
    --dump-pair ...a0-before-0700.txt ...a0-after-0700.txt \
    --dump-pair ...a0-before-0f00.txt ...a0-after-0f00.txt
```

§4.5's two temperature bytes were simply absent from the whole-block read,
under both pairs, each naming itself `not covered by this pair` — which is true
of the pair and says nothing about the run. The closing summary then printed:

> The whole-block dump pairs above were read as a second, wider bracket on the
> same §4.1-§4.3 bytes.

For §4.5 that is a bracket that was never taken, stated as one that was.

**Dropping the `0x0700` pair is the worse case, and the issue did not name
it.** `0x0783-0x0785` (§4.1) and `0x07C6` (§4.3) are *graded* bytes and live
in that page, so a run without it has no whole-block bracket on two of the
three §4.1-§4.3 groups — and §6's `0x0F00` and `0x0400` pairs reach neither.
Same shape, worse stakes, and the summary sentence is just as wrong.

## What the `0x0400` pair actually decides

Run from §6's own command block over the committed fixtures, the `0x0400`
pair is reached by **none** of §4.1-§4.3: all four graded groups print `not
covered by this pair`. Its entire contribution is §4.5's two context
temperatures (`0x043E 0x32 -> 0x37`, `0x044F 0x30 -> 0x32`), one battery
address, and nothing graded. §3b's dump bullet says §4.5's temperatures "are
in the `0x0400` pair and in neither of the others", and that is exactly
right — so the third pair #205 added buys the temperature half of §4.5 and
nothing else, and a run without it loses exactly that.

This is what the record can settle and no more:

- **Settles**: that a `--dump-pair` over the `0x0400` range is the only input
  that puts §4.5's whole-block temperature read in evidence at all, and which
  bytes on that page a whole-block bracket reaches.
- **Does not settle**: whether `0x0751` does anything. §4.6's readback is a
  `--dump` comparison and is taken from the `0x0700` pair; §4.1-§4.3 are not
  in this range; and CPU package power is in no EC sweep at all. `0x0751`
  stays `present-untested` and `ec/annotations/registers.yaml` is not edited.

## The fix

In the tool, so `--help` and every copy of the block inherit it.

**The missing half is named where a reader sees the run, not one pair.**
`report_pair_coverage` prints one line per §4 group that no `--dump-pair`
reached, naming the range to add. The range is derived from the group's own
addresses by `pages_of`, not from a table of which group lives where: such a
table is a second spelling of §6's list, and a group added to `WATCHED`
without a row in it would be named by nothing.

**Graded and context groups are named separately.** A `WATCHED` group with no
pair is a graded §4.1-§4.3 byte with no bracket at all; a `CONTEXT` group with
no pair is the temperature half of §4.5. One list would put them on the same
footing, and the graded one is what a run that skipped a range silently drops.

**Per block, not per run.** A bracket is one block's before and after, so a
run-level union would hide a short block behind a complete one: block `0xA0`
handed all three ranges and `0x10` two, and a union says `0x0400` is covered,
so `0x10`'s temperature read is never named. `covered` is reset per block
group and the notice is printed inside it, so a `--block` run says the same
thing about its block as an unscoped one does about each of its.

**The summary is scoped, not withheld.** "A second, wider bracket on the same
§4.1-§4.3 bytes" is a claim about those bytes, and it is now qualified over
the groups no pair reached. Withholding the sentence instead would make it
false about the ranges that *were* covered — trading this overclaim for a new
one.

**A refused pair is not coverage.** A pair given one file twice reaches the
address and reads nothing; it contributes no bracket, so a group reached only
by one is uncovered. `covered` is updated where the pair's own intersection is
computed, after the refusal, so this falls out rather than needing its own
rule.

## The guard

`ec/tools/test_grade_0751_isolation_pair_coverage.py`, a new suite rather
than cases appended to `test_grade_0751_isolation.py`, which is over eight
thousand lines and has collided at its last line more than once. The loader,
the runner and the §6 fixture paths are imported from that suite rather than
re-spelled — a second copy of `run` or of `RUN_BEFORE_0400` is a second answer
to the same question.

Twelve cases, each of which was checked by breaking the tool and watching the
right one fail:

| break | fails |
| --- | --- |
| the notice removed (the pre-fix behaviour) | 5 |
| `covered` made a run-level union again | 1 — the short-block case |
| the summary scoping dropped | 1 |
| `pages_of` returning a constant | 3 |

The negative cases matter as much as the positive ones: all three ranges
given prints no notice and no scoping at all, no pairs given keeps its own
one-line refusal, and a group covered by some pair is never named. A marker on
every ordinary run would be noise that gets the line deleted by the next
reader who finds it uninformative.

Prose is asserted against a whitespace-flattened copy of the output, because
the notices go out through `wrap_note` at this file's 72 columns and asserting
the wrapped form would pin the measure into every case. The per-pair and group
lines are not wrapped and are still asserted directly, since their indentation
and order are what those cases are about.

The docstring guard from the first attempt stays: it holds the `Usage:` block
to §6's own command block, so the copyable text cannot fall behind §6 again.
It is a smaller part of the change than it was, and it is a real one.

## What this does not establish

- **No run happened.** No capture was opened, no dump taken, no procedure
  executed. Every claim above is the grader's output over committed files
  under `ec/tools/testdata/`. §3, §3a and §6 remain a human's work at the
  physical machine.
- **No claim about the EC.** `0x0751` stays `present-untested`; nothing here
  says what a `--dump-pair` will show when one is eventually taken on the
  machine.
- **The fix is about the record, not the register.** What changed is what the
  tool says about which files it was handed — a claim it can support — and
  nothing about what those files mean.
- **The runbook is unchanged.** §6's command block and §3b's dump bullet were
  the source and are already correct; this reads them and does not edit them.

## Two of the issue's quotes are not in the tree

Recorded rather than quietly dropped, because the issue's readers are exactly
the people who would go looking for a stale "eight".

- **The hyphenated "eight-file" phrase the issue quotes is not in the tree.**
  The probe's docstring reads "§6's **ten** files" and did when the issue was
  filed; only the thing beside the count — what the missing files would have
  answered — was missing.
- **The grader's `Usage:` block is not at `:57-60`.** It is further down the
  module docstring. It did still show two `--dump-pair` flags where §6 passes
  three, so the finding stands and only the citation is off.