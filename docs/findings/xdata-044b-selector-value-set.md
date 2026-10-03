# `0x044B`'s writable set and its reader set are the same values, and `0x9A0E` spends the byte on one threshold of three

**Issue #223, 2026-10-03.** The issue asked for three things: the writable value
set and the reader set, each with the site that produces or consumes every value;
the "`0x9B33` tests for 1 and nothing writes it" gap, resolved or recorded as not
found by this method; and `0x9A0E`'s three-way subtract plus `0xBB39`'s
destination described well enough to say what the byte is for.

The first resolves from files already in the tree and needs no other issue. The
third turned out to need **correcting** rather than describing — the issue reads
both `0xBB31` and `0xBB39` the wrong way round, and the corrected reading is
what makes the routine say anything at all.

[`044b-mode-stepper.md`](044b-mode-stepper.md) already decodes the dispatch at
`bank0 0x9AAD`: which value leads to which, and which routine writes it. This
page is the other half — which values a *caller* can put there at all, which
values a reader has to cope with, and what the one routine that reads the byte
for something other than dispatching on it does with the result. It cites that
page rather than restating it.

Nothing here is a live observation. Every statement below is read out of a
committed `.asm` listing, and the two whole-image scans named further down were
run against the committed firmware and are quoted beside the commands that
produce them. No register was read back, no hardware or Windows machine was
involved, and `XDATA_044B` keeps its `status:`.

## The gap, and the one byte that closes it

The issue's difficulty was arithmetic on paper: the three write sites the direct
scan counts supply 0, 2, 3 and 4, plus "whatever `0xBA15` returns plus one" —
and the reader at `0x9B33` tests for 1, which none of the counted writers
obviously writes. `0xBA15` is the unknown in that sentence, and it is one byte:

```
BA15     e4 - -   clr      A
BA16     90 08 cc mov      DPTR, #0x8cc
BA19     f0 - -   movx     @DPTR, A
BA1A     a3 - -   inc      DPTR
BA1B     f0 - -   movx     @DPTR, A
BA1C     90 08 ce mov      DPTR, #0x8ce
BA1F     f0 - -   movx     @DPTR, A
BA20     a3 - -   inc      DPTR
BA21     f0 - -   movx     @DPTR, A
BA22     22 - -   ret
```

`ec/decompiled/listing-index.csv` gives `BA15` a size of one, and the run ends
in the single `ret` at `BA22`; nothing between them touches A. So `lcall 0xBA15`
returns **A = 0**, and the `inc A` at `0x9A7E` makes the value `0xBD20` is
handed exactly 1.

Two things make that the reading rather than a coincidence of the boundary.
Every committed transfer to `0xBA15` is an `lcall` — `bank-call-targets.csv`
names `0x9A7B`, `0x9A86`, `0x9A90` and `0x9A9C` and no other — so no caller in
the tree takes the fall-through that would have it store four bytes instead of
returning. And the listing immediately below it, `0xB9F5`'s, ends in the `ret`
at `BA14`, so nothing falls in from above either.

The `anl A,#0x7f` at the end of `0x9A7B` masks the byte `0xBD20` **returns** —
the read of XDATA `0x08E2` — and not the value written to `0x044B`, which the
accumulator no longer holds at that point. Reading the mask as a limit on what
`0x044B` can hold is a mistake the listing itself refutes.

## The writable value set, one producer each

| the value | the site that writes it | how it gets there |
|---|---|---|
| 0 | `reset_08ad_08bf_and_clear_08e2_bit7` (`bank0 0x9C24`) | `clr A`, then `lcall 0xBD20`, which stores the caller's accumulator to `0x044B` |
| 1 | `store_bd20_result_masked_7f` (`bank0 0x9A7B`) | `lcall 0xBA15` (A = 0), `inc A`, `lcall 0xBD20` |
| 2 | `call_ba15_then_write_02_to_044b` (`bank0 0x9A86`) | `mov A,#0x02` into `DPTR = 0x044B` |
| 3 | `call_bd20_with_03_then_or_80_into_dptr` (`bank0 0x9A90`) | `mov A,#0x03`, then `lcall 0xBD20` |
| 4 | `write_04_to_044b_and_set_08e2_bit7` (`bank0 0x9A9C`) | `mov A,#0x04` into `DPTR = 0x044B` |

