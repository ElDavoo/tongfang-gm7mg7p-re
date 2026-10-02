# §4.6's readback names the writer that cannot have moved the byte, and what is left

(2026-10-02, issue #220. Static reading of committed disassembly, the arms
CSV, the writers CSV and §4 of the procedure. No capture opened, no EC, no
hardware, no Windows, no run.)

Issue #220 asked two things of the surfaces an operator reads when a
`0x0751` write has moved back by the time the after-dump was taken: say that
the bank0 `0x8978` Fan-Boost temperature clear **cannot** be the writer on the
three values this procedure writes, and name what does remain rather than
"something". Both are text changes, to
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §4's step 4 and step 6
and to `report_readback()`'s mismatch line in
[`ec/tools/grade_0751_isolation.py`](../../ec/tools/grade_0751_isolation.py).
No `status:` moves, and nothing here is a claim about what a readback will
show.

## The gate, and the arithmetic that closes it

`0x8942` is `jnb acc.6,0x8998`. On this branch family **taken means bit clear**:
`jnb` jumps when the bit is *not* set, so the taken arm is the bit-clear path
and the fall-through is the bit-**set** one. §9.1 of
[`ec/annotations/manual-fan-ctrl-0751.md`](../../ec/annotations/manual-fan-ctrl-0751.md)
states that convention for all seventeen branches rather than leaving it to be
re-derived, and its arms table carries the consequence in the row's own two
cells:

| `0x8942` arm | start | `0x0751` in the row's XDATA |
| --- | --- | --- |
| taken (bit 6 clear) | `0x8998` | `0x0751 read` |
| fall-through (bit 6 set) | `0x8949` | `0x0751 r+w` |

The store is on one side only, and it is the side that needs bit 6 **set**.
That is the same thing the arm's own instruction listing says: `0x8978` reads
`CPU_TEMP` `0x043E`, `0x8986` reads `GPU_TEMP` `0x044F`, both against `0x46`,
and `0x898E` is `anl a,#0xbf` storing at `0x8990` — a read-modify-write
because the byte is loaded first. Read off the firmware rather than the
annotation, the gate is two instructions:

```
0x8942  900751   mov  dptr,#0x0751
0x8945  e0       movx a,@dptr        ; acc.6 is bit 6 of 0x0751 itself
0x8946  30e64f   jnb  acc.6,0x8998    ; taken when bit 6 is CLEAR
0x8949  ...                        ; fall-through: bit 6 SET
```

So:

- `0xA0` is bits 7 and 5;
- `0x10` is bit 4;
- `0x00` is nothing;
- bit 6 is `0x40`, and it is clear in all three.

The branch is taken, the taken arm runs, and the `0x8978` compare and the
`0x8990` store are not reached. This is arithmetic over three written values
and one instruction's sense — no hardware, no capture, and nothing here that a
different firmware image would not have to be re-checked against.

**How this sits beside the census's wording, which is not a contradiction.**
`0751-writer-census.md` records that `0x8990` "clears bit 6 whenever both
sensors are under 70 °C, without ever testing bit 6", and the writers CSV's
`condition` cell for that row reads `temperature-gate` with no mention of bit
6. Both are true and they are about **different gates**. The census's is the
store's own — the compare chain at `0x8978`-`0x8988`, which indeed never looks
at bit 6 — and its walk starts at the site (`0x898A`), so it never sees the
enclosing branch. This adds the gate *above* that: the block is entered only
when bit 6 is set, so the temperature test is downstream of a check that
excludes these three values. The census is left alone, because a measurement
record is not the place to add a reachability claim it did not make, and
because "not tested here" and "not reached here" are different sentences about
different instructions.

## What it rules out, precisely

It rules out **one site of one table**: the `0x898A` row of
[`manual-fan-ctrl-0751-writers.csv`](../../ec/annotations/manual-fan-ctrl-0751-writers.csv),
whose `condition` cell already reads `temperature-gate`, and which the census
write-up records as the only one of its sites gated by a temperature. It does
not rule out:

- the EC's other `0x0751` write paths — the two boot-time defaults and the
  mode-decode sites, all in the same table with their own masks and gates;
