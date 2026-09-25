# The `movx @DPTR,A` batch: 88 functions, and only 37 of them take a value from a caller (issue #263)

The second variable-annotation batch, and the one where the **predicate was
right and the expectation was wrong**.

Issue #133's first batch took its boundary from an existing prose claim
("every function whose `hand-decoded` comment already names a `param_N`"), so
the work was transcription. This one takes its boundary from a property of the
machine code — *in this function's own listing, the first instruction that
touches the accumulator A is a `movx @DPTR, A`* — which reads like a stronger
kind of evidence than it is. It is not. It is a fact about **A**, and the batch
found that **49 of the 88 rows on it are not values arriving in A at all**.

The boundary is measured by `ec/tools/merge_annotation_shards.py --census`,
added for this issue. The rows live in
[`ec/annotations/ghidra-variables.csv`](../../ec/annotations/ghidra-variables.csv);
`docs/findings.md` §18 has the declaration census this batch re-measured.

**No hardware and no Windows host is reachable from this pipeline.** Everything
here is static: the listing is the evidence and the regenerated export is the
proof that a row landed. Nothing in it observes the machine.

---

## The boundary, and the two filters between the predicate and the batch

`--census` over the committed export, and each number below is that tool's
output rather than anybody's arithmetic:

| | count |
|---|---:|
| functions whose first A-touch never happens | 771 |
| `movx @DPTR, A` — the predicate | **117** |
| `movx @Rn, A` — same property, reported not folded in | 2 |
| …already named by issue #133's batch, so no longer declaring a `param_N` | 7 |
| …with no row in `ghidra-functions.csv` | 22 |
| **annotated and still declaring a `param_N` — the batch** | **88** |

By scope: bank0 55, bank1 17, pd 16, common 0. Between them the 88 signatures
declare **187** `param_N` (17 declare one, 53 declare two, 12 three, 2 four, 4
five). Median listing length 5 instructions, longest 208 (`bank0,0x8C46`).

Three things in that table are worth reading twice.

**`movx @Rn, A` is not 0 occurrences.** The plan this batch was built from
predicted it was, and said the selector should report the shape rather than
fold it in silently. It reports **2**: `common,0x0713` and `common,0x7003`.
Both have the same property, and both are left out of the batch because neither
is a bank program entry and the `value_a` rows the first batch wrote are
`@DPTR` rows. That is a scope decision, and it is recorded rather than hidden.

**Seven functions on the predicate no longer declare a `param_N`.** They are
issue #133's five `value_a` rows plus `bank0,0xAE87` and `bank0,0xDC17`, whose
placeholders that batch named by other routes. They are the predicate working
correctly on work already done.

**22 functions on the predicate have no row in `ghidra-functions.csv` and this
batch does not reach them** — 14 of them `common`. They are listed by address in
the tool's own report, so the next person to size this does not have to
rediscover them. Bounding a batch on the annotated population is a choice, and
this file states it rather than letting 88 read as the size of the predicate.

**Re-running the census now reports 71, and that is the same measurement rather
than a different one.** 86 of the 88 rows committed a name over their
`param_1`; 17 of those functions declared *only* that one, so they now declare
no placeholder at all and drop out of the "still declaring a `param_N`" line,
joining the 7 from the first batch in "already named". The two
`kind=unresolved` rows keep their placeholder and stay in the 71, as they
should. The 22 unannotated functions and the two `movx @Rn,A` are unchanged,
because nothing in this batch touched either.

---

## What the batch found: the predicate selects a family, and most of it is a constant

**37 `param`, 49 `artifact`, 2 `unresolved`** across the 88 rows: bank0 29/26/0,
bank1 1/15/1, pd 7/8/1.

Every row's `key` is `param_1`. That is worth one sentence because it is the
result the plan was most worried about going the other way: 53 of the 88 declare
two placeholders, `variable_csv_problems()`'s bidirectional check is satisfied
by a substitution between two of them, and a swap would pass every automated
check there is. It did not happen — but only because a second agent read all 88
`.c` files and decided, row by row, which identifier carries the stored value.