`0xBD20` stores whatever A it is handed, and each of its callers hands it a
different constant, so routing through it adds no value of its own. Nothing else
in the tree writes `0x044B` at a site the direct scan counts —
`ec/annotations/xdata-0400-045f-sites.csv` has carried the `0x0BD20` write row
since the byte was entered, and it is a row of that table, not a row this page
found.

`0x9C24` is the one producer here that is not one of the arm writers
`044b-mode-stepper.md` names. It is the routine the dispatch's three prologue
bail-outs jump to, so it is where the byte is re-initialised rather than
re-decided, and it is the only path by which the byte takes value 0 at all. That
is why that page could call 0 "the entry state rather than a peer of the other
four" without naming the instruction that produces it.

**What this is not.** "Nothing else in the tree writes `0x044B`" is a statement
about the sites this tree's methods place, and the boundary is worth naming
because the issue named it. `trace_xdata_refs.py` finds direct `MOV DPTR,#imm16`
sites, so a store through a computed DPTR would not be in the table above. The
two committed scans that look for that shape both report page `0x04` unreached
by the main EC —

```sh
python3 ec/tools/computed_dptr_sites.py ec/firmware/GMxMGxx_11.800 --page 0x04
python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --page 0x04
```

— and each prints the sites it could not place rather than ruling them out. That
is "not found by this method" and it stays that. It does not affect the
question the issue asked, because the gap closed above closed by reading the
bytes at a site the direct scan had counted all along; issue #110 stays open for
addresses with no direct writer at all, and this is not one.

## The reader set, one arm each

`bank0 0x9AAD` reads the byte once, at `0x9B33`, and its chain enumerates the
same values:

| the value | the arm that consumes it |
|---|---|
| 1 | `0x9B63`, the first `dec`/`jz` pair |
| 2 | `0x9B75`, the second |
| 3 | `0x9B99`, the third |
| 4 | `0x9B43`, the `jnz` falling through to `ljmp 0x9C00` |
| 0 | `0x9B4D`, the `add A,#0x4` at `0x9B46` restoring the byte so the `jz` at `0x9B48` can take it |

`0x9B4A` is the default for everything else. **The two sets are equal**, which is
the issue's question — "does the reader test for a value nothing writes?" —
stated as a relation rather than as two headcounts that a later branch would
have to re-derive. Which arm does what with the value it found is
`044b-mode-stepper.md`'s subject, not this one's.

The issue also said `0x9B33` has no row in `ghidra-functions.csv` and sits
inside `0x9917`. Both halves are stale: `bank0,0x9AAD` now carries a row named
`dispatch_044b_then_write_01_02_03_or_04`, and `0x9B33` is inside that routine.

## The second reader, and three corrections to its reading

`bank0 0x9A0E` is the only other routine that reads `0x044B`, and it reads it
twice, at `0x9A4B` and `0x9A57`. The issue's account of what it then does needs
three corrections, and they are the substance of this page's second half.

### It is two tests over a default, not three cases

```
9A4F     b4 04 05 cjne     A, #0x4, 0x9a57
9A52     90 08 cb mov      DPTR, #0x8cb
9A5B     b4 02 05 cjne     A, #0x2, 0x9a63
9A5E     90 08 c2 mov      DPTR, #0x8c2
9A63     90 08 ca mov      DPTR, #0x8ca
```

Value 4 selects `0x08CB`, value 2 selects `0x08C2`, and **everything else —
0, 1, 3 and any value above 4 — takes `0x08CA`**. Three of the writable values
and the whole default arm land on the same byte, so the selector picks between
two named thresholds and one catch-all rather than between three.

### `0xBB39` does not choose the destination

