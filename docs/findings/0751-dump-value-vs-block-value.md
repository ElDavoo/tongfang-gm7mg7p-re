# A block's `<value>` came off a file name and nothing checked it against the day's own write (issue #1400)

The write-up for [issue
#1400](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1400), which is
the third member of the family
[`0751-readback-written-value-notice.md`](0751-readback-written-value-notice.md)
started and [`0751-readback-before-dump-holds-written-value.md`](0751-readback-before-dump-holds-written-value.md)
continued: what §4.6 is allowed to conclude, and what it has to check first.

**Offline throughout, and nothing here is a claim about the machine.** No EC
was read, no §3 run was performed, no laptop or Windows box was reached, and
no register was observed. Every transcript below is this tree's Python over
the committed fixtures in `ec/tools/testdata/`, whose own headers read
`CONSTRUCTED INPUT, NOT A CAPTURE`. The transposed copies are made per run into
a `tempfile` directory; nothing is committed that a real capture would not
produce. `ec/annotations/registers.yaml` is not touched by this change, and
`MANUAL_FAN_CTRL`'s `present-untested` stands for the reason its own note
gives.

## Where the value comes from

On the plain unscoped invocation §6 sanctions — "a plain invocation over them
prints every block's windows, each labelled with the block it falls in" — the
only source of a written value that exists is `dump_block`, and everything it
returns is a regex match against `os.path.basename(path)`:

```python
DUMP_VALUE = re.compile(r"-0751-isolation-([0-9a-f]{1,2})-(?:before|after)-", re.I)
```

§6 asks for `<value>` "lower case and without `0x`" in six file names per
block, so on that path §4.6's comparison is between a byte on disk and a
substring of a name somebody typed by hand.

The day's real values are in hand next to it. `assign_blocks` opens a block on
a `write` mark and names it by the value that mark carries; `Block.value` is
documented as what that mark carried; and `verdicts_for` builds `{value:
marker}` from exactly that set. It is used for one thing — `verdict_note`
looks the value up to decide whether to print a block marker, and prints
"no block under test 0xNN is in this run" when the value is absent. **The
comparison against the written value never consulted it**, and after a
transposition it could not: a swap leaves every value still a block of the
day, so that membership test passes on exactly the runs where it is least
useful.

## The two transcripts

`0751-isolation-run-multi-block/` is a two-block day: block 1 writes 0xA0,
block 2 writes 0x10, both `intact`, and the two blocks' `0x0700` dumps hold
each block's own starting value before and its own written value after. Copy
the directory and rename one block's two `0700` dumps to carry the other
block's `<value>`, so the files now named `-10-` hold block 0xA0's bytes:

```
$ cp -r ec/tools/testdata/0751-isolation-run-multi-block /tmp/swap
$ cd /tmp/swap
$ mv 2026-01-01-0751-isolation-a0-before-0700.txt 2026-01-01-0751-isolation-10-before-0700.txt
$ mv 2026-01-01-0751-isolation-a0-after-0700.txt   2026-01-01-0751-isolation-10-after-0700.txt
$ python3 ec/tools/grade_0751_isolation.py /tmp/swap/*.csv \
    --dump /tmp/swap/2026-01-01-0751-isolation-10-before-0700.txt \
    --dump /tmp/swap/2026-01-01-0751-isolation-10-after-0700.txt
```

Before this change that printed, byte for byte, with `/tmp/swap/` shortened to
`…` and the run's exit code 0:

```
  block 0x10, from the <value> in these files' §6 names
  …-10-before-0700.txt: 0x0751 = 0x10
  …-10-after-0700.txt: 0x0751 = 0xA0
  the first --dump already holds the written 0x10, so these files do not show the write landing: either the write did not take, or the dump named before was taken after it. Nothing here separates the two.
  the last dump holds 0xA0, not the written 0x10 -- the byte moved back. What remains is the EC's other 0x0751 write paths or the vendor service, and §3a's service-stopped run is what separates them.
```

Block 0x10's write did not move back. Block 0xA0's did not either — it is the
byte printed two lines above, from a different file, filed under the other
block. "The byte moved back" is a claim about the EC reverting a host write,
and it is the sentence that sends an operator to run §3a's second pass. The
line above it is arithmetically right and explains itself as *"the write did
not take, or the dump named before was taken after it"* — neither of which is
what happened, and both of which are about this block's own write.

The other direction, renaming the other block's pair onto this one's stamps, is
the same shape under 0xA0:

```
  block 0xA0, from the <value> in these files' §6 names
  …-a0-before-0700.txt: 0x0751 = 0xA0
  …-a0-after-0700.txt: 0x0751 = 0x10
  the first --dump already holds the written 0xA0, …
  the last dump holds 0x10, not the written 0xA0 -- the byte moved back. …
```

**Both directions give the false cause, not one of each kind.** The issue
expected the other direction to read `the last dump still holds the written
0xNN` — a false positive — and quoted a transcript for it whose own two byte
lines do not agree with the sentence under them. Renaming the committed
fixture's names does not produce that shape. It takes a group's *after*-dump
holding the written value as well as its before-dump, which no exchange of two
`<value>` stamps produces: each block's after-dump holds its own written value,
and moving a name moves the file with it. What a transposition does produce is
what is printed above, in both directions, and the check catches both. The
false-positive shape is a different input, and it is disclosed by
`report_readback`'s before-side line rather than by this one — see the gate
below.

Both sections are affected. Through `--dump-pair` the same two files are a
bracket filed by the same stamp, and `dump_pair_block` refuses a pair whose
two names disagree *with each other* — a swap makes them agree with each other
and be wrong together, so §6's own observation applies directly: "the two
blocks' brackets here are the same reading of the same page in opposite
directions and come out byte for byte identical, so nothing inside a mis-filed
bracket looks wrong".

## The rule

§3 takes the `-before-` dump at step 0, before the control arm and before the
write. So a file named `-before-` for block `V` cannot already hold `V`
**because of that block's write** — `V` is what the block's `write` mark
carries, and that write is after step 0.

**Step order is not the whole of it, and the missing half is a day §3
produces.** It says nothing about the byte having held `V` before the block
*began*. §3 nowhere requires the value under test to differ from what is
already there: step 2 is literally "write the value already there back to
itself and mark that as a no-op", which presupposes a value and names none.
A day that writes 0xA0 onto a byte already at 0xA0 is a day the procedure
produces, and on it a `-before-` dump holding 0xA0 **is** that block's
before-dump.

So the withhold is gated on the day's own answer to that question rather than
on the step order alone. The capture records it directly: §3's step-2 mark is
`no-op wrote 0x0751=<current>`, so `control_arms_for` reads each block's
control arm into `{value: byte}`, scoped exactly as `verdicts_for` scopes its
own index, and **`misfiled_before` fires only where that block's control arm
named some other value.** Where the day records no control-arm value at all
the answer is `None` and nothing fires — "not recorded" is not "recorded as
something else", and a withhold rests on disagreement rather than on silence.

That is arithmetic about two artefacts of the same run. It asserts nothing
about the EC, and it is what `misfiled_before` tests — once for the `--dump`
group and once for the `--dump-pair`'s before side, from the same predicate
and the same index, so the two readers cannot disagree about a group both are
looking at.

### The day that is not transposed and is not wrong

Built from §6's own single-block day with the control arm and restore rewritten
to the value already in the file, the `0x0751,0x10,0xA0` change row dropped
because nothing moved, and the before-dump set to 0xA0:

```
$ python3 ec/tools/grade_0751_isolation.py <the copy's three CSVs> \
    --dump <before, 0x0751 = 0xA0> --dump <after, 0x0751 = 0x10>

  block 1 of 1: value under test 0xA0, roles control, write, restore
=== 0x0751 across the dumps (§4.6) ===
  block 0xA0, from the <value> in these files' §6 names
  …-a0-before-0700.txt: 0x0751 = 0xA0
  …-a0-after-0700.txt: 0x0751 = 0x10
  the first --dump already holds the written 0xA0, so these files do not show the write landing: either the write did not take, or the dump named before was taken after it. Nothing here separates the two.
  the last dump holds 0x10, not the written 0xA0 -- the byte moved back. …
```

Every mark spelled as §6 spells it, every change row agreeing with what the
dumps hold, nothing transposed, exit code 0. The readback prints, the bracket
compares, and the notices are absent — which is the whole of what the control
arm gate buys. A rule resting on step order alone withholds here and prints
that the file name and the day's marks disagree about which block these bytes
are, while naming as the record of the byte having been elsewhere a control
arm that recorded 0xA0. Nothing disagrees, and that sentence is false of the
day it is printed about.

`test_a_day_that_writes_the_value_the_byte_already_holds_is_still_read` builds
that day and pins it. It is the case the fixture scan below cannot reach: no
committed capture happens to rest at the value under test, so the scan is
green whether or not the rule handles this shape.

## Withheld, and where the withhold stops

The notice replaces the verdict rather than printing under it: a warning
*beneath* a §4.6 result leaves that result standing, and the result is the
line a fold-in quotes. It names the file, the block's own `no-op wrote
0x0751=0xNN` control-arm mark and the value that mark recorded, the `wrote
0x0751=0xNN` mark that puts the value there afterwards, and the `<value>` the
file name came from — and names **no cause**, because which of the two file
names is the wrong one is a question about files, and the notice does not
answer it.

It claims **no uniqueness** for any mark it names. "The only other record of
`V`" would be false on the very run this fires on: `multi-block/`'s
`0x0700` CSV carries 0x10 in three mark rows — `no-op wrote 0x0751=0x10`,
`restored 0x0751=0x10`, `wrote 0x0751=0x10` — and in each of the four
`0x0751` change rows the file has:

```
$ grep -E ',0x0751,' ec/tools/testdata/0751-isolation-run-multi-block/2026-01-01-0751-isolation-0700-07ff.csv
```

A day that wrote a value twice carries several records of it whatever else is
true. A `no-op wrote` and a `restored` carrying the value are records of it in
the day as plainly as the `wrote` mark is, and the control-arm one is the
record that says the byte already held the value before this block's write,
which is the record the withhold now turns on.

The exit code is unchanged and the rest of the run still reads: nothing in the
capture is broken, the marks grade and both blocks print `intact`, so this is
an input error stated in place of the claim it made unsupportable, not a
refusal. §4.6's per-file `0x0751 = 0xNN` lines still print above it, since
what a file holds is a fact about files on disk, and the whole-block report
still names the pair where it was handed in.

Four gates, each because the broader form would take something back:

- **A name-derived value only.** A group filed from `--block`/`--wrote` has
  no name-derived claim, and §6 has the operator name the block themselves.
- **A value the day actually wrote.** The notice names the day's
  `wrote 0x0751=0xNN` mark as one of the records that disagree with the file
  name, and a value the day never wrote has no such mark — so firing there
  would print a line whose own sentence is false. That case is a *different*
  one and `verdict_note` already discloses it by name, without guessing which
  file is wrong: a single-block day whose dump is stamped for a value it never
  wrote prints `no block under test 0xNN is in this run`, and that line is
  kept and pinned rather than replaced.
- **A control arm that named some other value**, for the reason the section
  above gives. This is the precondition the withhold rests on, and it is read
  from the day's own marks rather than inferred from step order.
- **The `last != written` arm of §4.6, and this one is the narrowing that
  matters.** §4.6 has two arms and they are not the same kind of sentence.
  `last == written` prints "the last dump holds the written 0xNN. Per
  CLAUDE.md that is a readback, not evidence the EC acted on it" — true of the
  last file whatever else is true, carrying its own calibration, and sitting
  under the before-side line that already names both readings a group in that
  shape leaves open. Nothing there is a claim about the machine to withdraw.
  `last != written` prints "the byte moved back", names the EC's other write
  paths or the vendor service, and points at §3a — and that is a claim about
  the EC, and the one this change stops. `readback_blames_a_writer` is the
  gate, and it is a gate on the *claim* rather than on the files.

The last two gates are independent and neither does the other's work, which
is what the two cases in the suite pin: a group whose before-dump holds its
own value while the control arm says otherwise is withheld only when the last
dump does *not* hold it too, and a group whose before-dump holds its own
value while the control arm agrees is not withheld at all.

That last gate is why
[`0751-readback-before-dump-holds-written-value.md`](0751-readback-before-dump-holds-written-value.md)
needed no edit. That work chose to keep the positive arm ("only disqualifies"),
and a rule stated more broadly than the claim it removes would have taken that
choice back — including the assertion that the comparison still runs when the
byte holds what was written.

**One thing it does take back, on the `--dump-pair` side.** That write-up's
last follow-up records that `--dump-pair` reads the same two files at a
different strength, and that §4.6 is now the stronger of the two readers on
this shape with the whole-block section not yet brought up to it. The control
arm gate keeps §4.6's positive arm, but `--dump-pair` has no `last ==
written` arm to fall back on, so a pair whose before side already holds its
own block's value on a block whose control arm named something else is now
withheld there rather than compared. That is the deliberate trade this change
makes: a bracket is either printed or it is not, and printing one over a
before-dump the day's own marks contradict would file the other block's bytes
under this one. It is the same disagreement §4.6 withholds for, in a section
that has no weaker sentence to keep.

## What it does not catch, and the fixture that would catch it

- **A group of one dump.** There is no before side to check. §6's own command
  line hands the block's `0x0700` pair in as two `--dump`s, so this is not
  the shape §6 produces — but a run is not required to hand in a pair, and
  the same is true of the days' own second range.
- **A day's dumps checked against the CSV's own `0x0751` change rows** — the
  stronger cross-check, which would catch a day where only the *after*-dumps
  were transposed. It is not taken because it is conditional on the `0x0700`
  watcher having recorded the row inside the block's write window, which a
  real run may not, and a conditional check that silently does nothing is the
  failure mode this repository keeps writing about.
- **A block whose control arm is missing or carries no value.** The gate is
  the day's own record of what the byte held before the write, and a day that
  records none cannot be checked against it. That block's mark set is already
  reported as incomplete by the census; this adds nothing on top of it rather
  than guessing.
- **`multi-block/`'s own `-10-` before-dump is inconsistent with its own
  control mark.** That file holds 0xA0 while the block's control arm in the
  same fixture is `no-op wrote 0x0751=0x00`. Committed input that does not
  agree with itself is a separate finding and is not acted on here; it is
  named because it is the reason the stricter rule above would redden on this
  tree today, and because fixing it is a fixture byte plus a header sentence
  plus the `testdata/README.md` row for it. It does not fire the withhold
  either way: the file holds 0xA0 under the name `10`, and 0xA0 is not the
  value that group names.

## The no-op property, and how it is held

The change fires on no committed input: every committed `-before-` dump holds
a value other than the one its own name carries.
`test_no_committed_before_dump_already_holds_the_value_it_is_named_for` reads
each of those files through `read_dump` and asserts the property, which is a
claim about the fixtures' shape rather than a count of them — so the next
fixture landing cannot turn it into a figure every merge has to edit.

That scan is the weaker half of the pin, because it is green whether or not
the rule handles the shape that matters: no committed capture happens to rest
at the value under test, so there is none in that shape to find.
`test_a_day_that_writes_the_value_the_byte_already_holds_is_still_read` builds
that day instead — from §6's own files, per run, in a `tempfile` directory —
and asserts that the readback and the bracket both come back. The rest of the
suite's assertions over `dumps_section` and `whole_block` are the wider half of
the no-op: a clean run's output is byte for byte what it was.

## Where the rest of it lives

- `ec/tools/grade_0751_isolation.py` — `DUMP_SIDE` beside `DUMP_VALUE`,
  `dump_side` / `readback_blames_a_writer` / `misfiled_before` beside
  `dump_block`, `control_arms_for` beside `verdicts_for` (same index shape,
  same scoping, for the same reason), `MISFILED_BEFORE_NOTE` and
  `misfiled_note` beside `SAME_FILE_PAIR` (both readers print one string, for
  the reason that constant gives), and the two call sites. `dump_block` itself
  is untouched — same signature, same return shape, same docstring — so
  nothing that reaches it moves.
- `ec/tools/test_grade_0751_isolation.py` — `MisfiledBeforeDumpTests`, the
  last class in the file. Appended rather than inserted, for the reason the
  comment above `ReadbackNoticeTests` gives: line pins across this suite's
  write-ups and the per-pin table in
  [`test-line-pin-census.md`](test-line-pin-census.md) cite into the file
  below `GradeTests`, and a class added anywhere else moves all of them onto a
  line that no longer says what its sentence says it does.
- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §6, the paragraphs
  after the `--dump-pair` attribution one, which is where a reader of the
  procedure is told the rule.
- `ec/tools/measure_mark_provenance.py` — one row of `CITATIONS`, re-anchored
  and nothing else. Its quoted text is carried by two functions, so `resolve`
  picks whichever site is nearer a number that is only a hint; the helpers and
  the notice above `existing_mark_provenance` shifted that pair across the
  midpoint, and the join then reported its site as one no citation names. The
  row's `what` still describes the same line, and the comment above the row
  already records this crossing and this remedy from an earlier one.
- `ec/annotations/registers.yaml` is **not** touched. `MANUAL_FAN_CTRL` stays
  `present-untested`; whether the fixed-load run moves it is that run's
  question, and this change removes one way a wrong §4.6 could be produced. It
  produces no evidence for or against the register.