The distribution is the finding. **A value arriving in A is the minority case on
this predicate**, and the reason is structural:

> Ghidra's function boundaries on this firmware cut through straight-line code.
> 53 of the 88 listings contain no `ret` at all. They are not functions; they
> are addresses inside a block, and inside a block A is produced by the
> instruction before.

Two runs make it plain. `bank0,0xF079`–`0xF118` is one zero-filling and
constant-writing block that Ghidra carved into twelve separate entries; only
`0xF079` and `0xF161` take a value that arrives. `bank1,0x8008`–`0x8048` is
seven one-instruction entries, each one instruction after a `dec A`, so the
stored value is a countdown in each case and only `0x8801` in the shard is a
value from a caller.

So the honest row for most of the batch is `kind=artifact` with a name that says
where the value came from — `a88_from_8014`, `a0_from_b5c7`, `a_from_8047`,
`a_from_r5` — and the comment says the store writes the preceding block's
constant. **That is a better row than `value_a` would have been.** A `value_a`
on `bank0,0x801F` would have rendered `*entry_dptr = value_a` in the export for
an instruction Ghidra framed as a function but which its own annotation already
describes as "a single `movx @DPTR,A`" storing the `0xA0` that `0x801D` loaded.

Three of the bank0-3 rows are worth reading together, because their function
comments had **already reached the artifact reading** and the decompile still
emitted `param_1`: `bank0,0xF118`'s plate comment says the byte at 0xF116 loads
A with 0x40 "immediately before this entry, so the two together store the
constant 0x40", and the signature still says `DAT_EXTMEM_1621 = param_1`. Same
for `0xF498` and `0xF0EF`. The function layer had solved these; the variable
layer had not caught up.

---

## A recorded `lcall` is evidence that the address is reached, not that a caller supplied the value

This is the calibration the batch turned on, and it runs against the obvious
reading in both directions.

The 88 split 70/18 on whether `ec/annotations/bank-call-targets.csv` records an
`lcall`/`ljmp` into the address, and the plan's calibration said a row with a
recorded edge may say the caller left the value in A. **Read every reachable
caller of the `0xF079`–`0xF118` run and that rule inverts.** All twelve exported
callers set A explicitly immediately before the call — a constant (`mov A,#0x10`
at 0xEEDC before `lcall 0xF079`, `mov A,#0xff` at 0xE68A before `lcall 0xF0C8`),
a `clr A` (0xEDE9 before `lcall 0xF083`), or a register copy (`mov A,R5` at
0xE8A6 before `lcall 0xF0CA`) — and the second reader re-derived that set from
the image rather than taking it from the author. A caller that loads A right
before an `lcall` is **staging a value, not passing one**. So the edge
establishes that the address is a destination; it says nothing about where A
came from.

The rows say that, and the ones with no readable caller say the value's origin
is not established by these instructions. Three caveats about the census itself
came out of the same reading, and each is a limit rather than a result:

- **The file has no `pd` rows at all.** It is a bank-to-bank audit, so "no
  recorded edge" for the 16 pd candidates is a fact about the file's scope. The
  pd listings record `lcall`/`ljmp` into 15 of the 16, and the rows that lean
  on an edge cite the export rather than this file.
- **Some recorded sites are misaligned decodes.** All five `ljmp 0xE054` sites
  and the one `ljmp 0xE0C3` site sit inside the immediate bytes of a neighbouring
  `mov DPTR,#imm16`: `02 E0 54` is the `0x02` low byte followed by the `0xE0`
  (`movx A,@DPTR`) and `0x54` opcodes. This is the same pathology the committed
  `bank1,0xC118` rows already document, found independently in bank0.
- **A function's second recorded edge is very often in an unexported gap.** Eight
  of the bank0-2 edges (0x92D9, 0xA616, 0x92AB, 0xD19D, 0xD1A2, 0xD1D8, 0xD200,
  0xD25F) fall in three regions no committed listing covers. `0xD2EF`'s only
  two edges are both in the 0xD196-0xD235 gap, so it has no exported caller at
  all, and its row says so instead of reading the census as a caller.