- the vendor service, which is not in that table because the table is the EC's;
- a writer no site scan found. `0751-writer-census.md` §4 is the write-up for
  those blind spots and it is **not** closed, so "not in the table" stays
  "not found by this method" rather than "absent".

So a readback that does not hold the written value is still a finding, and
nothing in this change lowers the bar for it. What changed is that one
candidate is named and excluded up front, so the operator does not spend the
run matching a value against a path the byte cannot have taken.

**The grader's sentence is conditional, and that is a correction to the issue's
framing rather than an addition.** `--wrote` takes any byte, so a value with
bit 6 set is a case `report_readback()` can be handed — and on that value the
`jnb` falls *through* and the temperature clear is reachable. A message
claiming it was ruled out regardless would be the tool asserting a static fact
that does not hold of the value it was just given, which is the overclaim
CLAUDE.md puts above every other rule. So the exclusion prints only when bit 6
is clear in the value in hand, which is every value §3 writes; a value with it
set gets the opposite sentence, naming the temperature clear as a live
candidate. The runbook's two paragraphs are scoped to §3's three values
explicitly and do not need the same branch.

**No count of writers appears in any of the surfaces this change touches**,
and that is deliberate. The census's own figure is open-ended by its own
account, so a numeral in a runbook sentence or a grader message is one every
later census has to keep right; they point at the table and at
`0751-writer-census.md` instead.

## Why §3a is the step that separates what is left

What remains is the EC's other write paths and the vendor service, and those
two are separated by exactly the thing §3a already does: the same write, the
same load, with `GCUService` stopped and confirmed gone. With the service up,
a byte that moved back may be the service re-asserting its bundle; with it
stopped and the byte still moving, that explanation is off the table and the
EC's own writers are what is left. §3a already gives both reasons and already
names the minimum pair, so this change points at it rather than restating it.

## What the temperature pair is for, and why it is not this step's input

`0x0400-0x045F` is the input to §4.5's flat-load check, which is what §6
already says the pair is for: it shows the load was flat across both capture
windows, which is the precondition §4.4's comparison needs. An operator who
pairs a **failed §4.6 readback** with that bracket is looking for a thermal
explanation, and on these three values the one thermal path is already
excluded above. The two are different questions and the runbook now says so
where the readback is read.

## The surfaces are held together by tests

`ReadbackWriterNamesTests` in
[`ec/tools/test_grade_0751_isolation.py`](../../ec/tools/test_grade_0751_isolation.py)
holds the message and the runbook to the same anchors, by **content** rather
than by line: each value gets its own case rather than a parameterised loop, so
a failure names which value lost its wording; the mismatch line must carry the
exclusion and the `0x8978`/`0x40`/annotation-path anchors; `"something"` must
be gone; and a numeral presented as a count of writers is what the `#196`
guard fails on. The runbook side is located by anchor phrase rather than by
line, and the tool side by the words the operator reads, so none of these
anchors moves when another branch edits either file — and the runbook cannot
lose its half of the claim on the next edit of the tool without a case going
red.

## What this does not establish

- **No run happened.** No `--dump` was taken, no capture opened, no EC or
  Windows machine reachable from this pipeline. §3, §3a and §6 are a human's
  work at the physical machine and this change does not touch them.
- **No claim about what a readback will show.** The message says what the
  files say and nothing further; `MANUAL_FAN_CTRL` stays `present-untested`
  and `ec/annotations/registers.yaml` is not edited.
- **One firmware image.** `GMxMGxx_11.800`. A different image can gate that
  store differently, and the sense of `jnb` at `0x8942` is what this rests on.
- **A negative is not an absence.** "The `0x8978` clear did not run here" is a
  statement about a path and the three values in §3, not a statement that the
  EC has no other temperature-gated writer. `0x93CA` and `0xB73C` read the same
  two temperatures, as §9.3 records, and what they do with them is not settled
  by this.
- **The count is not closed**, and nothing here moves it. `0751-writer-census.md`
  §4 owns that gap and issue #34 owns the blind spot under it.