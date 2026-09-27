# Every DPTR-recipient entry the low base run reaches (#67)

[pd-index-geometry.md](pd-index-geometry.md) §2.3 names eleven helper entries
and says the 151 base sites of §3 hand DPTR to more than those, without
enumerating them. This is the enumeration: one row per entry the run reaches,
carrying the decode outcome each one gets — its term string, or `unmodelled`
with the listing — and the measurement of what widening the decode did to §3.

**Nothing here was observed on hardware.** No register was read, written or
read back, and no site was seen run. This is a static decode of
`ec/firmware/GMxMGxx_11.800` cross-checked against `r2 -a 8051` listings, and
that is all it is. **Arithmetic is not behaviour**: a term here says what
address a byte sequence computes, never that the code path executes, that an
index register holds a value in range, or that a record is any particular size.
`registers.yaml` is untouched, and a static decode of a second 8051 image's
address arithmetic is not evidence about an EC register in either direction.

## 1. The file and how to read it

[`pd-reached-helpers.csv`](pd-reached-helpers.csv) is the machine-readable
form, one row per entry, sorted by entry, produced by
`tools/pd_index_geometry.py --reached-csv` and pinned by its `--self-test`. Its
columns:

| column | meaning |
|---|---|
| `entry`, `file_offset`, `bytes` | the PD runtime entry, the file offset it is at, and the length of the body the walk read |
| `terms` | the term sum, or empty where the model does not cover the body |
| `tail_target` | the branch the body ends on, where it ends on one |
| `unmodelled`, `note`, `first_unmodelled` | `yes`/no, the stop reason verbatim, and the address of the first instruction the model does not cover |
| `sites`, `bases` | how many of the 151 sites hand DPTR to this entry, and which effective bases they are indexing |
| `named_in_table` | whether the row is one of §2's eleven |
| `listing` | filled only where `unmodelled` is `yes` |

`listing` is quoted rather than fitted, and that is the point of the column: a
resolved row is one short line of terms, an unresolved one is its bytes.

The two §2 entries this file does **not** contain are `0x9180` and `0x9A71`, and
neither is absent by accident.

`0x9A71` is called at `0x9DFE`, which is inside the `0x04A6` site at `0x9DEC` —
but that site's chain stops at the `movx @dptr,a` three bytes earlier, at
`0x9DFB`, so the call is never reached. The site is in the table, with
`0x9A71` absent from its chain, and that is the whole of the reason:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9dfa; pd 4' /tmp/pd-67.bin
            0x00009dfa      ea             mov a, r2
            0x00009dfb      f0             movx @dptr, a
            0x00009dfc      a3             inc dptr
            0x00009dfd      eb             mov a, r3
```

`0x9180` is byte-identical to `0x9A99`, which the low run does reach; whether
any site in the image calls it is not something this file measures, and "not
reached from the low run" is all that is claimed. `pd-index-helpers.csv` remains
the table of the eleven and regenerates unchanged; this one supersedes it as
the table of what the low run actually calls.

## 2. Input and reproduction

Input: `ec/firmware/GMxMGxx_11.800`, SHA-256
`158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`. The PD
image is file `[0x20000,0x30000)`; for every instruction address below, file
offset = runtime address + `0x20000`.

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --reached
80 DPTR-recipient entry/entries reached by the PD-image MOV DPTR site(s) with a base in 0x0400-0x04A8
60 decode, 20 do not; 9 of them are in the 11-entry table

$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --reached-csv \
          > /tmp/pd-reached-helpers.csv
$ cmp /tmp/pd-reached-helpers.csv ec/annotations/pd-reached-helpers.csv
```

Independent decoding used **radare2 5.5.0** on a temporary flat image, so the
byte claims below are not the tool agreeing with itself:

```console
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd-67.bin bs=65536 skip=2 count=1
$ r2 -a 8051 -e scr.color=0 -q -c \
    's 0x99e2; pd 5; s 0x0faf; pd 8; s 0x3627; pd 5; s 0x104d; pd 6; s 0x35f3; pd 5; s 0x99d4; pd 5' \
    /tmp/pd-67.bin
```

r2's trailing `; [0x…]` memory-hint column is stripped below for width, as
[pd-index-geometry.md](pd-index-geometry.md) §1 does. Nothing else is edited.

## 3. The population

| | entries | decode | unmodelled |
|---|---:|---:|---:|
| before this change | 78 | 47 | 31 |
| after | **80** | **60** | **20** |

The count of reached entries goes *up* by two, not down, and that is not an
error. `mov rN,a` used to end a decode, so a call sitting behind one was never
followed and never became an entry. Exactly two are new. `0x872F` (which
decodes to `0x200×A`) is behind `0x87E1`'s `mov r3,a`, and `0xB1FA` — one of
§5's `inc dptr` rows — is behind `0xB160`'s `mov r7,a`; both are reached only
once the walks step over those instructions. None is lost. Enumerating the
population the old model could see would have missed both, which is the reason
this is measured rather than filtered.