---

## The defect the verifier caught, because it is the one this predicate invites

**Ten of the 88 rows were rejected on the first verification pass**, and the
author of bank0-2 then found three more of the same shape in its own shard once
it had the pattern. Six of the ten were one mistake, and it is worth stating as
a rule because it is invisible in the export and natural to make:

> **`mov DPTR,#imm` as the last instruction before an entry is not evidence
> that nothing set A.** When it is the second instruction of a two-instruction
> block, the `movx A,@DPTR` ahead of it is the producer.

`bank0,0xB994`'s comment justified `value_a` by observing that the instruction
before the entry, `mov DPTR,#0x792` at 0xB991, "touches no A" — omitting
0xB990, which is the `movx A,@DPTR` that supplies the value the store writes.
`bank0,0xB9EE` is the same shape (`0xB9EA` reads, `0xB9EB` loads `0x0A56`), and
so are `0xBE21`, `0xE054` and `0xE0C3` in bank0-2, where the verifier found the
omitted producer in bytes that belong to **no exported listing at all** and had
to be decoded from the image. The correct reading walks back to the nearest
barrier — a `ret`, an `ljmp`, or the start of an unexported gap — and accounts
for every instruction in between.

The walk-back is also what the two rows' corrected comments now say, and it
made one of them better than the author first wrote it: `0xB9EE`'s fall-through
is fully decoded as a pointer chase (0x1919 → 0x0A56), while `0xB994`'s is not,
because `0xB989`'s block rebuilds DPTR from a byte it reads rather than a
constant. The asymmetry is stated rather than papered over.

Two of the corrections moved a row's **kind**, not just its wording, and both
moved it away from `param`: `0xE054` is now `artifact`/`a_from_r7` because an
unexported `mov A,R7` sits one byte before the store, and `0xE0C3` is now
`artifact`/`a0_from_e0c2` because an unexported `clr A` does. One moved the
other way: `0xBB4D` was `artifact`/`a0a_from_bb4b` until the image showed a real
`lcall` at 0x92D9 with `mov A,#0x05` before it, and a name that says 0x0A is
wrong on a path where the value is 0x05. **That is the batch's argument in one
row** — the artifact reading is what the *export* shows and the param reading is
what the *image* shows, and only the image settles it.

The remaining four rejections were plain factual errors, all in bank1-1 and all
checkable from the committed listings in seconds: a block head and tail reversed
(`0x8018`), a neighbouring block's byte attributed to this one (`0x8028`), a
`dec A` address in a name that belonged to a different store (`0x8048` — the
name moved to `a_from_8047`), and two blocks separated by a `ret` treated as
one (`0x9007`). The last rejection, in bank0-3, is a naming rule worth keeping:
`a80_from_e376` pointed at the **block head**, and 0xE376 is a `mov DPTR` that
never touches A — the setter is `0xE379`. In the other thirteen artifact rows of
that shard the two addresses coincide, which is exactly why the mistake was easy
to make and invisible:

> **A name built from a block head silently misdirects as soon as the block
> grows a `mov DPTR` ahead of its A-load.** Name the address of the instruction
> that *sets* the register, always.

The same walk-back, re-run from the image rather than the export, found the
three self-caught rows in bank0-2: `0xBC06`'s preceding run has **two** A-writes
and the comment named one; `0xD2EF` asserted "no caller is visible" and the
image refutes it, because both recorded call sites decode as real `lcall`s in a
stretch no listing covers; and `0xBE73`, `0xD2CB`, `0xD2DA` and `0xD304` each
gained what the image shows at their second call site.

---

## The two `unresolved` rows, and why they are the right answer

**`bank1,0xF030`.** Its `.asm` exists because a byte-pattern scan found `f0`
inside `mov DPTR,#0xF0A1` at 0xF02F, so the predicate fired on operand bytes.
The `*param_2 = param_1` in the decompile belongs to 0xF02C. A's value there is
not established.