Its whole listing is a fixed literal:

```
BB39     90 0a 49 mov      DPTR, #0xa49
BB3C     e0 - -   movx     A, @DPTR
BB3D     94 00 -  subb     A, #0x0
BB3F     22 - -   ret
```

`0x0A49` is a constant in the instruction, not a value carried from the caller.
The `movx @DPTR,A` at `0x9A72` therefore stores to `0x0A49`, and the routine
the issue found "unnamed" names it after all — in the listing, three bytes down.

### The two listings are one routine, and the carry is a 16-bit borrow

`0xBB31` is eight bytes with no `ret` of its own and runs straight into
`0xBB39`, so the two are one subtraction:

```
BB31     e0 - -   movx     A, @DPTR        ; A = the byte the caller selected
BB32     ff - -   mov      R7, A
BB33     d3 - -   setb     CY             ; the +1
BB34     90 0a 4a mov      DPTR, #0xa4a
BB37     e0 - -   movx     A, @DPTR
BB38     9f - -   subb     A, R7
BB39     90 0a 49 mov      DPTR, #0xa49
BB3C     e0 - -   movx     A, @DPTR
BB3D     94 00 -  subb     A, #0x0
BB3F     22 - -   ret
```

It computes `(0x0A49:0x0A4A) − (selected + 1)`, with `0x0A49` the high byte and
`0x0A4A` the low, and returns the high byte of the difference in A with the
carry left by the **whole** sixteen-bit subtraction — not the borrow of the low
byte alone, which `0xBB38` produced and `0xBB3D` consumed.

That settles the "what `0xBB31`'s carry signifies is not established by this
listing" clause in the `bank0,0x9A0E` row. Read against the branch conditions
at the call sites:

| the call | the branch after it | so the routine continues only if |
|---|---|---|
| `DPTR = 0x08CA` | `jc 0x9A41` (failure) | scaled > `XDATA[0x08CA]` |
| `DPTR = 0x08CB` | `jc 0x9A41` (failure) | scaled > `XDATA[0x08CB]` |
| `DPTR = 0x08C2` | `jnc 0x9A4B` (success) | scaled > `XDATA[0x08C2]` |

`jnc` jumps *on carry clear*, so the third branch continues to the arithmetic
under the same predicate as the two `jc` failure tests — all three are lower
bounds on the scaled value, not a bracket around it. `0xBB31` opens with
`movx A,@DPTR`, so what each call compares is the **byte at** the address in
the first column. **The subtraction runs only when the scaled pair exceeds the
byte at `0x08CA`, the byte at `0x08CB` and the byte at `0x08C2`** — three lower
bounds, which together are the one condition that the pair exceeds the largest
of the three. On any other value `0x9A0E` writes `0x00` to `0x0A49`, `0x01` to
`0x0A4A` and returns 1.

Which of the three binds is **not established**, and the addresses do not say.
All three are run-time table entries rather than constants: `0x96AD` fills them
out of one indexed CODE table, `mov A,#0x31` / `movc A,@A+DPTR` and then `#0x32`
and `#0x33`, over an `R6:R7` base that `0xB93A` loads from XDATA `0x0A51` and
`0x0A52` at run time, so which table they are read from is itself decided then.
`ec/annotations/boot-xdata-sites.csv` records all three as `0x00` at boot, where
they are equal and none of them is the largest. Ordering them by address says
nothing about their values.

Note also what the pair is before any of this: `0x9A0E` loads XDATA `0x08EA`,
scales it through `mul16` (`0x707D`) with `0x0013` and `div_r6r4_by_r5_16bit`
(`0x708F`) with `0x0A`, and stores the two result bytes at `0x0A49`/`0x0A4A`.
The thresholds are compared against that scaled result, not against `0x08EA`.

## Where the number lands