Nine of the eighty are §2's eleven. Of the resolved sixty, 27 decode to
`A×0x60`, 7 to `R7×0x60`, 6 to `0x200×A`, and the remaining 20 across eleven
smaller shapes — every one of them a term string the §2 table already has a
term for, not a new kind of arithmetic.

## 4. The one rule added, and why it is a rule and not a template

The term model is a set of byte templates; the walkers are a small interpreter
with a per-opcode rule set. §2.1's `0x9987`/`0x998B`/`0x998F` entries were
already described as a fall-through-entry-point idiom, and `0x99E2` — the entry
§2.3 names as the reason `0x04A4` has sites with no term — is the same idiom:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x99e2; pd 5' /tmp/pd-67.bin
            0x000099e2      fe             mov r6, a
            0x000099e3      75f060         mov b, #0x60
            0x000099e6      0210bc         ljmp 0x10bc
```

It is `0x9A1B` with `R3` replaced by `R6`: load a register into A, load the
stride into B, tail into `0x10BC`. What the walkers lacked was not a template
for these bytes but a rule for `0xF8`-`0xFF`. On an 8051 `MOV Rn,A` takes its
source from A and writes only the register bank, so **A's symbol carries
through unchanged** and the walk continues to the template behind it. It
contributes no term — it adds nothing to DPTR, which is exactly what separates
it from the `add`/`mul` idioms the templates cover.

That is the whole extension. `A_WRITERS` already excluded `0xF8`-`0xFF`, so
`ab_of()` and `literals_in()` — the two backward frame walkers — always read
this instruction as not writing A. Only the two forward walks treated it as the
end of a decode, and they now read it the same way as the frame walks do.

`0x99E2` decodes to `A×0x60` and its two sites now carry a term.
`--self-test` pins the rule as behaviour on a synthetic chain, in both
directions: `mov a,r7 ; mov b,#0x5E ; mov r0,a ; mul ab ; …` still yields
`R7×0x5E`, and `mov a,r6 ; mov b,#0x5E ; mov r7,a ; mul ab ; …` yields
`R6×0x5E` — the rule is A surviving, not a rename.

## 5. The five classes still unmodelled, quoted

Twenty of the eighty do not decode. They are five classes, and every one is a
row with its listing rather than a fitted term. **"Not resolved by this method"
is the result; none of these is evidence of absence.**

| class | entries | what the first uncovered instruction is |
|---|---:|---|
| `inc dptr` | 14 | a multi-byte XDATA reader, in four copies |
| `mov a,0x82` | 3 | reads half of DPTR back and adds a register to it |
| `mov r0,0x82` | 1 | a Keil register-bank save/restore, ending in `jmp @a+dptr` |
| `mov dptr,#0x0408` | 1 | rebases into a different array mid-helper |
| `add a,#0x01` | 1 | a `+1` the term model has no template for |

`--self-test` pins one named entry per class by its exact stop reason, so none
of the five can quietly start "decoding" into nothing.

**`inc dptr` — the four-byte reader `0x0FAF`**, reached by 10 sites, the largest
unmodelled class:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x0faf; pd 8' /tmp/pd-67.bin
            0x00000faf      e0             movx a, @dptr
            0x00000fb0      fc             mov r4, a
            0x00000fb1      a3             inc dptr
            0x00000fb2      e0             movx a, @dptr
            0x00000fb3      fd             mov r5, a
            0x00000fb4      a3             inc dptr
            0x00000fb5      e0             movx a, @dptr
            0x00000fb6      fe             mov r6, a
```

It reads four consecutive bytes into R4-R7. `inc dptr` changes the address by
one without a term constant, so folding it into the model would add `+1` to
every chain that reaches it — and §6's `0x260` arithmetic is read off exactly
those term strings. Leaving it out keeps the before/after comparison
reviewable. `0x0FCB` (R0-R3), `0x1041` (a *writer*) and `0x10C8` (R3-R1) are
the other three copies; the remaining ten entries in the class reach them by
`lcall`.

**`mov a,0x82` — `0x3627`**, reached by 5 sites:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x3627; pd 5' /tmp/pd-67.bin
            0x00003627      e582           mov a, dpl
            0x00003629      2e             add a, r6
            0x0000362a      f582           mov dpl, a
            0x0000362c      e4             clr a
            0x0000362d      3583           addc a, dph
```

It reads DPTR's low byte back and adds `R6` to it. That is a real addend and
the model has no template for it because the addend's operand is DPTR itself,
not an immediate. The other two are `0x5726` and `0x99C9`, the same shape
against `R7` and `R5`.

