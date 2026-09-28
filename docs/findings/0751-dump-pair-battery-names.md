# The 0x0400 pair's "other" bucket, on a mover the capture recorded (issue #219)

The write-up for [issue #219](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/219),
which found two things wrong with the `other addresses that differ` bucket of
`grade_0751_isolation.py`'s whole-block read on the `0x0400-0x045F` pair: its one
committed demonstration moved a byte no capture has ever recorded moving, and it
printed that byte — and every other byte on the page — as an address and nothing
else. This is a fixture and a report change: **no EC was read, no capture was
re-read, no `status:` in `ec/annotations/registers.yaml` moves, and nothing here
is a claim about what any register does.**

---

## The fixture's mover was a byte the evidence says is static

`ec/tools/testdata/0751-isolation-run/2026-01-01-0751-isolation-a0-{before,after}-0400.txt`
differ at exactly three addresses: `0x0402`, `0x043E`, `0x044F`. The two
temperatures are `CONTEXT`, so the bucket's sole demonstration rested on `0x0402`
— the low byte of `BAT_DESIGN_CAPACITY`, `present-untested`, and the one address
in that file set no committed capture has ever recorded moving.

`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` is the only committed
capture of this page, and `ec/annotations/xdata-0400-045f.md` §8 tabulates what it
found there: six bytes moved, the two busiest `0x044C` and `0x0449` in constant
jitter in both directions, and the quietest `0x0438`, which moved once, from
`0x97` to `0xAE` at 23:03:49. `0x0402` is in none of the six, and no second
committed capture of the page exists. So the one demonstration of this bucket was
an invented mover in a report whose job is to be the mechanical first pass, and
nothing about the output would have told the operator so.

**`0x0438` is now the mover**, taking `0x97 -> 0xAE` from the capture's one row for
it (23:03:49). Both `CONSTRUCTED INPUT` headers say what that means and only that:
the *address* is one the capture recorded and the *values* in that row are the
capture's, while every other byte in the file is still invented. `0x0439`, the
high half, stays `0x00` because the capture has no row for it and the fixture has
no other source for the byte — which is the same treatment `0x044F` has always
had beside it.

`0x0402` is **removed** from that fixture's run set rather than kept alongside.
Keeping it would have kept the defect: a second mover in the bucket, still
invented, still indistinguishable from the real one in the output.

## What the capture establishes, and what it does not

Worth being exact, because the fixture change leans on it.

**Established:** that `0x0438` moved, once, from `0x97` to `0xAE`, at 23:03:49 on
2026-09-18, in a run where the vendor service was cycling the three battery
modes. That is a fact about a capture, and the fixture now rests on it.

**Not established:** that `0x0438` moves because `0x0751` was written, or moves
during a §3 block at all. The capture was a profile-switch sweep, not a §3 run,
and this change did not perform one — no physical machine is reachable from this
pipeline, and no result that would need one is claimed anywhere below. The §6
sentence added alongside this says *expected*, and grounds it in the capture and
in what step 3 asks of the load, not in a bracket any run has produced.

And the assembled reading the tool now prints is arithmetic on the fixture's own
two bytes, not a battery voltage. §6's `0x0400` pair reads `0x0097 -> 0x00AE`,
which is `151 -> 174 mV` and is nonsense as a terminal voltage precisely because
`0x0439` is zero there. The headers say so; the test asserts the figure so that a
future reader who changes the fixture has to notice.

## The report names them, and assembles the pairs

`XDATA_NAMES` is a module-level table beside `CONTEXT`, transcribed rather than
read from `ec/annotations/registers.yaml` for the reason `CONTEXT` is
transcribed: this is a report an operator runs against a capture and two dumps,
and it takes no repository file as an input, so there is no path by which it
could read the YAML. Six entries — `0x0434`/`0x0435` `BAT_CURRENT_MA`,
`0x0436`/`0x0437` `XDATA_0436_PAIR`, `0x0438`/`0x0439` `BAT_VOLTAGE_MV`, and the
single bytes `0x0448`, `0x0449`, `0x044C` — each with the unit its assembled
reading would be in, and each with the bank1 routine that derives it where
`registers.yaml` records one.

The issue offered two readings: names at minimum, or "the 16-bit values
`registers.yaml` defines". The fuller one was taken, because the issue's own
argument is that splitting a byte pair across two rows leaves a subtraction for
the operator to do by hand in the one report meant to save the hand work. Both
halves of a named pair are already in `common` whenever the low one is, so the
high byte's *unchanged* value is a byte the section had already read — the
assembly is arithmetic on existing input, not a widening of what is compared. A
pair whose high half one of the two dumps does not reach is skipped rather than
guessed, because `common` is the intersection and that case is a coverage gap
the section already prints.

**Six entries, not forty.** `registers.yaml` names about fifty addresses on
`0x0400-0x045F`. The six here are the battery's own bytes, and the reason is
`registers.yaml`'s: they are what a fixed load moves, and §3's main arm holds
one. An address the table does not cover prints exactly as it did before this
existed — a bare `0xNNNN` on the flat list, nothing under it — and
`test_the_other_bucket_names_a_byte_and_assembles_its_pair` pins that with the
`0x0751 0x0796` bucket, so the naming stays an aid rather than becoming a claim
that every address on the page has a name.

### The one name withheld

`0x0436`/`0x0437` prints the placeholder and **not** the name upstream gives it.
`registers.yaml` records `EC_ADDR_BAT_REMAIN_CAPACITY` and declines it: in the one
committed capture of this page the low byte steps by exactly `+0x14` every ~35 s
while the high byte never moves, which reads as a periodic counter and not as a
charge level. The report prints the placeholder, says no unit for the assembled
value, and prints the reason in full — who proposed the name, what refutes it,
and that the live read that would settle it is [#172](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/172)'s
and has not been run. Printing the name would put a claim this board has already
retracted into the output an operator acts on.
`test_the_unnamed_pair_prints_the_placeholder_and_not_the_name` asserts its
absence over the whole report, not just the line.

### The shape, and why `differing_addresses()` was not taught a new one

`differing_addresses()` recovers the report's differing-address set by reading the
line **immediately after** the `other addresses that differ` heading and nothing
else, and holds it equal to `dumped_change_addresses()`. That equality is the
issue's own criterion — the cross-check has to fail on an edit to either side of
the fixture — so the flat address list stays on its own line, and the names and
assembled readings go on lines **under** it. A name or a `0x0438/0x0439` partner
spelled on that line would be read as a differing address and break the check.

That is a decision, not an accident: putting the names beside the addresses is the
more natural shape, and it would have cost a second edit to a 4,700-line shared
file to teach the helper the new form. The lines under are also the shape
`report_window`'s context section already uses — a named line at six spaces and
its values at eight — so the output reads as something the rest of the report
already does.

`differing_addresses()` is unchanged, and the half-edit property was checked by
hand: editing the CSV alone (moving the row to `0x0439`) fails two cases, editing
the after-dump alone (putting `0x0438` back to `0x00`) fails one, and restoring
both is green.

## A pair built for the entries §6's set cannot reach

`ec/tools/testdata/0751-isolation-example-moved-battery-{before,after}-0400.txt`
is new, and it exists because §6's own `0x0400` pair cannot test the assembly.
With `0x0439` at `0x00`, `0x0097 -> 0x00AE` is what a little-endian assembly and a
zero-padded low byte *both* print, so a fixture with a zero high byte cannot hold
the claim. This pair moves all three named pairs with a non-zero high byte and
the two ÷100 quotients and `0x044C` beside them, so every entry in the table is
reached by a committed fixture.

It is the same construction the three existing example pairs use — a copy of the
`0751-isolation-run` page with the smallest edit that reaches a branch §6's own
fixtures cannot — and it sits outside `0751-isolation-run/` for the same reason
they do: `test_section6s_file_list_is_the_fixture_set` holds §6's ten file names
and that directory equal, and §6's command line is unchanged by this work. The
`2040 mA` and `16021 mV` it carries are the two live figures `registers.yaml`
records for this board, and the `0x0448`/`0x0449` values are those two divided by
100 as the bank1 writers it names would divide them — so the page is internally
consistent with the annotation's account of the wiring, while every value in it
is still invented, because the annotation records the wiring and not a reading.

### Where the new cases are, and why it is not beside the reader each one exercises

`OtherBucketNameTests` is at the **end** of `test_grade_0751_isolation.py`, and
`PAIR` is one of its class attributes, while the module's other fixture pairs
sit in a shared block near the top. That is a placement decision and it is worth
reading as one.

Dozens of lines of that suite are cited by line number from the write-ups under
`docs/findings/`, and `census_test_line_pins.py` classifies every target line as
a header, an assertion, a comment or prose. An insertion anywhere above the last
cited line therefore moves those citations onto a different line **and onto a
different class**, and `test_census_test_line_pins.py` — which asserts that split
as today's figures — goes red over a change that never edited it. The failure
arrives as a bare `AssertionError: {...} != {...}` in a suite about line pins,
on a branch whose whole subject is a report's wording.

The two responses are to re-point the citations and re-derive the split, or to
put the new material where it moves nothing. The first is what this repository
has done before, and `test_census_test_line_pins.py` carries a long history of
it: one paragraph per re-anchoring, each another entry in the shape the
`no-append-logs` rule was written about, and each another line a concurrent
branch has to touch. The second costs one class sitting away from its siblings.

**Appending was taken, and the pin census is byte-identical to the tree this
branch started from** — measured, not assumed. A case added to `GradeTests`
would have been better placed and would have left four other agents' write-ups
citing lines that no longer say what they claim, until somebody re-pointed them.

## What this does not establish

**Nothing about the machine.** Every input is a hand-written fixture or a
committed capture read for which bytes it recorded moving. No EC was read, no
register was read back, and the six named bytes stay `present-untested` in
`ec/annotations/registers.yaml`. The report's new text is a name and two bytes
out of two files; it grades none of them, and the heading still says *not graded
here* in the same words as before.

**The §6 sentence is an expectation.** It says what the `0x0400` pair's bucket is
expected to contain on a real run and why those bytes are the load registering
rather than a result. It is grounded in the 2026-09-18 capture and in step 3, and
in no observation of a §3 bracket.

**`0x0436`/`0x0437` is still not settled.** This change prints the placeholder
because that is what the evidence supports. Whether the pair is a capacity field
is [#172](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/172)'s live
experiment, and the tools for it are already written and unrun.

## Follow-ups

- **The windowed reader still prints no names.** `report_window`'s `other
  addresses that moved` line is the same flat list as the whole-block one, and
  this change gave the naming to `report_dump_pairs` only. The issue asked for
  the dump pair's bucket, and the two are separate code paths; naming both would
  need the change repeated there, with the same shape question on a line the
  suite's `other addresses that moved` reader also takes. Worth doing, and worth
  its own fixture — the run set's own `0x0438` row is the case.
- **The table is six addresses out of about fifty `registers.yaml` names on the
  page.** The selection is principled (§3's load) rather than complete, so a
  future byte that a load moves will need adding by hand. Whether the table
  should carry every name on the page, and what "a name for every address"
  would even mean for the placeholders, is a question this change answers only
  for the six.
- **`0x0439` could be read rather than zeroed.** §6's `0x0400` pair now prints
  `151 -> 174 mV`, which is visibly not a battery voltage. That is honest, and
  the new example pair is where a real-looking reading lives — but a reader who
  runs the §6 set will see the nonsense figure before the plausible one, and the
  headers are the only thing explaining it.
- **The pin fragility above is not fixed, only stepped around.** The next change
  that adds a case to `GradeTests` meets the same wall, and the suite still
  asserts a shape census of the whole tree. Citing a line of a heavily-cited
  test file by number, and then classifying that line, is a coupling this
  repository chose; the write-up that would fix it is about the census rather
  than about any one branch's four re-pointed citations.