**`pd,0xC808`.** The byte at 0xC808 is simultaneously the listing's
`movx @DPTR, A` opcode and the SFR-B (0xF0) address operand of `mov B,#0x77` at
0xC807 in the linear decode. Both readings are real: `ec/decompiled/pd/CB2A.asm`
ends `ajmp 0xc808`, so the listing is right for that entry, while the linear
path is a scaled-index idiom like 0x56CB's. On the jump path A is R3 **and** R5;
on the linear path it is R6. One name cannot say both, so there is no name.

Both rows keep the placeholder, which is what `kind=unresolved` is for: the
listing does not say, and saying so costs nothing.

---

## What this batch did not do

- **The `entry_dptr` family.** The 187 signatures declare 187 `param_N`; 88 are
  the A value, and most of the other 99 are the uninitialised-DPTR shape. That
  is a *different* predicate ("DPTR is loaded nowhere before first use") and
  issue #133 scopes this batch to the A family. It is the obvious next one, with
  the same boundary discipline.
- **The declared locals.** Explicitly out of scope, and blocked behind the XDATA
  map the register-naming issues own.
- **The 22 unannotated functions on the predicate.** Listed above; not batched.
- **Settling whether a variable row may change a caller's arity.** The census
  moved again (see `docs/findings.md` §18 and
  [`ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md)),
  and this is one more data point, not a decision.

## Follow-ups worth filing

- **`merge_annotation_shards.py`'s evidence guard does not check that the path
  exists.** It refuses a cell that names no path-like token and accepts one that
  names a path that is not there: an author who mistyped the prefix as
  `ec/annotations/bank0/` got all 20 rows of a shard accepted. `group_functions.py`
  already has the `os.path.exists` check the variables path lacks, and the
  author's rows were only caught by an ad-hoc sweep. Reported, not fixed here —
  widening the merge's refusal set is its own change.
- **The call census manufactures `ljmp`s from `mov DPTR,#imm16` immediates.** All
  five sites for 0xE054 (0xC12E, 0xC136, 0xC146, 0xC15E, 0xDC79) and the one for
  0xE0C3 (0xB3C8) are the `0x02` low immediate byte followed by the `0xE0`
  (`movx A,@DPTR`) and `0x54`/`0xC3` opcodes. This is the same pathology the
  committed `bank1,0xC118` rows already document, found independently in bank0,
  and it belongs in `bank-call-audit.md` because the census is where these
  function boundaries come from.
- **Conversely, "no exported listing covers that offset" was repeatedly evidence
  of presence.** Eight edges in the gaps 0x92B8-0x930B, 0xA4E2-0xA662 and
  0xD196-0xD235 (0x92D9, 0x92AB, 0xA616, 0xD19D, 0xD1A2, 0xD1D8, 0xD200, 0xD25F)
  all decode as real `lcall`s. Two rows in this batch had to be corrected from
  "no caller is visible" to "the image confirms a caller". Seeding those gaps is
  a `bank-call-audit.md` question, not a variable one.
- **`bank0,0xE054`'s function row is now questionable** and wants its own
  follow-up: its plate comment says "DPTR is left entirely to the caller", but
  the unexported run sets DPTR to 0x1521 one byte before the store, so on the
  fall-through path the address written is 0x1521.
- `pd,0x3544` and `pd,0x354F` are one routine split in two: read as a block it is
  `clr A`, ten `movx @DPTR,A` / `inc DPTR` pairs and a `ret` at 0x3559. Both
  function rows describe half of it; the pair is a candidate for the function
  layer.
- `ec/tools/build_ec_decompile.py --check` flagged a pre-existing staleness on
  `main` that this batch's re-export cleared: `bank1/19A8.c` carried a plate
  comment older than its own `ghidra-functions.csv` row (issue #255's
  correction), so the committed `.c` and the annotation disagreed. The export
  caught it up, which moved the XDATA census on its own — see the merge note in
  §18.