**`mov r0,0x82` — `0x104D`**, reached by 6 sites, and the clearest negative
answer to the issue's "or whether it is genuinely not an address helper":

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x104d; pd 6' /tmp/pd-67.bin
            0x0000104d      a882           mov r0, dpl
            0x0000104f      8583f0         mov b, dph
            0x00001052      d083           pop dph
            0x00001054      d082           pop dpl
            0x00001056      121064         lcall 0x1064
            0x00001059      121064         lcall 0x1064
```

It saves DPTR into the register bank, pops a *different* DPTR back, calls
`0x1064` four times, and ends in `clr a ; jmp @a+dptr` — a computed jump with
no target bytes. It is a byte-copy/serialise helper that DPTR passes through.
Modelling it would require control-flow recovery, which this tool does not do
and `pd-index-geometry.md` §6's `#26` bullet is about.

**`mov dptr,#0x0408` — `0x35F3`**, one site:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x35f3; pd 5' /tmp/pd-67.bin
            0x000035f3      e4             clr a
            0x000035f4      f0             movx @dptr, a
            0x000035f5      900408         mov dptr, #0x0408
            0x000035f8      ef             mov a, r7
            0x000035f9      75f060         mov b, #0x60
```

It zeroes the byte the caller's index points at, rebases DPTR onto the `0x0408`
array, and only then indexes — the "store the index, then use it" shape
`ec-0x07d0-sites.csv` records as `write x1`, one array away. The site does not
resolve *this* base's arithmetic, which is the honest reading.

**`add a,#0x01` — `0x99D4`**, one site: reads a byte through DPTR, adds one,
and tail-jumps to a bit-rotate routine. A `+1` is a real address arithmetic
and a one-off stride; the census has no `0x01` row because the model has no
template for it, and adding one on the strength of a single entry is not a
change the evidence supports.

## 6. What happened to the 35 sites with no term

§5 of [pd-index-geometry.md](pd-index-geometry.md) recorded 35 of the 151 with
no resolved term. **24 of them now resolve and 11 do not**, and the 11 are a
single identifiable shape rather than eleven separate gaps:

| | sites | what it was |
|---|---:|---|
| reached an entry beginning `mov rN,a` | 14 | `0x99E2` ×2, and twelve others — §4's rule resolves them |
| stopped inline on `mov rN,a` in the site body | 10 | `mov r7,a` ×9, `mov r3,a` ×1 — the same rule, in the other walker |
| **no helper at all** | **11** | `mov dptr,#imm` immediately followed by `ret` |

The 11 are worth naming precisely, because "no term" and "no arithmetic" are
different claims and only one of them applies here. All eleven are three bytes
long:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x351d; pd 3; s 0x9a94; pd 3' /tmp/pd-67.bin
            0x0000351d      900410         mov dptr, #0x0410
            0x00003520      22             ret
            0x00003521      9007d0         mov dptr, #0x07d0
            0x00009a94      9004a4         mov dptr, #0x04a4
            0x00009a97      22             ret
            0x00009a98      ee             mov a, r6
