# The opcode table's coverage and a differential decode: 254 of 256 rows, 0 disagreements against two decoders that are not independent — and 8 against the manual, which is the findingndependent

(2026-09-27, issue #37. Static reading of committed files, plus one `r2 -a 8051`
subprocess. No capture opened, no EC, no hardware, no Windows.)

Two numbers about `ec/tools/disasm8051.py`'s `OPCODE_LEN` were assumptions in
this repository and are now measurements in it. **How much of the table the
firmware exercises**: 254 of 256 opcode values appear at an instruction start in
`ec/decompiled/`, and the `--self-test` corpus reaches **20** of them. **How many
lengths are wrong**: **0** — out of 45,643 instruction starts against the
committed Ghidra listings, **0** out of a further 114,953 instruction positions
against a linear `r2 -a 8051` walk of all three images, and **0** of the 255
rows the MCS-51 manual assigns against the manual itself.

The table's own oracle is `--self-test`, and that oracle pins 20 rows. The other
236 were read one at a time by whoever wrote them, which is a real method and not
a reproducible one. The gap between "the table is 256 entries" and "236 rows were
checked by somebody else" is now a number rather than a habit, and the number is
in a script anyone can re-run.

**What the first two zeros do not mean, stated first because it is the whole
correction below.** Ghidra and r2 are not two independent readings of the opcode
map. They share a lineage, this repository already records where that lineage
departs from the MCS-51 manual (`0xA0`/`0xB0`), and where they share a departure
their agreement is one decoder counted twice. So "0 disagreements against two
decoders" was never "0 disagreements against two", and this document said so for
one revision. A third oracle — the manual, transcribed into `MCS51_LEN` — is now
what the two decoders' agreement is measured *against*, and the rows the manual
assigns nothing to are reported as a third state rather than as agreement. That
section is [below](#the-two-decoders-are-not-independent-and-what-the-manual-says-about-the-row-nothing-corroborates);
the corrections to the phrasings this document previously used are left in place
beside it rather than edited away.

Three oracles, then: two decoders that reach different ground, and one table
that is the only route here which can contradict both of them.

*(Corrected 2026-09-27, review of #67. **The manual is the only route that can
contradict both decoders on 247 of the 255 rows it assigns, and on eight it is
not.** `MCS51_LEN` was transcribed with `2` across `0xA8`-`0xAF` — a
byte-for-byte copy of the `0x78` row — where the instruction set has `XCH A,Rn`
at 1, the same instruction the table carries at 1 in the `0xC8` row and the same
two bytes `disasm8051.py` prints for `0x78` and `0xA8` alike. On those eight
rows the third oracle was agreeing with the two decoders it exists to contradict,
so the headline zero was 247 rows of corroboration and 8 of echo. **The honest
headline is 0 disagreements on the 247 rows where the manual is independent and
8 where it contradicts all three tools**, and `--divergence` now prints the
eight by name. The rows are left visible, and the fix is in
`SPOT_CHECKS`, which had no entry anywhere in the block — the gap that let a
256-byte literal keep a block wrong.)*

## The two decoders, and why the listings are the primary one

**The committed Ghidra listings.** `ec/decompiled/` holds Ghidra 12.1.3's own
disassembly as 2,711 `.asm` files across four programs, and every row carries its
own fixed-width byte column. Measured on the committed tree that is **45,643
instruction rows**. Each row's length is Ghidra's; the firmware bytes behind it
are in `ec/firmware/GMxMGxx_11.800`, and `verify_reassembly.py --check`
independently confirms all 45,643 against the image. So a length disagreement
here is a disagreement about the firmware, not merely about the listing.

This is a route to an opcode length that never saw `disasm8051.py`, needs nothing
installed, and is reproducible from committed files alone. It is the primary
decoder oracle for exactly that reason.

**`r2 -a 8051`.** `--r2-diff` linearly walks each whole 64 KiB program from its
first byte — 39,371 instructions in bank0, 39,187 in bank1, 36,395 in the PD
image, **114,953 positions in all**. It reaches opcode values the listings never
place: 254 of 256 in bank0, 256 in bank1, 255 in the PD image, and **256 of 256
across the three**, so between the two routes every row of the table has *a*
decoder behind it.

> **Corrected.** This paragraph previously ended "so between them the two routes
> put a **second** decoder behind every row of the table." That is the claim the
> rest of this document could not support, and it is wrong in the way that
> matters: a second decoder is a decoder whose disagreement would be visible, and
> these two never disagree. "A decoder" is what the measurement earns; "a second"
> was an assumption about independence dressed as a count. See
> [the section below](#the-two-decoders-are-not-independent-and-what-the-manual-says-about-the-row-nothing-corroborates).

It is also the disassembler the hand transcriptions in `SELF_TEST`, `REL_SITES`
and `BIT_SITES` were taken from. That is a reason to treat r2's agreement as
*weaker* evidence than Ghidra's, not stronger: where the two differ, the hand
transcriptions side with r2, so r2 cannot independently overturn a `--self-test`
expectation. The listings have no such relationship to the code under test, which
is why they lead and r2 follows.

> **Corrected.** An earlier revision of this sentence called r2 "strictly
> stronger" and, three sentences later, called its agreement "weaker evidence."
> Those are two different questions — how many rows it reaches, and how much its
> agreement is worth — and the document answered them in the word "stronger"
> where it meant the first and "weaker" where it meant the second. r2 reaches
> more rows and is the weaker oracle. Neither word survives as a summary of both,
> so neither is used: row coverage is a column and evidence weight is prose.

The two do not overlap completely, and the gap is the interesting part.

## The two decoders are not independent, and what the manual says about the row nothing corroborates

The premise of the whole comparison is that agreement between two decoders is
evidence the table is right. That premise is false here, and this repository
already says so in one place: `docs/findings.md`'s `0xA0`/`0xB0` entry records
that Ghidra's SLEIGH, r2 and `sdas8051` all put `ORL C,/bit` at `0xA0` where the
MCS-51 manual has `ANL C,/bit`, and that the re-encode "passes **because the
decoder and the assembler agree, not because either is right** — the one shape
of hole this tool structurally cannot see." A differential that only ever
compares those three against each other cannot see that hole either, because
none of them disagrees with any other.

So `MCS51_LEN` in `ec/tools/opcode_coverage.py`: instruction length for all 256
values transcribed from the MCS-51 instruction set, with `0` for a value the
manual assigns no instruction to. Not a decoder, not a subprocess, and not
derived from `disasm8051.py` — which is what makes it the one route that can
contradict the other three.

Measured on the committed tree:

- **`0` rows of the 255 the manual assigns disagree with `OPCODE_LEN`.** On every
  row where the manual has an opinion, the table has the same one.
- **`1` row the manual assigns nothing to: `0xA5`.**

That one row is the answer to "is the table wrong?", and the answer is *not
knowable from any decoder in this tree*. `OPCODE_LEN` says 1 byte, and both
decoders also say 1 byte — but the manual has no row to have said it, so the
agreement is a shared convention, not a corroboration:

| row | `OPCODE_LEN` | listings | r2 | MCS-51 manual | what the 1 byte rests on |
|---|---|---|---|---|---|
| `0xA5` | 1 | *no listing start* | `type: invalid` | *unassigned* | the table alone |

> **Corrected.** Two revisions of this section named **three** rows the manual
> leaves unassigned — `0x96`, `0x97` and `0xA5` — and built the shared-lineage
> finding on the first two of them, next to the `X a,@Ri` ladder quoted below.
> That was a transcription error in `MCS51_LEN`, not a property of the manual,
> and the finding it supported does not exist. The MCS-51 `0x90`–`0x9F` row
> carries all eight `SUBB A` forms: `0x94` `SUBB A,#data` (2), `0x95` `SUBB
> A,direct` (2), `0x96` `SUBB A,@R0` (1), `0x97` `SUBB A,@R1` (1) and
> `0x98`–`0x9F` `SUBB A,Rn` (1). The transcription had read the manual's
> `X a,@Ri` family as stopping after `0x26`/`0x46`/`0x56`/`0x66` and left
> `0x96`/`0x97` at 0, where the map makes that same `+0x20` step at `0x36` and at
> `0x96` as well. So on those two rows the manual, Ghidra and r2 all say 1 byte,
> the 5 instruction starts that sit on them are corroborated by a source that is
> not a decoder, and the shared-departure example this section led with is gone:
> what is left is `0xA0`/`0xB0`, which the paragraph at the end of this section
> covers and which a length table cannot see. Every count that rested on the
> 3/253 split is corrected at its own site rather than edited here.
>
> *(Corrected 2026-09-27, review of #67. **"What is left is `0xA0`/`0xB0`" is no
> longer the whole of it, and unlike that pair a length table *can* see the other
> one.** `0xA8`-`0xAF` is a second shared departure — the decoders collapse it
> onto the `0x78` row's two bytes, and this transcription had been copied from
> that row rather than from the instruction set, so it agreed with them instead
> of contradicting them. It is the one class of error a length oracle exists to
> expose and it was in the oracle. `0xA0`/`0xB0` remain a *mnemonic* departure
> that no length table can see; `0xA8`-`0xAF` is a *length* one that one can,
> and `--divergence` now prints all eight rows.)*

It is worth saying what the error cost, because the oracle was added precisely to
be able to make this class of mistake visible. A transcription that is wrong
where it is least expected produces a *confident* number — here a count of
uncorroborated rows, and a narrative about two decoders inventing an
instruction. Both read as findings, and both were downstream of a 256-byte
literal. The `SPOT_CHECKS` in `test_opcode_coverage.py` now pins `0x94`–`0x98`
individually for the same reason it pinned `0x10` and `0x13` before: a spot
check at the ends of a block does not see a slip in the middle of it.

The `X a,@Ri` ladder is what the correction looks like from the firmware side,
and the committed listings show all of it. Five rows, each one byte and each
named by the manual at the opcode both decoders use — one site per opcode, first
by address:

```console
$ for op in 26 46 56 66 96; do grep -rhoE "^[0-9A-F]{4} +$op - - +[^;]+" ec/decompiled --include=*.asm | sort | head -1; done
0C2D     26 - -   add      A, @R0
00C1     46 - -   orl      A, @R0
0057     56 - -   anl      A, @R0
4732     66 - -   xrl      A, @R0
0403     96 - -   subb     A, @R0
```

What the five rows have in common is the operand form, not the instruction: all
five are `…, A, @R0`, all five are 1 byte, and the MCS-51 map has all five —
`ADD A,@R0`, `ORL A,@R0`, `ANL A,@R0`, `XRL A,@R0`, `SUBB A,@R0`. The same
`+0x20` slot holds `mov @Ri,#data` at `0x76`, `mov direct,@Ri` at `0x86` and
`subb a,@R0` at `0x96`, in the manual and in both decoders alike. Read as a
ladder it looks like a `+0x20` step the manual does not make, which is what the
two earlier revisions read it as.

The five rows are also how much traffic that family carries: 11, 57, 16, 6 and 4
listing starts. `0x97`, the `@R1` half of the pair, has 1, so the `0x96`/`0x97`
pair is 5 instruction starts in the committed corpus — a real amount of framing
that rests on three sources agreeing rather than on one map counted twice, which
is the whole point of having counted it.

**What the manual oracle still cannot do**, stated next to it so it is not
overclaimed the other way. It is a *length* table, and the `0xA0`/`0xB0` question
is a length table's blind spot by construction: `ANL C,/bit` and `ORL C,/bit` are
both 2 bytes, so the manual agrees with the decoders on that row and the swap
stays exactly where `disasm8051.py:177-188` leaves it. Adding a third oracle did
not settle `0xA0`/`0xB0`; it made visible that *no length oracle ever could*.
Closing that one needs a mnemonic comparison against a source that is not a
decoder, which is the same shape of work as the `mnemonic()` gap below and not
this document's.

## The two rows the listings cannot see, and what r2 says about them

`0xA5` and `0xC1` never appear at an instruction start in any committed listing.
`--r2-diff`'s whole-image walk reaches both, and both cases are worth stating
separately because they are the two different states a length can be in when
nothing in the corpus has placed the value.

**`0xC1` — the decoders disagree about the instruction and agree about its
length.** r2 decodes `0xC1` as `ajmp 0x86fa` and the like, because `0xC1 & 0x1F
== 0x01` is the `ajmp` pattern; `disasm8051.mnemonic()` calls the same bytes
`clr 0x20.0`. **Both say it is 2 bytes long**, which is the only thing this
differential measures. Which of the two mnemonics is right is **not settled
here** — the manual's map has `CLR bit` at `0xC1` and `disasm8051.py` follows
it, while r2's `ajmp` reading comes from the `op & 0x1F == 0x01` pattern, and
`clr bit` and `ajmp` are both defensible readings of these bytes, which is the
same posture `disasm8051.py:177-188` already takes about the `0xA0`/`0xB0` pair.
It does not matter to this work because both readings are 2 bytes, and it is
exactly why `--r2-diff` compares lengths and nothing else. For the `0xC1` row
alone, a text comparison would have reported eight sites in bank1 and one in the
PD image — nine, all the same disagreement, and none of them about framing. That
is *this row's* count, not the whole text comparison; the whole of it is measured
in the next section, and it is two orders of magnitude larger than nine.

**`0xA5` — r2 does not implement the opcode at all.** r2 marks it
`type: "invalid"` and gives it a length of 1, which is what `OPCODE_LEN` says
too. A decoder refusing to name an opcode is a third-party arrival at the same
conclusion from a different route than the manual `disasm8051` was written from.

> **Corrected.** This row was previously described as *pinned by both routes*,
> and that was not what the two routes did. The listings pin nothing here — no
> listing places `0xA5` at an instruction start at all, so their "not found by
> this method" is the only thing they have to say — and r2's `type: invalid` is
> one decoder declining a row, which is not a second reading of a length. The
> manual, which this document now compares against, agrees it is unassigned but
> supplies no length to agree *with*. So `0xA5`'s 1 byte rests on the table
> alone, and `--divergence` now says so in those words rather than leaving the
> row to read as corroborated.

**`0xC1` is not a new finding.** `disasm8051.py:415-417` already says this, in a
comment attached to the `TEXTBOOK_BIT_SITES` pair:

> CLR bit has no entry in BIT_SITES because this firmware contains no
> instruction-start byte 0xC1 at all (measured over every committed listing, and
> why verify_reassembly.BIT_UNSUPPORTED calls it a latent hole rather than a live
> one).

That claim was made from a byte scan; this measures it at instruction starts from
a third-party decoder, and it holds. The pairing it exists to protect — `0xC1`
and `0xC2` differing only in the opcode — is the reason `0xC1` has no live
backing at all: the corpus's `clr psw.0` case is stated from the 8051 manual,
which is the honest thing to do with an opcode the image never places.

Of the two rows the listings never place, `0xC1` is the one where the manual
oracle *does* have a length to offer — `CLR bit`, 2 bytes, the same as
`OPCODE_LEN` — and it is the only row of `0xC0`–`0xCF` that the manual assigns
while the listings never put it at an instruction start. That second half is
what makes it distinct, because all sixteen rows of the block carry a manual
length and every one of them agrees with `OPCODE_LEN`: `0xC1` is the only row
corroborated with nothing of the firmware behind it, `--coverage` giving it
`starts 0` and `agree n/a`.

> **Corrected.** This paragraph previously made `0xC1` "the only row in
> `0xC0`–`0xCF` whose length is corroborated by a source that is not a decoder",
> and that is not a distinction any row of the block has. All sixteen are
> assigned by the manual — `MCS51_LEN[0xC0..0xCF]` is `[2, 2, 2, 1, 1, 2, 1, 1,
> 1, 1, 1, 1, 1, 1, 1, 1]`, no zeros — and every one agrees with `OPCODE_LEN`,
> `0xC2`'s 180 listing starts included, so manual corroboration singles out
> nothing here. What singles `0xC1` out is the other column: it is the only row
> of the block the listings never place at an instruction start. The first half
> of the sentence, that `0xC1` carries a manual length where `0xA5` carries
> none, stands.

`0xA5` is absent from the self-test corpus and from every listing, so before
this work its length rested on the table alone — which is precisely the class of
row the issue was about.

So the honest count is not "256 rows pinned by one decoder" and not "254 rows
pinned by a third-party decoder".

> **Corrected.** That sentence — 254 rows pinned by a third-party decoder over
> 45,643 starts, the remaining 2 by r2, "the two agreeing about every length they
> both see" — read as two independent confirmations covering all 256 rows. There
> are two, not three, and they are not independent. What the 254 is: 254 rows
> where a decoder that never saw `disasm8051.py` placed the value at an
> instruction start and produced the length the table predicts. What the 2 is:
> `r2` reached both and produced the same lengths, on a map that agrees with
> Ghidra's where they overlap. The rows nothing outside this table corroborates
> are the three the manual leaves unassigned, and one of them is in each group
> above.
>
> **Corrected again, and the second correction is the one that stands.** That
> last sentence was itself built on the 3-row transcription: of `0x96`, `0x97`
> and `0xA5`, only `0xA5` is a row the manual leaves unassigned, and the
> "one of them is in each group" split fails with it — `0xA5` is one of the 2
> the listings never place, and is not among the 254. The corrected state is
> one row that neither decoder group covers, and the two groups are the 254 and
> the 2 rather than two halves of 256. The `0xA0`/`0xB0` question is unaffected
> and stays open.

The measured version, per oracle, is `--divergence`: 0 of 45,643 against the
listings, 0 of the manual's 255 assigned rows against the manual, and 1 row no
oracle can speak to.

## What a text comparison would have found, since this one does not

`--r2-diff` compares lengths because framing rests on lengths, not because the
two decoders agree on text. Scoping the mode is not the same as measuring what
is behind the scope, so here is what is behind it.

Comparing the two **first tokens** at every address r2 itself walked — the same
anchoring `walk_against()` uses, so the two framings are compared like for like
— gives **112,673 agreements against 2,214 first-token disagreements**, over the
114,887 instructions r2 named. The other 66 of the 114,953 walked positions are
ones r2 declined to name, and all 66 are `0xA5` (31 in bank0, 34 in bank1, 1 in
the PD image).

The 2,214 splits in two, and only the first of them is the `0xC1` row above:

| sites | of | shape |
|---|---|---|
| 9 | 8 in bank1, 1 in the PD image | `0xC1`: `clr bit` here, `ajmp` in r2 |
| 2,205 | 35 opcode values | `disasm8051.mnemonic()` returning `db 0x..` |
| 0 | — | any other shape of disagreement |

An earlier draft of this file said the text comparison would report nine sites
and that they were all the `0xC1` disagreement. That was wrong, and wrong in
the direction that hid the second row: 2,214, not nine, and 2,205 of them have
nothing to do with `0xC1`. Nine is this document's count for the `0xC1` row
alone.

The second row is a finding this work opens and does not close, so it is stated
here rather than folded into the count above or left implicit.
`disasm8051.mnemonic()` falls through to `return f"db   0x{op:02x}"`
(`ec/tools/disasm8051.py:297`) for **35 opcode values**, and the manual divides
them: **34 are assigned instructions in the MCS-51 map** and **1 is not** —
`0xa5`, the one value `MCS51_LEN` leaves at 0.

The full set, all 35, with the manual's own name and length for each. A paired
row is two opcode values sharing one form.

| op | MCS-51 | len | op | MCS-51 | len |
|---|---|---|---|---|---|
| `0x06`/`0x07` | `inc @Ri` | 1 | `0x56`/`0x57` | `anl a,@Ri` | 1 |
| `0x16`/`0x17` | `dec @Ri` | 1 | `0x62`/`0x63` | `xrl direct,a` / `xrl direct,#data` | 2 / 3 |
| `0x26`/`0x27` | `add a,@Ri` | 1 | `0x66`/`0x67` | `xrl a,@Ri` | 1 |
| `0x36`/`0x37` | `addc a,@Ri` | 1 | `0x72` | `orl c,bit` | 2 |
| `0x42`/`0x43` | `orl direct,a` / `orl direct,#data` | 2 / 3 | `0x76`/`0x77` | `mov @Ri,#data` | 2 |
| `0x46`/`0x47` | `orl a,@Ri` | 1 | `0x82` | `anl c,bit` | 2 |
| `0x52`/`0x53` | `anl direct,a` / `anl direct,#data` | 2 / 3 | `0x86`/`0x87` | `mov direct,@Ri` | 2 |
| | | | `0x96`/`0x97` | `subb a,@Ri` | 1 |
| | | | `0xa5` | **unassigned** | — |
| | | | `0xa6`/`0xa7` | `mov @Ri,#data` | 2 |
| | | | `0xb6`/`0xb7` | `cjne @Ri,#data,rel` | 3 |
| | | | `0xd4` | `da a` | 1 |
| | | | `0xf4` | `cpl a` | 1 |

> **Corrected, twice, in the same sentence.** This paragraph previously said
> "**34** of them are assigned instructions in the MCS-51 map", named 26 of
> them, and closed with "Only `0xa5` is unassigned." Both halves were wrong. The
> count is **32**, not 34: `0x96` and `0x97` are as unassigned as `0xa5` is, and
> the enumeration omitted them along with `0x72`, `0x76`/`0x77` and
> `0x86`/`0x87` — eight of the 34 missing, and the omissions mattered, because
> two of them (`0x96`/`0x97`) are the rows where the two decoders share a map the
> manual does not have. A list of 26 that claims to be 34 would have hidden
> exactly the finding it sat next to. The count of 35 reaching the `db`
> fall-through was always right, and the one-liner printed below regenerates the
> set; that command, not this table, is what to re-run.
>
> **Corrected a third time, and this is the split the paragraph above now
> uses.** The 32 is wrong for the same reason the 34 was: `0x96` and `0x97` are
> *not* unassigned in the MCS-51 map. They are `SUBB A,@R0` and `SUBB A,@R1`,
> 1 byte each, in the same `0x9X` row as `0x94`, `0x95` and `0x98`–`0x9F`. The
> corrected split of the 35 `db` values is **34 assigned, 1 unassigned** —
> `0xa5` alone — and the split the second correction was built on, 3 rows the
> manual leaves open, is down to 1. The 34 is not the retracted figure coming
> back: it is the same number reached the other way round, and the reason the
> first correction gave for rejecting it is not true. What that correction got
> right, and what is why the number moved twice rather than once, is that the
> enumeration underneath it was incomplete — that part stands.

> **Corrected.** "r2 gives every one of the 34 a name and marks `0xa5`
> `type: \"invalid\"`" was read as r2 agreeing that all 34 are assigned. It does
> the opposite: r2 names `0x96`/`0x97` `subb a,@Ri` and marks only `0xa5`
> `invalid`, because r2's map is not the manual's — see
> [the two-decoders section](#the-two-decoders-are-not-independent-and-what-the-manual-says-about-the-row-nothing-corroborates).
> r2 naming a value the manual leaves unassigned is the tell, not a
> confirmation. Where r2's name for one of the 32 differs from the manual's that
> is the `0xC1` question again — two defensible names for a value the walk
> reached over data — and is not settled here either.
>
> **Corrected again, on the same evidence as the third correction above.** The
> reason given in the previous paragraph — that r2's map is not the manual's at
> `0x96`/`0x97` — was the 3-row transcription again, and it does not survive it.
> On the corrected table r2, Ghidra and the manual all name `0x96`/`0x97`
> `subb a,@Ri` at 1 byte, so there is no departure there to be a tell about.
> What survives of that paragraph is the part about *why* r2's `0xA5` is not a
> second reading: it is r2 declining the opcode, not confirming a length. And
> the disagreement of names that is still open is `0xC1`, not `0x96`/`0x97`.

### The `0x3x` and `0x9x` rows a review disputed, and why all 17 are not wrong

A review of an earlier revision of this file claimed `OPCODE_LEN` is wrong on 17
rows in blocks `0x3x` and `0x9x` — `0x36 0x37 0x38 0x39 0x3c 0x3d 0x3e 0x3f 0x96
0x97 0x98 0x99 0x9a 0x9c 0x9d 0x9e 0x9f`, over 452 instruction starts — on the
grounds that Ghidra and r2 share a non-MCS-51 map there. The premise was right;
the list was not, and the difference is worth keeping in the repository because
the same question will be asked again by anyone who reads `subb A, @R0` at `0x96`
and assumes the whole `0x9x` row is suspect with it.

**15 of the 17 are correct in `OPCODE_LEN` and match the manual.** `0x36`/`0x37`
are `ADDC A,@Ri` and `0x38`–`0x3F` are `ADDC A,Rn`, all 1 byte; `0x98`–`0x9F`
are `SUBB A,Rn`, all 1 byte. The review's evidence for the `0x3x` half was that
"`addc a,@R0` is MCS-51 `0x26`" — `0x26` is `ADD A,@R0`, and `ADDC A,@R0` is
`0x36`, one row away in the very block being called wrong. Its evidence for the
`0x97` half was that "MCS-51 `0x97` is `ANL direct,bit` at 2"; there is no `ANL
direct,bit` in the MCS-51 map, and `ANL C,bit` — the instruction that looks like
it — is `0x82`. The two committed listings cited as proof agree with
`OPCODE_LEN` and with the manual, and they say so directly:

```console
$ sed -n '118p;122p' ec/decompiled/bank0/D091.asm
D165     36 - -   addc     A, @R0
D16B     38 - -   addc     A, R0
$ sed -n '80,82p' ec/decompiled/common/6A02.asm
6ACF     96 - -   subb     A, @R0
6AD0     99 - -   subb     A, R1
6AD1     97 - -   subb     A, @R1
```

`0x36`, `0x38`, `0x3E` and the whole `0x98`–`0x9F` row are 1 byte here and in
`OPCODE_LEN`; `0x30` is `JNB bit,rel` at 3 bytes in both, from the row above, and
`disasm8051.py:74,162` already gets that right. The 452 is the sum of those rows'
`starts` in the appendix below and is arithmetically right — it counts starts on
rows that are not wrong.

**The 2 that were left over, `0x96`/`0x97`, are not left over either.** They
were the rows where the review's shared-lineage premise looked like it landed,
and that was the 3-row transcription again: the MCS-51 map has all eight `SUBB A`
forms in the `0x90`–`0x9F` row, so the manual gives `0x96`/`0x97` a length of 1
at the opcodes both decoders use, and the 5 instruction starts the corpus puts
across the pair are framed by something three routes agree on, one of which is
not a decoder. `--divergence` reports neither row by name, and `0xA5` — the one
value the manual leaves open — is not among the 17, so the honest count on that
review's list is 17 of 17 rather than 15.

> **Corrected.** The paragraph this replaces read "**The 2 that are genuinely
> uncorroborated are `0x96`/`0x97`, for exactly the shared-lineage reason the
> review gave** … The honest state of those two rows is 'the table's 1 byte
> rests on a shared decoder map', and that is now what is written down." It was
> wrong, and it is left here because the reasoning it used is the one worth
> seeing fail: it read the manual's `X a,@Ri` family as stopping at
> `0x26`/`0x46`/`0x56`/`0x66`, when the map makes that same `+0x20` step at
> `0x36` and at `0x96`. Two decoders agreeing on a row is not by itself
> evidence; this is the case where that rule was applied to a row that turned
> out to have three sources, and applying it there cost a finding that was not
> there.

`OPCODE_LEN` is **not** changed for those two rows, and now there is nothing to
change it to: 1 is what the table, the listings, r2 and the manual all say.

So the two tables in `disasm8051.py` disagree about coverage in **opposite**
directions, and that is the shape of the finding:

- `OPCODE_LEN` is complete. 0 length disagreements over 45,643 listing rows,
  0 over 114,953 r2 positions, and 0 of the manual's 255 assigned rows.
- `mnemonic()` is the one that declines: 35 opcode values reach its `db`
  fall-through, and it will not name any of them.

> **Corrected.** The first bullet previously read "all 34 of these opcodes are
> sized correctly by both routes — each has listing starts whose length agrees,
> and `0xa5` is the only one of the 35 with no listing start at all." Three
> things in it did not survive the third oracle. "34" is 32, because `0x96` and
> `0x97` are unassigned in the manual too and so are not among the "assigned
> ones"; "sized correctly by both routes" credited two decoders where there is
> one map counted twice, which is the defect this section exists to correct; and
> "`0xa5` is the only one of the 35 with no listing start at all" was a
> statement about the corpus that got read as a statement about the map. `0x96`
> has 4 listing starts and `0x97` has 1, and it is precisely because they are
> placed that the decoders' name for them is on the record — the two decoders
> naming a value the manual does not contain is the finding, and it is invisible
> on a row nothing places.
>
> **Corrected again, and the count is back to 34 for a different reason.** The
> paragraph above rejected 34 on the grounds that `0x96` and `0x97` are not among
> the "assigned ones". They are: `SUBB A,@R0` and `SUBB A,@R1`, 1 byte each, in
> the MCS-51 map. Of the 35 values that reach `db`, 34 are assigned and `0xa5`
> alone is not — the same figure the sentence started with, reached from the
> other direction. The two parts of that paragraph that were about *credit*
> rather than *count* are unaffected and stand: "sized correctly by both routes"
> is still wrong for the reason given, because two decoders that share a map are
> one map counted twice, and that remains true of every row in the table.

Which is the hazard `disasm8051.py:168-170` already records for the carry forms:
a cross-decode can only "agree" with a `db` vacuously. It does not move any
number in this document, because `db 0x..` is a *name* and framing never reads
it — the length differential is 0 with or without it.

Both halves, and neither needs the listings. The 35 values first, which is one
line, no image and no r2 — and it is also the command that regenerates the
enumeration above, so a reader who wants the set rather than the table has it:

```console
$ python3 -c 'import sys;sys.path.insert(0,"ec/tools");import disasm8051 as D;print(len([o for o in range(256) if D.mnemonic(bytes([o]+[0]*7),0).startswith("db")]))'
35
$ echo $?
0
$ python3 -c 'import sys;sys.path.insert(0,"ec/tools");import disasm8051 as D,opcode_coverage as C;print(" ".join("%02x%s"%(o,"" if C.MCS51_LEN[o] else "*") for o in range(256) if D.mnemonic(bytes([o]+[0]*7),0).startswith("db")))'
06 07 16 17 26 27 36 37 42 43 46 47 52 53 56 57 62 63 66 67 72 76 77 82 86 87 96 97 a5* a6 a7 b6 b7 d4 f4
$ echo $?
0
```

`*` marks the one the manual leaves unassigned, which is how the 34/1 split
above is checked without reading the table.

and the walk behind 2,214 — the same `pDj` per image `--r2-diff` runs, compared
on the first token:

```console
$ python3 - <<'PY'
import collections, json, os, subprocess, sys, tempfile
sys.path.insert(0, "ec/tools")
import disasm8051 as D, opcode_coverage as C
work = tempfile.mkdtemp()
c = collections.Counter()
for name, args, _what in C.R2_IMAGES:
    path = os.path.join(work, name + ".bin")
    make = [sys.executable, os.path.join("ec/tools", "make_bank_image.py")]
    make += ["--pd", C.FIRMWARE] if args is None else [C.FIRMWARE] + list(args)
    subprocess.run(make + [path], check=True, stdout=subprocess.DEVNULL)
    img = open(path, "rb").read()
    rows = json.loads(subprocess.run(
        ["r2", "-a", "8051", "-e", "scr.color=0", "-q", "-c", "s 0; pDj 0x10000", path],
        capture_output=True, text=True).stdout)
    for r in rows:
        if not r.get("opcode"):          # r2 declined to name it: 0xA5, 66 sites
            continue
        a = r["offset"]
        mine = D.mnemonic(img[a:a + 8], 0, a).split()[0]
        c["0xC1" if bytes.fromhex(r["bytes"])[0] == 0xC1 else
          "db" if mine == "db" else "agree"] += 1
print(c["agree"], "agree,", c["0xC1"], "on 0xC1,", c["db"],
      "where we say db ->", c["0xC1"] + c["db"], "first-token disagreements")
PY
112673 agree, 9 on 0xC1, 2205 where we say db -> 2214 first-token disagreements
```

## The rarest rows are the ones the old oracle could not have caught

Three opcodes appear at exactly one instruction start each, and the counts run
down to there smoothly: 25 opcodes have three or fewer starts.

```
0x71   2    2     2    1      yes    common    -
0x97   1    1     1    1      yes    common    -
0xd7   1    1     1    1      yes    bank1     -
```

(`len` / `list?` / `man` / `starts` / `agree` / programs / self-test tables.)

A wrong length for `0x71` — `acall addr11`, 2 bytes, the rung above `0x70`'s
`jnz rel` — would not have failed `--self-test`, which contains no `0x71` and
never will, because a window is only worth adding if it was transcribed from a
*different* disassembler and there is no second one in the tree. It would have
silently misframed the one instruction in the firmware that uses it and every
linear walk crossing it. That is the failure the issue describes, and it is now
a measured absence rather than a possibility: `0x71` has a manual entry of 2
bytes, the listings and r2 both produce 2, and `OPCODE_LEN` says 2. Three
routes, the third of them not a decoder, and the row is right.

> **Corrected, on the name rather than the length.** This paragraph previously
> gave `0x71` as `jnz rel`. `jnz rel` is `0x70`; the manual's `...X1` ladder
> alternates `0x61` `ajmp`, `0x71` `acall`, `0xE1` `ajmp`, `0xF1` `acall`, so
> the name was a rung out, the same "right family, wrong offset" slip the other
> corrections in this file are about. Both the tree's own decoder
> (`disasm8051.mnemonic(bytes([0x71, 0x10]), 0)` → `acall page+0x10`) and the one
> committed listing that places `0x71` at an instruction start
> (`ec/decompiled/common/6D46.asm:62` → `68F9 71 ff - acall 0x6bff`) name it
> `acall`. The length was never in doubt and nothing else here moves: `0x70` is
> 2 bytes as well, so the argument that a wrong length here would have gone
> undetected is exactly as it was.

> **Corrected.** This paragraph previously ended the same way about all three
> rows, and the middle one does not hold. `0x97` is 1 byte in `OPCODE_LEN`, 1
> byte in the listings and 1 byte in r2 — and the `man` column is a dash, because
> the MCS-51 manual assigns `0x97` no instruction at all. So the walk did not
> check that row and find it right; it found the one row on this list where the
> table's length has no manual to be right or wrong about, and the two decoders
> that agreed with it share the map that invented the name. `0x71` and `0xd7` do
> carry a manual length and the sentence holds for both. This is the clearest
> single case of the defect the `man` column exists to make visible, and it was
> in the document as a claim of success.
>
> **Corrected again, by the same transcription error as the rest of them.** The
> dash in that `man` column was wrong: the manual has `0x97` as `SUBB A,@R1`,
> 1 byte, and the row now reads `1` in the table above. The paragraph it
> corrected is the one before it — all three rows here carry a manual length, the
> listings, r2 and the manual agree on each, and all three are exactly as
> uncorroborated by nothing as the sentence above claims for `0x71`. What the
> retracted paragraph got right is the reason to keep the `man` column at all:
> agreement between two decoders is not agreement with a third, and it is the
> `0x97` row that made that visible — it just made it visible wrongly.

## Zero disagreements, and what zero is

The result is zero, in all three oracles, and the write-up says zero with the
number rather than rounding it into a claim that the table is correct. Concretely:

- **The 0 is a count of rows compared.** 45,643 listings, 114,953 r2 positions,
  255 manual rows. Three counts, three oracles, and the report prints them
  separately because they are not interchangeable.
- **Two of the three are one map counted twice.** Ghidra and r2 are not
  independent, so their two zeros are one zero twice over. The manual's zero is
  the only one that is a comparison against a route neither decoder can have
  taken, and it is the one this document now leads the interpretation with.
  *(Corrected 2026-09-27, review of #67: "a route neither decoder can have
  taken" is the claim, and on `0xA8`-`0xAF` it was false — the transcription had
  been copied from the `0x78` row, so it *had* been taken. The manual's result
  is 0 on the 247 rows where it is independent and 8 where it is not, and
  `--divergence` prints the eight. This bullet's subject is which oracles are
  independent, not how many rows disagree; both are now measured rather than
  asserted.)*
- **Agreement is not correctness.** Even the manual's zero is agreement about
  what bytes mean. It is not hardware, and it is not the EC's behaviour.
- **The 1 row the manual leaves unassigned is outside all of it.** Not counted
  in the 255, not counted as agreement, and reported by name. "Not found by this
  method" is the wording `ec/annotations/registers.yaml` uses for its own nulls,
  and `0xA5` is that row here.
- **The 2 unfound-by-the-listings opcodes are outside the 254/256 fraction**, not
  counted in it, and "not found by this method" is the wording
  `ec/annotations/registers.yaml` uses for its own nulls.
- **An opcode the firmware never executes is outside all three measurements.**
  It is a column in `--coverage` for that reason and never a percentage.

Nothing here is a live test. There was no EC, no capture, no register read-back
and no Windows machine at any point; every number above is a read of files already
in the repository, plus one `r2` subprocess decoding bytes this repository holds.

## Reproducing it

All from the repository root. Command 1 is the primary artifact; commands 2 and 3
are the second decoder opinion and the anchor that must not have moved, and
command 2 now also carries the third oracle's comparison.

```console
$ python3 ec/tools/opcode_coverage.py --summary
opcode table coverage, from the committed Ghidra listings

  listings read                   2711  (3 index rows name no file: a region with no instructions)
  instruction starts              45643
  opcodes at an instruction start 254 of 256
  opcodes the self-test corpus reaches 20 of 256, of which 19 also appear at an instruction start
  length disagreements            0
  not found by this method        2  (0xa5, 0xc1)

  against the MCS-51 manual, which is a third route and not a
  decoder: 0 row(s) assigned and disagreed with, of 255 assigned
  the manual assigns nothing to   1  (0xa5)  -- on these rows no decoder's agreement is evidence

  'not found by this method' is a statement about these listings and
  the regions Ghidra decoded. It is not 'absent from the firmware',
  and an opcode the firmware never executes is outside this
  measurement entirely -- which is why it is a column and not a
  percentage. `r2 -a 8051`'s linear walk over all three images is a
  second route to the same rows and reaches both: --r2-diff.

  Ghidra and r2 are not independent decoders -- they share a map
  this repository already knows disagrees with the manual at
  0xA0/0xB0 -- so 0 disagreements against both is not 0 against
  two. The 'man' column of --coverage is the third oracle, and the
  rows it leaves at '-' are the rows nothing corroborates.
$ echo $?
0
```

```console
$ python3 ec/tools/opcode_coverage.py --divergence
vs the committed Ghidra listings:
  0 row(s) of 45643 instruction start(s) in 2711 listing(s)

vs the MCS-51 manual (transcribed, not a decoder):
  0 row(s) of 255 the manual assigns

rows no oracle can corroborate (the manual assigns no instruction, so a decoder agreeing here is one decoder's map rather than two readings that happen to meet):
  0xa5  no listing start and no manual entry either -- its length rests on the table alone
  1 row(s); 0 disagreements is not 0 against three oracles
$ echo $?
0
```

```console
$ python3 ec/tools/opcode_coverage.py --r2-diff
  bank0  39371 instruction(s) walked of 39371, 254 opcode value(s) reached  (common 0x0000-0x7FFF + bank 0)
  bank1  39187 instruction(s) walked of 39187, 256 opcode value(s) reached  (common 0x0000-0x7FFF + bank 1)
  pd     36395 instruction(s) walked of 36395, 255 opcode value(s) reached  (the ITE8850-PD image, its own 64 KiB address space)
r2 differential: 0 divergence event(s) over 3 image(s), reaching 256 of 256 opcode value(s)
$ echo $?
0
```

The 45,643 in command 2 is `verify_reassembly.py --check`'s own number, reached
by a separate implementation over the same listings — two readers agreeing on the
corpus size is what makes it a fact about the corpus rather than about this
script.

The two anchors, both unchanged by this work:

```console
$ python3 ec/tools/disasm8051.py --self-test
...
self-test passed: both charge-profile-flow.md windows decode identically, all 4 relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode as transcribed
$ python3 ec/tools/verify_reassembly.py --check
  listing bytes: 45643 instruction(s) checked against the firmware, 0 disagreement(s)
  reassembly report: 2580 match, 73 partial, 58 assembler-gap, 0 mismatch (of 2711)
  listing digests: 2711 compared against the committed report, 0 disagreement(s)
  all checks passed
```

And the unit suite, which is the part that keeps the report honest about its own
failure modes — 50 cases, no firmware, no Ghidra, no r2, no network:

```console
$ python3 ec/tools/test_opcode_coverage.py
OK
```

`--coverage` prints the table the appendix below reproduces, identically, and
`--csv PATH` writes the same 256 rows:

```sh
python3 ec/tools/opcode_coverage.py --coverage
python3 ec/tools/opcode_coverage.py --csv /tmp/opcodes.csv
```

## What this does not say

- **It does not say the table is correct.** It says two decoders that share a
  map agree with it on every instruction start either of them placed, and that
  the MCS-51 manual — a route neither decoder can have taken — agrees with it on
  all 255 rows the manual assigns. The 1 row the manual does not assign (`0xA5`)
  is reported as uncorroborated rather than as agreeing, and a fourth source
  could still disagree with all three.

> **Corrected.** This bullet previously read "It says two **independent**
  decoders agree with it … A third decoder could disagree with both." The
> independence was the claim under review and it is false: the two share a map
> that this repository already knows disagrees with the manual at `0xA0`/`0xB0`,
> and at `0x96`/`0x97` they both name an instruction the manual does not
> contain. A third decoder was not the hole; a second decoder that is not
> independent of the first was. The hedge has been replaced with the third
> oracle that closes it, and with the three rows it leaves open.
>
> **Corrected again on the second sentence's evidence.** The `0x96`/`0x97` half
> of that is the 3-row transcription and does not stand — the manual has both,
> and the departure it can cite is the `0xA0`/`0xB0` one, which the first
> sentence of this bullet already names. The `0xA0`/`0xB0` half stands, and so
> does the conclusion: the third oracle, the row it leaves open, and the numbers
> around it are unchanged by the two values moving.
- **It does not settle the mnemonics.** `--self-test` checks those against the
  hand transcriptions; this measures lengths only, because lengths are what
  framing rests on. The one place a mnemonic difference *is* measured is
  [the text comparison above](#what-a-text-comparison-would-have-found-since-this-one-does-not),
  and what it found there is a gap in the other table, not a dispute about a
  name: `mnemonic()` renders 34 assigned 8051 instructions as `db 0x..`. Which
  of two names for a value the walk reached over data is right is a separate
  question and is not answered here.
- **It does not say the framing is right.** That every length agrees means a
  linear walk stays in step, not that a walk starting at the right offset is
  decoding code rather than data. `converges_from()` is the framing evidence and
  it is unchanged; see `converge` in
  [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) for the separate
  question of buffer bounds at `OPCODE_LEN[` sites.
- **It does not say `0xA5` and `0xC1` are absent from the firmware.** It says no
  committed listing places either at an instruction start, and that r2's
  whole-image walk places them without a length disagreement.
- **No live test ran.** No EC, no capture, no register read-back, no Windows.
- **It is not in any gate.** `agent-gates.sh` is a `.github/` file and this
  branch cannot push one. `disasm8051.py --self-test`'s gate call is already
  prepared at `docs/ci/agent-gates-disasm8051-self-test.patch` and unlanded, so
  this work does not add a seventh patch beside the six there; if a gate call is
  wanted for it, that is a human's edit to that same patch.

## What is new, and what a shared file got

New: `ec/tools/opcode_coverage.py`, `ec/tools/test_opcode_coverage.py`, and this
file. `disasm8051.py` is **unchanged** — it grows no mode, and the new tool
imports `OPCODE_LEN` rather than copying it, so the report cannot drift away from
the table it reports on.

Shared files, minimally: one sentence and the measured number inside the existing
`tools/disasm8051.py` bullet in `ec/README.md`, and one section in
`docs/findings.md`.

No generated CSV is committed. A generated file under `ec/annotations/` would
have to be registered in `.github/workflows/agent-conflicts.yml` to survive a
re-export, this pipeline cannot push that file, and an unregistered generated
file is worse than none — so the full table is this appendix and `--csv` writes
it wherever a caller asks.

## Follow-ups this should surface

- **`disasm8051.mnemonic()` renders 34 assigned 8051 instructions as
  `db 0x..`, and the length table sizes every one of them correctly.** The two
  tables in the same file disagree about coverage in opposite directions, which
  is worth an issue of its own: `OPCODE_LEN` is complete over 256 rows while
  `mnemonic()` declines to name 35. Nothing in this document's numbers moves
  until that is fixed, and nothing in it breaks if it is — but any cross-decode
  over an opcode in that set can only "agree" with a `db` vacuously, which is
  the failure `disasm8051.py:168-170` already records for the carry forms. The
  measurement, the two commands and the per-value set are in
  [the section above](#what-a-text-comparison-would-have-found-since-this-one-does-not);
  what it needs is the mnemonic table brought up to the length table, decided
  against a decoder that has not seen this one. (This bullet said 34; a
  correction below it said 32; it is 34, for the reason given in
  [the section above](#what-a-text-comparison-would-have-found-since-this-one-does-not).)
- **`0xA5` is sized by nothing outside `disasm8051.py`, and that is now a
  reported state rather than a silent one.** The manual assigns it no
  instruction, so there is no length to check it against and no evidence that
  would let a future one be "corrected": the listings never place it at an
  instruction start, r2 declines the opcode outright, and the one byte in the
  table is the whole of it. It is the same question the previous revision of
  this file asked about `0x96`/`0x97` — 5 instruction starts in the committed
  corpus framed by a length only the decoders had an opinion about — and the
  answer there was that the manual had those two rows after all. `0xA5` is the
  one value it does not. Deciding it needs a source that is not a decoder and
  not a length table — the vendor's assembler, most likely, which is the same
  `sdas8051` question `verify_reassembly.py` already has open on the
  `0xA0`/`0xB0` row.

> **Corrected.** This bullet previously named `0x96`, `0x97` and `0xA5` and made
> `0x96`/`0x97` the live case: 5 instruction starts framed by a 1-byte length
> "that only the two decoders sharing a map have an opinion about", needing a
> source that is not a decoder to settle. That was the `MCS51_LEN`
> transcription error described in
> [the two-decoders section](#the-two-decoders-are-not-independent-and-what-the-manual-says-about-the-row-nothing-corroborates),
> and the follow-up it asked for is not needed: the manual has both rows and
> agrees on the length. The *class* it describes is real, though — a length only
> two decoders that share a map can be checked against — and `0xA5` is its only
> remaining member on this table. That is why the bullet is narrowed rather than
> deleted.
- **`0xA5` and `0xC1` have no listing-backed length and never will.** If a
  future export decodes the reserved opcode or a `clr bit` into a listing, the
  `not found by this method` count drops without anything having changed here.
  That is the correct behaviour, and it is worth someone knowing it is a
  property of the corpus rather than a regression. The same is true of the
  `man` column's one dash for a different reason: it will not change because the
  corpus changed, but because a source other than a decoder gained an opinion —
  or because a transcription was wrong, which is how the other two dashes in an
  earlier revision of this column came to be there.
- **No length oracle can settle `0xA0`/`0xB0`, and this one demonstrably
  cannot.** `MCS51_LEN` has the manual's `ANL C,/bit` at `0xA0` and
  `ORL C,/bit` at `0xB0`, and because both are 2 bytes it agrees with
  `OPCODE_LEN` there exactly as the decoders do. Adding the third oracle made
  the blindness visible and did nothing to remove it. The question is still open
  and still belongs where `disasm8051.py:177-188` puts it.
- **The r2 walk reads data as code over most of each image.** That is what makes
  it reach 256 of 256, and it is also why its 114,953 positions are not a
  coverage figure about the firmware — only the listings' 45,643 instruction
  starts are. A `--r2-diff` restricted to the committed listings' addresses would
  answer a narrower question this work did not need answered.
- **The self-test corpus is 20 opcodes and stays 20 opcodes** until someone
  transcribes another window from a decoder that has not seen this one. The
  column in `--coverage` is derived from those four tables precisely so that
  adding a site moves the number with no second edit to forget.

## Appendix: the whole table

`python3 ec/tools/opcode_coverage.py --coverage`, unedited. `len` is
`OPCODE_LEN[op]`; `list?` is the length the committed listings give
it and `-` where they place none; **`man` is the MCS-51 manual's length
and `-` where the manual assigns no instruction at all** — one row, `0xA5`,
and the column exists so that one reads as uncorroborated instead of as
agreeing; `starts` counts instruction starts
carrying it; `agree` is `n/a` where the listings have nothing to say,
which is the third state and not a failure.

```console
$ python3 ec/tools/opcode_coverage.py --coverage
opcode len  list? man  starts agree  programs  self-test tables
0x00   1    1     1    485    yes    common,bank0,bank1,pd -
0x01   2    2     2    35     yes    common,bank0,bank1,pd -
0x02   3    3     3    1063   yes    common,bank0,bank1,pd -
0x03   1    1     1    27     yes    common,bank0,bank1,pd -
0x04   1    1     1    222    yes    common,bank0,bank1,pd -
0x05   2    2     2    25     yes    common,bank0,bank1 -
0x06   1    1     1    13     yes    common,bank0,bank1,pd -
0x07   1    1     1    16     yes    common,bank0,bank1 -
0x08   1    1     1    54     yes    common,bank0,bank1,pd -
0x09   1    1     1    21     yes    common,bank0,bank1,pd -
0x0a   1    1     1    9      yes    common,bank1,pd -
0x0b   1    1     1    9      yes    common,bank0,bank1,pd -
0x0c   1    1     1    7      yes    bank1     -
0x0d   1    1     1    22     yes    common,bank0,bank1,pd -
0x0e   1    1     1    16     yes    common,bank0,bank1,pd -
0x0f   1    1     1    45     yes    common,bank0,bank1,pd -
0x10   3    3     3    55     yes    common,bank0,bank1,pd -
0x11   2    2     2    6      yes    common,pd -
0x12   3    3     3    3854   yes    common,bank0,bank1,pd -
0x13   1    1     1    85     yes    common,bank0,bank1,pd -
0x14   1    1     1    161    yes    common,bank0,bank1,pd -
0x15   2    2     2    24     yes    common,bank0,bank1,pd -
0x16   1    1     1    19     yes    common,bank0,bank1 -
0x17   1    1     1    20     yes    common,bank0 -
0x18   1    1     1    15     yes    common,bank0,bank1,pd -
0x19   1    1     1    15     yes    common,bank0,bank1,pd -
0x1a   1    1     1    23     yes    common,bank1 -
0x1b   1    1     1    16     yes    common,bank0,bank1,pd -
0x1c   1    1     1    12     yes    common,bank1 -
0x1d   1    1     1    20     yes    common,bank1 -
0x1e   1    1     1    6      yes    common,bank1,pd -
0x1f   1    1     1    7      yes    common,bank1,pd -
0x20   3    3     3    403    yes    common,bank0,bank1,pd SELF_TEST,REL_SITES
0x21   2    2     2    3      yes    common,bank1 -
0x22   1    1     1    1851   yes    common,bank0,bank1,pd -
0x23   1    1     1    25     yes    common,bank1,pd -
0x24   2    2     2    444    yes    common,bank0,bank1,pd -
0x25   2    2     2    78     yes    common,bank0,bank1,pd -
0x26   1    1     1    11     yes    common,bank1,pd -
0x27   1    1     1    11     yes    common,bank1,pd -
0x28   1    1     1    60     yes    common,bank0,bank1,pd -
0x29   1    1     1    47     yes    common,bank0,bank1,pd -
0x2a   1    1     1    23     yes    bank1,pd  -
0x2b   1    1     1    29     yes    bank1,pd  -
0x2c   1    1     1    30     yes    common,bank1,pd -
0x2d   1    1     1    37     yes    common,bank0,bank1,pd -
0x2e   1    1     1    23     yes    common,bank1,pd -
0x2f   1    1     1    83     yes    common,bank0,bank1,pd -
0x30   3    3     3    581    yes    common,bank0,bank1,pd REL_SITES
0x31   2    2     2    2      yes    common,bank1 -
0x32   1    1     1    33     yes    common,bank1,pd -
0x33   1    1     1    134    yes    common,bank0,bank1,pd -
0x34   2    2     2    240    yes    common,bank0,bank1,pd -
0x35   2    2     2    59     yes    common,bank0,bank1,pd -
0x36   1    1     1    15     yes    common,bank0,bank1 -
0x37   1    1     1    5      yes    common,bank0,bank1 -
0x38   1    1     1    25     yes    common,bank0,bank1,pd -
0x39   1    1     1    14     yes    common,bank0,bank1,pd -
0x3a   1    1     1    37     yes    common,bank0,bank1,pd -
0x3b   1    1     1    27     yes    common,bank1,pd -
0x3c   1    1     1    102    yes    common,bank0,bank1,pd -
0x3d   1    1     1    27     yes    common,bank0,bank1,pd -
0x3e   1    1     1    53     yes    common,bank0,bank1,pd -
0x3f   1    1     1    34     yes    common,bank0,bank1 -
0x40   2    2     2    366    yes    common,bank0,bank1,pd -
0x41   2    2     2    27     yes    common,bank1,pd -
0x42   2    2     2    20     yes    common,bank1,pd -
0x43   3    3     3    29     yes    common    -
0x44   2    2     2    376    yes    common,bank0,bank1,pd SELF_TEST
0x45   2    2     2    40     yes    common,bank1,pd -
0x46   1    1     1    57     yes    common,bank1,pd -
0x47   1    1     1    4      yes    common    -
0x48   1    1     1    12     yes    common,bank1,pd -
0x49   1    1     1    11     yes    common,bank1,pd -
0x4a   1    1     1    9      yes    common,bank1,pd -
0x4b   1    1     1    9      yes    common,bank1,pd -
0x4c   1    1     1    10     yes    bank0,bank1,pd -
0x4d   1    1     1    17     yes    common,bank0,bank1,pd -
0x4e   1    1     1    39     yes    common,bank0,bank1,pd -
0x4f   1    1     1    29     yes    common,bank0,bank1,pd -
0x50   2    2     2    301    yes    common,bank0,bank1,pd -
0x51   2    2     2    4      yes    common    -
0x52   2    2     2    5      yes    common    -
0x53   3    3     3    9      yes    common,bank1,pd -
0x54   2    2     2    828    yes    common,bank0,bank1,pd SELF_TEST
0x55   2    2     2    5      yes    common,bank1,pd -
0x56   1    1     1    16     yes    common,bank1,pd -
0x57   1    1     1    2      yes    common,bank1 -
0x58   1    1     1    5      yes    bank0,bank1,pd -
0x59   1    1     1    3      yes    common,bank1,pd -
0x5a   1    1     1    35     yes    common,bank1,pd -
0x5b   1    1     1    3      yes    common,bank1,pd -
0x5c   1    1     1    7      yes    common,bank1 -
0x5d   1    1     1    7      yes    common,bank1,pd -
0x5e   1    1     1    6      yes    common,bank1,pd -
0x5f   1    1     1    6      yes    common,pd -
0x60   2    2     2    810    yes    common,bank0,bank1,pd -
0x61   2    2     2    2      yes    bank1,pd  -
0x62   2    2     2    5      yes    common    -
0x63   3    3     3    8      yes    common,bank1 -
0x64   2    2     2    168    yes    common,bank0,bank1,pd -
0x65   2    2     2    3      yes    bank1     -
0x66   1    1     1    6      yes    common,bank0,bank1,pd -
0x67   1    1     1    4      yes    common,bank0,bank1,pd -
0x68   1    1     1    6      yes    common,bank1,pd -
0x69   1    1     1    4      yes    bank1     -
0x6a   1    1     1    3      yes    bank1     -
0x6b   1    1     1    6      yes    common,bank1 -
0x6c   1    1     1    2      yes    bank1,pd  -
0x6d   1    1     1    5      yes    common,bank0,bank1,pd -
0x6e   1    1     1    163    yes    common,bank1,pd -
0x6f   1    1     1    41     yes    common,bank0,bank1,pd -
0x70   2    2     2    678    yes    common,bank0,bank1,pd -
0x71   2    2     2    1      yes    common    -
0x72   2    2     2    2      yes    pd        -
0x73   1    1     1    27     yes    common,bank1,pd -
0x74   2    2     2    1341   yes    common,bank0,bank1,pd -
0x75   3    3     3    328    yes    common,bank0,bank1,pd -
0x76   2    2     2    19     yes    common,bank0,bank1 -
0x77   2    2     2    4      yes    common,pd -
0x78   2    2     2    194    yes    common,bank0,bank1,pd -
0x79   2    2     2    126    yes    common,bank0,bank1,pd -
0x7a   2    2     2    132    yes    common,bank0,bank1,pd -
0x7b   2    2     2    210    yes    common,bank0,bank1,pd SELF_TEST
0x7c   2    2     2    127    yes    common,bank0,bank1,pd -
0x7d   2    2     2    209    yes    common,bank0,bank1,pd -
0x7e   2    2     2    95     yes    common,bank0,bank1,pd -
0x7f   2    2     2    511    yes    common,bank0,bank1,pd -
0x80   2    2     2    931    yes    common,bank0,bank1,pd SELF_TEST,REL_SITES
0x81   2    2     2    3      yes    common,bank0,bank1 BIT_SITES
0x82   2    2     2    4      yes    bank0,bank1 -
0x83   1    1     1    4      yes    common,pd -
0x84   1    1     1    19     yes    common,bank0,bank1,pd -
0x85   3    3     3    57     yes    common,bank0,bank1,pd -
0x86   2    2     2    10     yes    bank0,bank1,pd -
0x87   2    2     2    3      yes    bank0,bank1,pd -
0x88   2    2     2    18     yes    common,bank0,bank1,pd -
0x89   2    2     2    43     yes    common,bank0,bank1,pd -
0x8a   2    2     2    45     yes    common,bank0,bank1,pd -
0x8b   2    2     2    20     yes    common,bank1,pd -
0x8c   2    2     2    60     yes    common,bank0,bank1,pd -
0x8d   2    2     2    31     yes    common,bank0,bank1,pd -
0x8e   2    2     2    64     yes    common,bank0,bank1,pd -
0x8f   2    2     2    49     yes    common,bank0,bank1,pd -
0x90   3    3     3    6679   yes    common,bank0,bank1,pd SELF_TEST
0x91   2    2     2    5      yes    common,bank0 -
0x92   2    2     2    19     yes    common,bank0,bank1,pd BIT_SITES
0x93   1    1     1    269    yes    common,bank0,bank1,pd -
0x94   2    2     2    305    yes    common,bank0,bank1,pd -
0x95   2    2     2    6      yes    common,bank0 -
0x96   1    1     1    4      yes    common,bank0,bank1 -
0x97   1    1     1    1      yes    common    -
0x98   1    1     1    18     yes    common,bank0,bank1,pd -
0x99   1    1     1    31     yes    common,bank0,bank1,pd -
0x9a   1    1     1    21     yes    common,bank0,bank1,pd -
0x9b   1    1     1    16     yes    common,bank0,bank1,pd -
0x9c   1    1     1    10     yes    common,bank0,bank1,pd -
0x9d   1    1     1    18     yes    common,bank0,bank1,pd -
0x9e   1    1     1    23     yes    common,bank0,bank1,pd -
0x9f   1    1     1    51     yes    common,bank0,bank1,pd -
0xa0   2    2     2    6      yes    bank0,bank1,pd BIT_SITES
0xa1   2    2     2    2      yes    bank0,bank1 -
0xa2   2    2     2    13     yes    common,bank0,bank1,pd BIT_SITES
0xa3   1    1     1    620    yes    common,bank0,bank1,pd -
0xa4   1    1     1    213    yes    common,bank0,bank1,pd -
0xa5   1    -     -    0      n/a    -         -
0xa6   2    2     2    7      yes    common,bank0,bank1,pd -
0xa7   2    2     2    3      yes    bank1,pd  -
0xa8   2    2     2    17     yes    common,bank1,pd -
0xa9   2    2     2    43     yes    common,bank1,pd -
0xaa   2    2     2    44     yes    common,bank1,pd -
0xab   2    2     2    49     yes    bank0,bank1,pd -
0xac   2    2     2    56     yes    common,bank1,pd -
0xad   2    2     2    46     yes    common,bank0,bank1,pd -
0xae   2    2     2    56     yes    common,bank0,bank1,pd -
0xaf   2    2     2    99     yes    common,bank0,bank1,pd -
0xb0   2    2     2    6      yes    common,bank0,bank1 BIT_SITES
0xb1   2    2     2    3      yes    common,bank1,pd -
0xb2   2    2     2    13     yes    common,bank0,bank1,pd BIT_SITES
0xb3   1    1     1    5      yes    common,bank0,bank1 -
0xb4   3    3     3    473    yes    common,bank0,bank1,pd -
0xb5   3    3     3    37     yes    common,bank1,pd -
0xb6   3    3     3    6      yes    common,bank1 -
0xb7   3    3     3    2      yes    bank1,pd  -
0xb8   3    3     3    4      yes    common,bank1,pd -
0xb9   3    3     3    6      yes    common,bank0,bank1,pd -
0xba   3    3     3    8      yes    common,bank1,pd -
0xbb   3    3     3    37     yes    common,bank0,bank1,pd -
0xbc   3    3     3    6      yes    bank0,bank1,pd -
0xbd   3    3     3    7      yes    common,bank1,pd -
0xbe   3    3     3    9      yes    bank0,bank1,pd -
0xbf   3    3     3    55     yes    common,bank0,bank1,pd SELF_TEST
0xc0   2    2     2    250    yes    common,bank0,bank1,pd -
0xc1   2    -     2    0      n/a    -         TEXTBOOK_BIT_SITES
0xc2   2    2     2    180    yes    common,bank0,bank1,pd TEXTBOOK_BIT_SITES
0xc3   1    1     1    325    yes    common,bank0,bank1,pd -
0xc4   1    1     1    50     yes    common,bank0,bank1,pd -
0xc5   2    2     2    29     yes    common,bank0,bank1,pd -
0xc6   1    1     1    5      yes    common,bank1,pd -
0xc7   1    1     1    3      yes    bank1,pd  -
0xc8   1    1     1    95     yes    common,bank0,bank1,pd -
0xc9   1    1     1    15     yes    common,bank0,pd -
0xca   1    1     1    15     yes    common,bank0,bank1,pd -
0xcb   1    1     1    10     yes    common,bank0,bank1,pd -
0xcc   1    1     1    29     yes    common,bank0,bank1,pd -
0xcd   1    1     1    38     yes    common,bank0,bank1,pd -
0xce   1    1     1    41     yes    common,bank0,bank1,pd -
0xcf   1    1     1    44     yes    common,bank0,pd -
0xd0   2    2     2    219    yes    common,bank0,bank1,pd -
0xd1   2    2     2    11     yes    common,bank0,pd -
0xd2   2    2     2    95     yes    common,bank0,bank1,pd -
0xd3   1    1     1    137    yes    common,bank0,bank1,pd -
0xd4   1    1     1    5      yes    bank0     -
0xd5   3    3     3    14     yes    common,bank0,bank1,pd -
0xd6   1    1     1    4      yes    bank0,bank1 -
0xd7   1    1     1    1      yes    bank1     -
0xd8   2    2     2    40     yes    common,bank0,bank1,pd -
0xd9   2    2     2    5      yes    common,bank1 -
0xda   2    2     2    5      yes    common,bank1,pd -
0xdb   2    2     2    2      yes    common,bank1 -
0xdc   2    2     2    3      yes    common,bank1 -
0xdd   2    2     2    6      yes    common,bank1 -
0xde   2    2     2    12     yes    common,bank0,bank1,pd -
0xdf   2    2     2    23     yes    common,bank0,bank1,pd REL_SITES
0xe0   1    1     1    4129   yes    common,bank0,bank1,pd SELF_TEST
0xe1   2    2     2    2      yes    common    -
0xe2   1    1     1    16     yes    common,bank1,pd -
0xe3   1    1     1    8      yes    common,bank0,pd -
0xe4   1    1     1    1072   yes    common,bank0,bank1,pd -
0xe5   2    2     2    191    yes    common,bank0,bank1,pd -
0xe6   1    1     1    183    yes    common,bank0,bank1,pd -
0xe7   1    1     1    5      yes    bank1,pd  -
0xe8   1    1     1    32     yes    common,bank0,bank1,pd -
0xe9   1    1     1    124    yes    common,bank0,bank1,pd -
0xea   1    1     1    51     yes    common,bank0,bank1,pd -
0xeb   1    1     1    99     yes    common,bank0,bank1,pd -
0xec   1    1     1    157    yes    common,bank0,bank1,pd -
0xed   1    1     1    236    yes    common,bank0,bank1,pd -
0xee   1    1     1    228    yes    common,bank0,bank1,pd -
0xef   1    1     1    852    yes    common,bank0,bank1,pd -
0xf0   1    1     1    3749   yes    common,bank0,bank1,pd SELF_TEST
0xf1   2    2     2    4      yes    bank1     -
0xf2   1    1     1    12     yes    common,bank0,pd -
0xf3   1    1     1    9      yes    common,bank0,bank1,pd -
0xf4   1    1     1    23     yes    common,bank0,bank1,pd -
0xf5   2    2     2    641    yes    common,bank0,bank1,pd -
0xf6   1    1     1    122    yes    common,bank0,bank1,pd -
0xf7   1    1     1    12     yes    common,bank0,bank1,pd -
0xf8   1    1     1    170    yes    common,bank0,bank1,pd -
0xf9   1    1     1    159    yes    common,bank0,bank1,pd -
0xfa   1    1     1    115    yes    common,bank0,bank1,pd -
0xfb   1    1     1    144    yes    common,bank0,bank1,pd -
0xfc   1    1     1    167    yes    common,bank0,bank1,pd -
0xfd   1    1     1    256    yes    common,bank0,bank1,pd -
0xfe   1    1     1    319    yes    common,bank0,bank1,pd -
0xff   1    1     1    1367   yes    common,bank0,bank1,pd SELF_TEST
```
