# The charge-path staging word at `0x0834`/`0x0835` and the word it is compared against (issue #715)

**Nothing here was observed on hardware.** No register was read, written or
read back, no byte was watched move, and no site was seen run. This is a
static reading of the committed listings under `ec/decompiled/` and of
committed scans run against the committed image
`ec/firmware/GMxMGxx_11.800`. A `write` in the census is an instruction that
stores to an address, not evidence the EC acts on it, and "not found by this
method" is never "absent" — `ec/annotations/registers.yaml`'s own header says
so, and this file does not restate it as settled fact.

What the two words are is a shorter answer than what they are taken to be.
Four routines read and write `0x0834`/`0x0835` and agree on which side of a
zero test writes. Three of them also write `0x0836`/`0x0837` in the same block,
immediately before, and set two bits of `0x0832` in the same order. That
ordering is what this file establishes, by address, from bytes. What the pair
is *for*, whether `CHARGE_TARGET_MV` is involved in the way the addresses
suggest, and whether a difference between the two decides anything downstream
are all left open, and section 5 says so in the words the naming uses.

`ec/annotations/registers.yaml` now carries one `present-untested` entry per
word — `CHARGE_STAGE_WORD` and `CHARGE_STAGE_CMP_WORD` — with the per-program
`static_refs` split, and `ec/ghidra/xdata-symbols.csv` is regenerated from
them. `ec/tools/test_0834_charge_stage_word.py` pins the byte facts below.

## 1. The two words, and what made them words

Both are read and written through the shared pair helpers, six bytes of bank1
code each. `write_r3r4_to_xdata_pair`
(bank1 `0x889E`) is `mov A, R3 / movx @DPTR, A / inc DPTR / mov A, R4 /
movx @DPTR, A`, and `read_xdata_pair_to_r3r4` (bank1 `0x8892`) is the mirror
image into R3 and R4. The `inc dptr` between the two halves is the whole of
the byte order on that path: **on the helper path `0x0834` is the low byte and
`0x0835` the high.**

**The byte order is not settled for the words as a whole.**
`dispatch_0832_event_bits` (bank1 `0xA750`) reads them one byte at a time with
no helper — `0xA787 mov DPTR,#0x834 / movx A,@DPTR / mov R6,A`, then
`0xA78C mov DPTR,#0x835 / movx A,@DPTR / mov R7,A` — and whether that call
takes them high byte first is not established here. `load_r6_r7_from_04a3_04a2`
(bank0 `0xBAE7`) reads `0x04A3` into R6 and `0x04A2` into R7, so R6:R7 is
high:low in *that* routine; nothing committed says the same convention holds
at `0xA787`. This is why both symbols are indexed by address order
(`CHARGE_STAGE_WORD_0`, `CHARGE_STAGE_WORD_1`) and carry no `_LO`/`_HI`:
`gen_xdata_symbols.py`'s own docstring calls a wrong-endianness suffix baked
into a symbol "an overclaim in the least defensible place — the name will
outlive the note that corrects it", and here the note and the symbol would
disagree rather than the symbol explaining itself.

The 16-bit compare the guards branch on is `cmp_r3r4_against_r1r2_16bit`
(bank1 `0x8863`): `clr CY / mov A,R3 / subb A,R1 / mov A,R4 / subb A,R2`,
carry out meaning the first operand is the smaller. It then returns `A=0` and
carry clear only when the first operand is exactly `0x0001`, and `A=1`
otherwise. The call sites test the accumulator's bit 0 in one place and the
carry in another, which is what that special case is for.

## 2. The routines, and what each does with the zero test

All of them are in bank1 and named in `ec/annotations/ghidra-functions.csv`.

### `stage_0577_against_0834_0836` — bank1 `0xBABF`

The routine's own listing ends at `0xBB3C`, and the zero branch leaves it. At
`0xBAE6` it does `jz 0xBB40` when the word read through
`read_xdata_pair_to_b_and_a` is zero, and the block that does the staging is
outside `stage_0577_against_0834_0836`'s own listing.

