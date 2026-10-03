# `0xA5E6` returns the quotient's low byte in R1, and a probe built on the opposite reading could not have agreed with a capture (issue #358)

**2026-10-03, issue #358.** PR #200 read `mul_16_round_shift_subtract` (bank1
`0xA5E6`) as leaving "the quotient's high byte in R1, its low byte in R2" and
built `windows/tools/system_id_probe.py` on that reading, while correctly
refusing to say which side of the resulting model/capture disagreement was
wrong. **The reading was wrong.** R1 is the **low** byte. The probe, its
offline checks, and the procedure written from it were all corrected; the
error is left visible here rather than edited out of history, per `CLAUDE.md`.

The correction is not a reading of the listing. `ec/tools/a5e6_quotient.py`
parses `ec/decompiled/bank1/A5E6.asm`, executes the instruction stream on a
small 8051 core, and compares every register against an independent Python
model of shift-and-subtract written from the algorithm rather than from the
listing. Two implementations, one machine; a disagreement is a red run.

```console
$ python3 ec/tools/a5e6_quotient.py
listing ec/decompiled/bank1/A5E6.asm: 39 instructions
two implementations over 423 input pairs: they agree on every register
```

## Where the claim was carried, and what happened to each

| file | what it said | verdict |
|---|---|---|
| `ec/annotations/ghidra-functions.csv`, `A5E6` row | "Which register holds which operand is not decoded further" | corrected here: the roles, the carry-into-R0 step and the epilogue mapping, cited to listing addresses |
| `ec/annotations/ghidra-functions.csv`, `0xF3D7`, `0xF416`, `0xE8A4` rows | wrote the returned R1 to their byte without saying which byte of the quotient that was | corrected here, one clause each |
| `ec/annotations/ghidra-functions.csv`, `0xF436` row | "If the quotient's high byte R2 is nonzero it overwrites the low byte R1 with 0xFF" | already correct — cited below as corroboration, left alone |
| `ec/annotations/ghidra-functions.csv`, `CB80`, `CB1F` rows | "stores the low byte of the quotient" | already correct — corroboration, left alone |
| `windows/tools/system_id_probe.py` | "on exit R1 is the quotient's high byte, R2 its low byte", and arithmetic that masked nothing | corrected in place; the old wording is quoted in this row and in the file's own docstring, which now says an earlier version read it the other way |
| `windows/tools/test_system_id_probe.py` | pinned the swapped model in `test_what_is_stored_is_the_quotients_high_byte`, in `test_the_mask_keeps_the_060c_arm_inside_one_byte`'s `{0, 1}` bound and in `test_the_two_divisors_separate_only_where_the_byte_can_move` | rewritten; the `{0, 1}` bound was an artifact of the swap, and the replacements assert the property rather than a numeral |
| `docs/hardware-tests/system-id-0456-bit6-divisor.md` §1 and §5 | "write the quotient's high byte", and §5's "a run that comes back mostly `unexplained` is the model and the machine disagreeing in the open" | corrected in place, each with a dated correction paragraph inside the section. No new heading: `check_no_append_logs.py` fails a `##` that names a merge, and a `*(Superseded …)*` outside `docs/findings/` |
| `ec/annotations/registers.yaml`, `XDATA_0448`, `XDATA_0449`, `SYSTEM_ID` | described the division without saying which byte was stored | corrected in place. **No `status:` moved** — nothing here is a live observation, and `present-untested` is what both entries already said |
| `ec/annotations/xdata-0400-045f.md` §9 | "`0x0448` is the battery voltage divided by 100, `0x0449` the battery current divided by 100" | **left deliberately.** Byte-ambiguous rather than false, and loose under *both* readings, so there is no sentence here the swap falsifies. Cited from this write-up instead of churning a long shared page |
| `ec/decompiled/bank1/*.c`, `ec/ghidra/c-digests.csv` | plate comments generated from the CSV rows above | regenerated, never hand-edited |

## The derivation

`ec/decompiled/bank1/A5E6.asm`, sixteen rounds of:

- **`0xA5EE`-`0xA5F9`** shift `R1`, `R2`, `R6`, `R7` in that order with the
  carry chained, so the dividend is `R7:R6:R2:R1` and **`R1` is the low
  byte**. The rule that fixes this: in a carry-chained shift, whichever
  register is shifted first is the low one.
- **`0xA5FA`-`0xA608`** subtract `R3:R4` from `R6:R7` into `DPH:DPL`; `0xA603`
  `cpl CY` and `0xA604` `jnc` keep the difference only when the subtract did
  not borrow, so the compare's outcome is still in `CY` at `0xA60A`.
- **`0xA60A`-`0xA60F`** shift that bit into **`R0`**, then `R0`'s carry-out into
  `R5`. `R0` is shifted first, so **`R0` is the low accumulator**.
- **`0xA613`-`0xA61C`** copy `R5`→`R2`, `R0`→`R1`, `R7`→`R4`, `R6`→`R3`.

**So `R1` is the low byte and `R2` the high one, and `R3:R4` is the
remainder.** The generated `A5E6.c` already agreed in its last four
statements; only its plate comment repeated the gap.

Three committed rows corroborate the direction independently of the shift
order, and each is a fact about a *caller*, so the correction is not resting
on one reading of one function:

- `0xF436` (`halve_sum_into_044c`) reads `R2` at `0xF44B`, and on it being
  nonzero overwrites `R1` with `0xFF` at `0xF44E`. That is a **clamp**, and a
  clamp only coheres one way round: the byte that normally reaches the store
  is `R1`, and `R2` is the overflow flag. Under the swapped reading the same
  three instructions would overwrite the high byte and leave the stored byte
  untouched — not a clamp. `0xCC2D` has the identical shape at `0xCC6C`.
- `CB80` says it stores "the low byte of the quotient", over `mov A, R1` at
  `0xCBA5`.
- `CB1F` says "from the low byte q of the quotient", over `mov A, R1`.

`0xD37F` corroborates from the operand-order side: at `0xD40C` and `0xD455`
it does `mov 0x04,0x02` / `mov 0x03,0x01` — `R4`←`R2`, `R3`←`R1` — the
epilogue's own low-word-first order, passing the whole 16-bit result on.

## The two conventions, and why the swap was easy

The firmware uses **both** register conventions, and they belong to different
helper families. The rule is common — whichever register a helper touches
first is its low byte — and the answers differ:

| helper | first touched | so |
|---|---|---|
| `0x8844` `ror16` | `R2` | `R2` is low, `R1` high |
| `0x8854` `add`, `0x885B` `subb` | `R1` (combined with no carry-in) | `R1` is low |
| `0xA5E6` | `R1` (shifted first) | **`R1` is low** |

`system_id_probe.py` applied the `0x8844` family's reading to the `0xA5E6`
family. **This is the one piece of context a future reader needs**: the rule
does not transfer between helpers even though it is the same rule, and
`a5e6_quotient.py`'s default mode prints the derived order for each of the
four so the next helper is a lookup rather than a guess.

## The capture

The capture is the discriminator, and it was already committed.
`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` has `0x0449`
across `0x22`-`0x5A`.

```console
$ python3 ec/tools/a5e6_quotient.py --capture \
    evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv
  pairs nearest-in-time: 238; distinct 0x0449 values observed: 46
  0x0449 spans 0x22-0x5a
  divisor 0x22 high-byte reading (R1): 1 distinct byte(s) reachable, 0 of them in the observed set
  divisor 0x22 low-byte reading (R1): 47 distinct byte(s) reachable, 43 of them in the observed set
  divisor 0x44 high-byte reading (R1): 1 distinct byte(s) reachable, 0 of them in the observed set
  divisor 0x44 low-byte reading (R1): 26 distinct byte(s) reachable, 8 of them in the observed set
```

The qualitative claim reproduces decisively: **under the high-byte model the
reachable set is `{0x00}`, and not one of the 46 observed `0x0449` values is
in it.** That is what the procedure reported as "all 237 of its gradeable
values in `unexplained`", and it was the model, not the machine.

Three calibrations on that measurement, because the numbers invite more than
they carry:

- **Reachability is not a match.** Pairing the change log nearest-in-time does
  not align two bytes that were not written at the same instant. What this
  establishes is that the observed values are *possible* under the corrected
  reading from the capture's own inputs, and that they were not possible at
  all under the old one. It does not establish that any particular sample was
  produced by either arm, and R7's origin is still unestablished.
- **The recipe is pinned, the issue's counts are not reproduced and were not
  targeted.** The issue quoted 25 and 21 distinct bytes from a 30-pair recipe;
  the tool uses every `0x0449` row in the capture and prints what it derives.
  Nothing here was written to hit a figure from the issue.
- **The divisors do not *stop* overlapping.** Over the masked input space
  (`lo` 0-255, `hi` 0-3) a handful of pairs give the same byte under both, and
  all of them are the degenerate near-zero region where both quotients are
  below the divisor. The honest claim is *near*-non-overlap, which is what
  makes the probe's per-sample `implied` column discriminating rather than a
  foregone conclusion. `test_system_id_probe.py` asserts the property, not the
  numeral.

## Tried and rejected: `0x044C` as a second discriminator

`0x044C` looked like an independent check: it is the busiest byte on the
`0x0400`-`0x045F` page in the capture — 247 changes, spanning `0x44`-`0x93`,
ahead of `0x0449`'s 238 — and `halve_sum_into_044c` computes it from
`0x0449 × 0x0448`. It is **not** the busiest byte in the capture as a whole:
counting the `new` column per address over the file's 4 960 rows, `0x0566`,
`0x06CF`, `0x06D6`, `0x06E4`, `0x06F8` and `0x06F9` each change 260 times and
`0x060C` 256, so `0x044C` ranks eighth. **It does not discriminate.**
`0xF416`'s second arm writes the constant `0xBE` (190), so the byte is
`0x0449 × 190 / 100` — and that product's low byte spans `0x40`-`0xAB` across
the observed `0x0449` values under **either** reading. The capture carries no
`0x0448` at all, so the product cannot be evaluated from it in any case.
Recorded because a rejected discriminator is worth as much as an accepted
one: it is the difference between "the capture agrees" and "we checked a
second thing and it did not speak".

## `0x0449` has no second writer

The issue asked that this be closed rather than left as a caveat. Both
writers are inside `0xF3D7` (`0xF3EB`/`0xF3EE` and `0xF411`/`0xF414`), and
the only other `0x0449` DPTR loads in the tree are reads (`0xF436`, and
bank0 `BE15`). `a5e6_quotient.py --callers` reports every `lcall 0xA5E6` site
in `ec/annotations/bank-call-targets.csv` and confirms each against the
firmware image rather than against the census's own target column. **A second
writer is not available as an explanation, and the question is closed.**

## What this does not claim

- **No live evidence.** Nothing was read back, no register was exercised, and
  no EC or Windows machine was reachable: this is a static correction over
  committed bytes. The procedure stays `not run` and issue #174 stays the run.
- **No `status:` moved.** `XDATA_0448`, `XDATA_0449` and `SYSTEM_ID` remain
  `present-untested`, which is what they already said.
- **Not #221.** Whether the byte counts *are* mA/100 is a separate open
  question and this does not answer it. Under the corrected reading `0x0449` ∈
  `0x22`-`0x5A` is 3 400-9 000 mA *if* `0x0434`/`0x0435` is mA — consistent
  with #221 and settling nothing about it.
- **R7's origin is still unknown**, and so is which arm produced any given
  capture sample. The correction makes the `implied` column discriminating so
  a future live run *can* answer the bit-6 question; it does not answer it.
- **`0xE715` has no listing.** The census names it as an `lcall 0xA5E6` and the
  firmware image holds it, but it sits in an unexported gap between `E6CB` and
  `E722`. Seeding a function for it would need `--mode rebuild-project`,
  which writes the committed Ghidra database; the tool reaches it from the
  image bytes instead. It is *decoded and unlisted*, which is not the same as
  missing — and the distinction is `CLAUDE.md`'s, not a hedge.

## What is left open

- **#221**, what the byte counts. Adjacent, not replaced by this.
- **R7's origin**, and the branch selector `0xF3D7` branches on.
- **Which arm a given sample took** — the open question for a live run.
- **`0xE715`'s enclosing function**, which a rebuild-project pass would seed.