```

A base is loaded and the routine returns with it, having indexed nothing. What
that is — a leaf that hands a caller its own pointer, a store-only site, or a
byte pattern the byte scan matched inside a data run — is not decidable from
these bytes, and `pd-index-geometry.md` §5's framing caveat applies to all
eleven: the 0x0400/0x0408/0x0410/0x0418/0x0428/0x0434/0x0474/0x04A4 bases
they load are themselves the low run's, so a caller-supplied index is the
reading, not a proven one.

## 7. Does `0x260` hold across the widened run

This is the issue's third question, and it is the one §3.2 of
[pd-index-geometry.md](pd-index-geometry.md) was built to leave open. As that
section stands after #74, 82 of the 151 sites apply both a `×0x60` and a
`0x200×` term; 40 of them name an identified register on both sides, all 40 the
same register; and the remaining 42 have one side unresolved and are counted
neither way. Widening the decode was the only way to test whether that subset
was special.

**It was not.** The answer:

| | before | after |
|---|---:|---:|
| sites applying both a `×0x60` and a `0x200×` term | 82 | **98** |
| …where both terms name an identified register | 40 | **40** |
| …of those, where the two are *different* registers | 0 | **0** |

Sixteen more two-term sites are now visible and all sixteen have one side
unresolved, so they are counted neither way — the same rule §3.2 already
applied, and the reason the 40 does not move. **The load-bearing number is the
zero.** The 58 newly-resolved sites produced no case of `Rn×0x60 + Rm×0x200`
with `Rn ≠ Rm`, which is what would have made `0x260` an artefact of the subset
the old templates happened to resolve. All three numbers are pinned by
`--self-test`, so this table cannot drift from the tool.

The `0x1F` term does not move either: still 3 sites, still 2 bases
(`0x04A5`, `0x04A6`), still a second inner index *alongside* `0x60` and never
instead of it. §3.2's statement that `0x260` is not a whole multiple of `0x1F`
and that nothing here says what the inner index addresses still stands.

`0x04A4` does move, and in the direction the issue predicted: its two sites
both reached `0x99E2`, so its dash in §3.3's table was always "not resolved by
this method", and one of them now resolves `A×0x60 + 0x200×R6`. The other,
`0x9A94`, is one of §6's eleven `ret` sites and still resolves nothing — so the
row reads `0x60` with one site carrying the page term, not two.

**All of this is arithmetic on the decoded terms, and it is exactly as strong
as the framing evidence behind them.** It is not a record count, not a name for
the record contents, and not a bound on any index register. Those stay where
[pd-index-geometry.md](pd-index-geometry.md) §5 left them.

## 8. What moved, and what did not

One committed CSV moved, and it moved because the rule changed what `chain_from`
resolves at a site — which is the answer to the issue's question, not a
regression. `pd-base-strides.csv` over the whole image:

| stride | before | after | bases before → after |
|---|---:|---:|---|
| `0x60` | 100 sites, 82 paged | 124 sites, 98 paged | 33 → 37 |
| `0x5E` | 6, 0 | 29, 0 | 4 → 9 |
| `0x17` | 9, 0 | 17, 0 | 3 → 7 |
| `0x77` | 6, 0 | 10, 0 | 2 → 4 |
| `0x67` | 6, 0 | 7, 0 | 5 → 6 |
| `0x1F` | 3, 3 | 3, 3 | 2 → 2 |
| `0x04` | 2, 0 | 2, 0 | 2 → 2 |
| unresolved | 3047, 16 | 2987, 16 | 448 → 438 |

The 3,176-site denominator does not move, and the page-term column is the part
that matters: **every stride other than `0x60` and `0x1F` still has zero sites
carrying `0x200×`**, so §7.4's answer to that question is unchanged by a decode
that got wider. §7.2's census table in
[pd-index-geometry.md](pd-index-geometry.md) takes these figures with the old
ones struck.

The other four generated CSVs are byte-identical, and structurally so rather
than by luck: `access_walk()` is a separate walker that never calls
`walk_helper()` or `chain_from()`, and `pd-index-callers.csv` depends on
neither. So the 653/428/225/186/977 census pins, the 151/3,176 denominators,
the 3047→2987 unresolved count and both access CSVs are untouched by this
change — which is what `--self-test` reports.

## 9. What this does not establish

- **Nothing is observed.** No register read, no site run, no PD transaction
  traced. It is a byte-level decode plus an independent disassembly of the same
  committed bytes.
- **A decode is not behaviour.** `0x260` is a stride the arithmetic produces.
  Nothing here bounds an index, counts a record, or names what a record holds.
- **The 20 unmodelled entries are not addresses the model failed on by
  accident.** Each row says what its bytes do and stops. `0x104D` in particular
  is a helper DPTR passes through, not one that computes an index, and saying
  so is the answer rather than a gap.
- **The 11 `ret` sites are not sites that do nothing.** A base loaded and
  returned is a shape this walk reports, and §5 of
  [pd-index-geometry.md](pd-index-geometry.md) — one caller found means one
  found by this method — is the standing caveat on what they do.
- **The byte scan over-counts and under-counts.** 29 of the 80 entries are
  reached by more than one site, and one entry by 39, so these counts are
  "sites this method reaches", never "sites that exist".
- **No `registers.yaml` status moved, and none could have.** See the preamble.
- **The census's `0x200×`-free verdict is a result of this decode, not a proof
  about the firmware.** §8 widens it and it held; an index term applied by an
  idiom outside the five templates and the one rule above would still not show
  up in it.

## 10. What this opens

- **`inc dptr` is the obvious next extension**, and it is deliberately not
  taken here. A constant addend of one changes the term string of every chain
  it touches, which is exactly what §7's before/after comparison is read
  against; folding it in would make that comparison unreviewable. Four reader
  copies (`0x0FAF`, `0x0FCB`, `0x1041`, `0x10C8`) and 34 sites are waiting on
  it.
- **The three `mov a,0x82` entries** add a register to half of DPTR read back
  out of it. That is one template, and each needs its own argument about what
  the carry out of `add a,rN` means for the high byte.
- **The 58 sites with one unresolved term side** are the largest remaining
  population in §7. They are the sites where §7 can be extended, not a
  measurement to be re-run.
- **Call-graph recovery** (`#26`) and **CODE-reader recovery** (`#61`) remain
  separate, and `0x104D`'s `jmp @a+dptr` is the kind of thing only the first of
  them settles.
- **The hardware half is unchanged** and still needs a human at the machine:
  trace the PD controller's XDATA at these sites and read what the index
  registers hold. Nothing in this file substitutes for that, and no part of it
  is a result of it.