> **SUPERSEDED 2026-10-05, on main (#1849).** This section originally read
> that `0xBB40` was **in no committed listing**, falling in the gap between
> `forward_to_bd20_bb3d` (ending `0xBB3F`) and `FUN_CODE_bba4` (at `0xBBA4`),
> with no `.asm` and no `.c` to cite. That was true of the tree this change was
> written against and is not true now: main seeds `0xBB40` as
> `stage_0834_from_0403_threshold_and_0497` (bank1/BB40.asm, 0xBB40-0xBBA3,
> `docs/findings/0400-045f-site-owners.md`), so the block has an enclosing
> export and the staging is now readable in a committed listing. The withdrawn
> text is left as it was written; what follows supersedes it. The bytes
> transcribed below are unaffected and the committed listing agrees with them
> instruction for instruction, which is the one thing this section's method
> could not have claimed for itself while the block was unlisted.

The bytes below are read from the image and are now also the committed listing's
own, so they can be cited as `ec/decompiled/bank1/BB40.asm` as well as pinned
by the suite.

The listed half compares. With the word non-zero it compares the word against
the literal `0x0180` (`0xBAF5`, again at `0xBB08` — the same two operands
loaded into the same registers, so the second compare returns what the first
did and changes nothing), and when the word is not below `0x0180` it goes on to
compare `0x0836`/`0x0837` against `0x3138`, or against `CHARGE_TARGET_MV`
`0x0522`/`0x0523` when bit 0 of `0x0497` is set (`0xBB10`-`0xBB2D`). A borrow
on either leaves through `0xBB3D`, which is a one-instruction `ljmp` to
`0xBD20`. Otherwise it writes `(XDATA 0x0491 and 0xC0) or 3` to `0x0491`.

### The block at bank1 `0xBB40`, listed as `stage_0834_from_0403_threshold_and_0497`

This is the word being staged, and it is the first of the three sites below:

```
BB40  90 31 38   mov   DPTR, #0x3138
BB43  ac 83      mov   R4, DPH
BB45  ab 82      mov   R3, DPL          ; R3:R4 = 0x3138
BB47  90 04 97   mov   DPTR, #0x0497
BB4A  e0         movx  A, @DPTR
BB4B  30 e0 06   jnb   0xE0, 0xBB54
BB4E  90 05 22   mov   DPTR, #0x0522
BB51  12 88 92   lcall 0x8892           ; the 0x0497 test sent us here
BB54  90 08 36   mov   DPTR, #0x0836
BB57  12 88 9e   lcall 0x889E           ; <-- the compare word is written first
BB5A  90 08 32   mov   DPTR, #0x0832
BB5D  e0         movx  A, @DPTR
BB5E  44 02      orl   A, #0x02
BB60  f0         movx  @DPTR, A         ; <-- and bit 1 before bit 0
BB61  90 04 97   mov   DPTR, #0x0497
...
BB7A  90 01 80   mov   DPTR, #0x0180
BB7D  ac 83      mov   R4, DPH
BB7F  ab 82      mov   R3, DPL
BB81  90 08 34   mov   DPTR, #0x0834
BB84  12 88 9e   lcall 0x889E           ; <-- and the staging word second
BB87  90 08 32   mov   DPTR, #0x0832
BB8A  e0         movx  A, @DPTR
BB8B  44 01      orl   A, #0x01
BB8D  f0         movx  @DPTR, A
BB8E  22         ret
```

`0xBB7A` and `0xBB8F` are the arms of the `0x0497`/`0x0539`/`0x0403` test and
are the same instruction sequence byte for byte, so that test has no
observable effect — which is the reading `stage_0577_against_0834_0836`'s own
annotation already records.

The `jnb 0xE0` and `jb 0xE0` operands above are written here as the listing
spells them, and the branch is read as a test of bit 0 of the byte just read,
which is what `stage_0577_against_0834_0836`'s annotation already says. That is
not settled by the bytes alone: `dispatch_0832_event_bits`'s own annotation
records that on the instruction stream such an operand is a bit address in
internal RAM `0xE0` rather than a mask on the accumulator, and that its listing
does not settle which the hardware means. This file does not re-open that
question; it follows the annotation, and the ordering claims below do not
depend on the answer: both successors of the `0xBB4B` test converge on the
store at `0xBB54`, and both arms of the later test store the same `0x0180`.

### `guard_then_store_pair_0834` — bank1 `0xBF3A`

Gated on bit 7 of `0x08E2`, it clamps its R5:R6 input and then branches on the
word. **The 0x0400 it clamps against is the immediate, not the register at
that address**: `0xBF42 mov DPTR,#0x400 / mov R3,DPL / mov R4,DPH` builds
`R3:R4 = 0x0400` out of DPTR's own bytes, and there is no `movx` anywhere in
`0xBF42`-`0xBF58`. The clamp is a constant ceiling, not a value the pack
reports, and nothing in these instructions ties either word to a unit.

Its zero branch (`0xBF96`) is the second staging site, and it is unconditional
about the source — it reads `CHARGE_TARGET_MV` and never tests `0x0497` or the
`0x3138` literal:

```
BF96  90 05 22   mov   DPTR, #0x0522
BF99  12 88 92   lcall 0x8892
BF9C  90 08 36   mov   DPTR, #0x0836
BF9F  12 88 9e   lcall 0x889E           ; the compare word
BFA2  90 08 32   mov   DPTR, #0x0832
BFA5  e0         movx  A, @DPTR
BFA6  44 02      orl   A, #0x02
BFA8  f0         movx  @DPTR, A         ; bit 1
BFA9  ee         mov   A, R6
BFAA  fc         mov   R4, A
BFAB  ed         mov   A, R5
BFAC  fb         mov   R3, A
BFAD  90 08 34   mov   DPTR, #0x0834
BFB0  12 88 9e   lcall 0x889E           ; the staging word
BFB3  90 08 32   mov   DPTR, #0x0832
BFB6  e0         movx  A, @DPTR
BFB7  44 01      orl   A, #0x01
BFB9  f0         movx  @DPTR, A         ; bit 0
```

Its non-zero branch compares and returns without writing: the word against the
clamped R5:R6, then `0x0836`/`0x0837` against `CHARGE_TARGET_MV` (loaded twice
under the `0x0497` bit 0 test, the second load redundant).

### `FUN_CODE_bc05` — bank1 `0xBC05`

A third copy of the same shape, and **not annotated**: it is a call-target seed
with the generic name `FUN_CODE_bc05`, so the third staging site has no comment
of its own anywhere in the tree. Its zero branch (`0xBC77`) is `0xBF96` with a
`0x3138`-or-`CHARGE_TARGET_MV` selection in front of it — the two are the same
bytes from the `mov DPTR,#0x522` onward. Its non-zero branch (`0xBC40`) is the
same compare pair as `stage_0577_against_0834_0836`'s, and leaves through the
`0xBF93` forwarder. Naming it is its own issue; it is recorded here because the
claim the entry makes rests on a pattern replicated three times, and two of
the three are annotated.

### `clear_0834_word_when_nonzero` — bank1 `0xBD20`, and `reload_083e_when_0834_is_zero` — bank1 `0xC4AF`

The clear reads the word through `0x8898` and returns if it is zero. Otherwise
it writes `0x02` to `0x08E4`, zeroes the word by building `R3:R4 = 0x0000` out
of `DPTR = 0x0000`'s own bytes and storing it through `0x889E`, and sets bit 0
of `0x0832`. Both `0xBB3D` and `0xBF93` are one-instruction forwarders to it,
so every "the word no longer matches" branch in the routines above converges
here.

`reload_083e_when_0834_is_zero` runs the other way round from what its name
suggests at a glance, and the bytes settle it: `0xC4B7 jz 0xC4CB` leaves for
the reload when the word is **zero**, and the fall-through decrements `0x083E`
when it is not, setting bit 0 of `0x0832` on the wrap. The reload is
`0xC4CB mov DPTR,#0x83e / mov A,#0x3c / movx @DPTR,A`.

## 3. What is new here, as distinct from what the annotations already said

Two things, both from the bytes rather than from the comments.

**The co-write is replicated, not incidental.** At all three staging sites
`0x0836`/`0x0837` is written first, `0x0832` bit 1 is set next, the staging
word is written after that, and bit 0 last. The annotations describe each
site's own instructions; none of them says the ordering repeats. The natural
reading — that `0x0836`/`0x0837` records the charge target as it stood when
`0x0834`/`0x0835` was staged, and the later compares ask whether it has moved
since — fits that ordering, and it is **not** established by it. A neutral
reading fits it equally: the two are latched values, the compares ask whether
the latched one still matches what is live now, and neither word has anything
to do with charge.

**One of the three sites is outside the listing of the routine that reaches
it.** This section originally read that the block at `0xBB40` had **no listing
at all** — it lay in the gap between `forward_to_bd20_bb3d` and
`FUN_CODE_bba4`, so the half of `stage_0577_against_0834_0836` that actually
stages the word was in no exported `.asm` and no exported `.c`, and the text
made that an argument for seeding `0xBB40` as a function of its own. Main has
since done that seeding (#1849): the block is
`stage_0834_from_0403_threshold_and_0497`, bank1/BB40.asm, and the listing is
byte-identical to the transcription §2 gives. So the staging is now readable in
a committed listing, and what remains true is narrower: **it is still not part
of `stage_0577_against_0834_0836`'s own decompile**, whose listing ends at
`0xBB3C`, so someone reading that routine to see the staging still does not see
it there and has to follow the `jz` into `0xBB40`. That is a property of where
the branch lands, not an absence of coverage, and it is the reason this file
cites the block by address rather than by the enclosing function's name.

## 4. What was already done — `0x04A2`/`0x04A3`

The issue this grew out of lists `0x04A2`/`0x04A3` alongside the four staging
addresses. **Both already have a row.** `ec/annotations/registers.yaml` names
them `PACK_TEMP_DK (pack temperature, decikelvin)`, `present-untested`, with
the same per-program `static_refs` split, added by issue #1425 — that entry is
the precedent for the shape used here. The annotations the issue lists as
saying the addresses are undocumented already say the opposite: each reads
"None of these addresses is documented in `ec/annotations/registers.yaml`
**except** `0x04A2`/`0x04A3`, which it names `PACK_TEMP_DK`". The issue was
filed from the pre-#1425 tree, so that half is already done and no row was
re-added.

`0x0832` is named in the same list and is **left out deliberately**. It is a
bit-flag byte with a seven-arm dispatcher at `dispatch_0832_event_bits` and
its own unresolved reading — that annotation records that the `.c` reads its
tests as masks on the byte just loaded while the instruction stream's operands
are bit addresses in internal RAM `0xE0`, and that the listing does not settle
which the hardware means. Naming a byte on that basis would mean a
whole-dispatcher claim resting on evidence about two words.

## 5. What these two words are **not** shown to be

- **No unit is claimed.** `0x0180` is 384, `0x0400` is 1024 and is a clamp
  ceiling rather than anything the pack reports, and `0x3138` is 12600. None
  of the three is demonstrably the same quantity as a millivolt target, and
  `CHARGE_TARGET_MV` has been read live as 16400, which is not `0x3138`. So
  the two sources `0x0836`/`0x0837` can be loaded from are not shown to be the
  same quantity either.
- **The association with the charge target is an association.** It is a real
  one in these listings — `CHARGE_TARGET_MV` is an operand in the routines
  that stage the pair, and at two of the three staging sites the bit 0 of
  `0x0497` test selects it as the source of the `0x0836`/`0x0837` copy — but
  `guard_then_store_pair_0834`'s own annotation says in as many words that
  "nothing in these instructions ties the compares to that meaning", and the
  names here say the same thing. Neither name asserts a mechanism.
- **Nothing is shown to be a limit.** The other operands are the literal
  `0x0180`, the clamped `R5:R6`, and `CHARGE_TARGET_MV` or the literal `0x3138`;
  what a difference between the two words decides downstream is not established
  here.
- **`present-untested` is the scan's grade.** It says the EC references the
  bytes and that nobody has exercised them, which is a statement about the
  census and not about the hardware.

**The PD half gets no name.** `ec/ghidra/xdata-symbols.csv` carries
`programs` as `bank0;bank1` for every row and never `pd`, the exporter applies
XDATA labels to the bank programs only, and no `pd` decompile spells either
name — the suite asserts all three. What does change is
`ec/ghidra/c-asm-counterpart.csv`, whose `symbol` column is a lookup of the EC
name for an address and so picks the new names up on the `pd` rows that reach
these addresses. That is the column's existing shape rather than a new claim:
it already reads `USB_C_POWER_PRIORITY` and `GFID` on `pd` rows, and its
`spellings` column beside them still records the address the PD text actually
uses.

The question that matters for a charge cap — whether the charger acts on
either word at all — needs the physical machine and is not answered here. No
hardware and no Windows machine is reachable from a cloud runner, and
`CHARGE_TARGET_MV` being host-read-only (`registers.yaml`, its own note) means
the staging path is not the place a Linux charge cap would be written anyway.

## 6. The re-export this change does not carry

Adding the rows renames the symbols in `ec/ghidra/xdata-symbols.csv`, and the
names do **not** reach `ec/decompiled/**.c` until the export runs again — the
committed `.c` files still spell these bytes `DAT_EXTMEM_0834`. The export was
run, and its output was discarded, for a reason worth recording.

`ec/tools/build_ec_decompile.py --check` recomputes the cross-decoder report
against the committed `ec/ghidra/cross-decoder.csv`, and a re-export moves
three sampled rows — bank0 `BD5D`, `BD6B` and `E024` — from `agree` to
`disagree`. That is the one direction `--self-test` refuses, because a widening
of the matcher cannot produce it and a rename that reaches the export is
supposed to be readable by it. The cause is not these four addresses. It is
that `names_an_address()` reads only the two spellings that carry their own
address (`DAT_EXTMEM_07d6`, `XDATA_1664`) plus hex literals, and the fan-RPM
renames reached `xdata-symbols.csv` without a re-export, so a re-export today
is the first time `MAIN_FAN_RPM_0` and `SECOND_FAN_RPM_0` appear in a `.c` and
the comparison cannot read them. `BD5D.c` becomes `return MAIN_FAN_RPM_0 +
(((MAIN_FAN_RPM_1 < 100) << 7) >> 7);` — which **does** name `0x0464` and
`0x0465`, so recording it as `disagree` would put a false row in a census.

Regenerating the report is not the way round that. It would satisfy
`--check`, and `--self-test`'s ratchet would then compare the regenerated
report against the same regenerated run and see nothing move — which is the
check being satisfied by regenerating past it rather than by fixing anything.

Widening the matcher to read a register's real name does fix it: measured, it
moves the three rows back and moves others only from `disagree` to `agree`.
But that changes what a committed census means, and
`docs/findings/cross-decoder-disagreement-population.md` measures the
`disagree` bucket over exactly this report while
`ec/ghidra/cross-decoder-disagreement.csv` records a per-row cause for each of
its rows — both of which a widening moves. That is its own change with its own
write-up rather than something to fold into a pull request about naming two
registers. **Until it lands, a re-export of the EC decompiles will turn the
cross-decoder report red**, which is worth knowing before the next branch
tries one.

Two consequences here, both stated rather than left to be found. The committed
`.c` files carry each function's annotation comment, so the sentence this
change corrects is corrected in `ec/annotations/ghidra-functions.csv` and not
yet in `BABF.c`, `BD20.c` or `BF3A.c`, which still carry the pre-naming
wording. And `spelled_as` in
`ec/annotations/xdata-registers.csv` still reads `DAT_EXTMEM+pair-literal` for
the EC half of these four, for the same reason; the census's `name` column
does carry the new names, because that column is read from the symbol table
rather than from the `.c`. A stale export is a state this repository is
already in — the fan-RPM names above are one — and nothing here hand-edits a
generated `.c`, which `CLAUDE.md` forbids and `ec/ghidra/c-digests.csv`
catches.

## 7. The new suite

`ec/tools/test_0834_charge_stage_word.py` pins the byte facts above against
`ec/firmware/GMxMGxx_11.800`: the pair helpers, the 16-bit compare's
special case, the clear, the countdown's direction, the clamp's immediate, the
staging order at all three sites, the two identical arms at `0xBB7A`/`0xBB8F`,
and that `0xBB40` is outside `stage_0577_against_0834_0836`'s own listing.
Alongside those it holds the
relations between `registers.yaml`, `xdata-overrides.csv` and the generated
`xdata-symbols.csv`, that the PD half of the census carries no EC register
name, that the PD decompiles spell none of them while
`ec/ghidra/c-asm-counterpart.csv` records the EC lookup beside the spelling
the PD text uses, and that the comments this change touches no longer call
these addresses undocumented while keeping the hedges they already carried.

Every case in it is static. None of them is a behaviour.