On the success path `0x9A0E` subtracts the selected threshold from the low byte,
hands the borrow to `0xBB39`, and returns the low byte of the pair in R7. Its
two callers are both inside `0x9AAD`, at `0x9AEF` and `0x9B1B`, and each passes
that R7 straight to `0xBEA3` — `x044c_minus_r7`, `0x044C − R7` — with nothing in
between. `0x044C` is an address `ec/annotations/registers.yaml` already carries
as `XDATA_044C`, so the result of spending `0x044B` this way lands against a
byte the repository has a row for.

That is as far as the arithmetic goes here. Neither caller keeps the result:
each one clears A over what `0xBEA3` returned a few bytes later and branches on
the carry alone, so the difference decides a polarity rather than a quantity in
`0x9AAD`'s prologue. What either byte *means* is not decoded by this page or by
`044b-mode-stepper.md`.

## The route the issue suggested, and why it is a dead end

The issue proposed starting from the `bank0 0x9917` row and its arms, expecting
a dispatch on `0x0A50` further gated by `0x044B`. Those two routines are not
nested, and neither reaches the other:

- `0x9917` is 144 bytes (`listing-index.csv`), so it spans `0x9917`–`0x99A6`.
  Its arms leave for `0x99A7`, `0x99ED` and `0x9A00`, and its default is
  `ljmp 0x9A0D` — a bare `ret`, with `0x9A0E` beginning the next listing.
- `0x9AAD` is 336 bytes, so it spans `0x9AAD`–`0x9BFC`. Its only bank0 caller is
  the `lcall` at `0x84F7`.

What they share is the threshold block, not control. `0x9917` switches on
`0x0A50` and its arms pick a triple out of `0x08C0`–`0x08C9`; `0x9A0E` picks a
single byte out of `0x08C2`, `0x08CA` and `0x08CB`. Both read bytes that
`0x96AD`'s row records as filled by one indexed copy out of a CODE table. They
are two selectors over the same block, and neither calls the other.

Recorded as a negative result rather than papered over, which is what the
issue's "the answer is that the image does not say, which is a legitimate
result" clause is for — though here the answer is that the image says the two
are siblings, not that it says nothing.

## A trap in `bank-call-targets.csv`

That table carries bank1 rows naming `0xBD20` (file offsets `0x13B3D`,
`0x13F93`, `0x14159`, `0x14189`) and one naming `0x9A0E` (`0x119C3`). Those
resolve to **bank1's own** `0xBD20` (`clear_0834_word_when_nonzero`) and `0x9A0E`
(`set_161c_80_and_0681_85`), which are different routines in a different bank;
`grep -rn '0x44b' ec/decompiled/bank1/` returns nothing. The bank0 rows in the
same table are the real callers, and they are the ones already counted above, so
an implementer grepping this table for `0xBD20` callers gets both banks' rows in
one result and would report writers of `XDATA_044B` that bank1's never are.

## What is not established here

- **What the values select.** No register, subsystem or mode name is claimed for
  any of them. This page maps values to sites; it does not name what they are
  for. `044b-mode-stepper.md` says the same of the transitions, and
  `XDATA_044B` keeps `status: present-untested`.
- **What `0x08C2`, `0x08CA` and `0x08CB` are, and which of them binds.** All
  three are filled by the indexed CODE-table copy in `0x96AD` and none has an
  entry in `registers.yaml`. Their role in the arithmetic is established; their
  meaning is not, and giving them entries is separate work with its own
  warrant. Which of the three is the largest at run time is not established
  either, so the guard is recorded as the three-way condition it is in the
  listing rather than as whichever byte turns out to be strongest.
- **Whether the EC acts on any of it.** Every sentence above is a sentence
  about which arm stores which constant and which comparison guards which
  subtraction. A store being issued is not a behavioural observation, nothing
  was read back, and no hardware or Windows machine was involved.
- **The name of `0xBB39`.** Its row is `sub_low_byte_0a49` and this page shows
  the routine returning the *high* byte of a little-endian pair, so the name
  reads the wrong way round. The name is left alone here: changing it moves
  `ec/decompiled/index.csv` and renames an exported `.c`, and it is worth its
  own change rather than riding along in one that does not need it.