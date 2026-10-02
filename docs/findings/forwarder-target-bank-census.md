# Every bank-switch forwarder's `imm16`, resolved in the bank its stub selects (issue #465)

The family of BL51 forwarders is **common-area code**. Every entry sits below
`0x8000`, where a bank program and the common program are the same bytes, so
there is no "own bank" for one of these to have been read in. That is not a
detail of the correction issue #255 made to nine annotation rows — it changes
what the correction *means*, and it is why the withdrawn count was not simply
measured against the wrong bank but measured against a bank these addresses do
not belong to.

`ec/decompiled/bank1/198A.asm` is the sharpest case, because it reads like a
bank-1 listing and is not one. Its bytes are `90 c1 e7 02 11 00` at file
`0x198A`. At file `0x1198A` — bank 1's own `0x8000`-`0xFFFF` region at the same
offset into that window, its runtime `0x998A` — the firmware holds
`70 0f 90 1c 04 e0 f9 90`. The listing header says so in every line: a bank
program is its own code *plus* the `0x0000`-`0x7FFF` common area, which is also
what `build_ec_decompile.py` and `make_bank_image.py` do when they graft one
image onto the others.

Every figure here comes from one command, which reads committed files only and
writes none:

```console
python3 ec/tools/census_forwarder_targets.py
```

and its per-target table, one row per forwarder of the whole family:

```console
python3 ec/tools/census_forwarder_targets.py --csv > ec/annotations/forwarder-targets.csv
```

**Nothing here is a behavioural claim.** Nothing was observed on hardware, no
listing was re-read, no Ghidra export ran, and no `status:` in
`ec/annotations/registers.yaml` moves on any of it. Which bank an address
resolves in says where the linker meant the bytes to be read; it says nothing
about what the EC does there.

## What was measured, and against what

Each forwarder's `imm16` is classified against the committed `.asm` listings of
**the bank its stub selects** — `entry` at an instruction start, `operand` under
a listing but not at a start, `no-listing` otherwise. The stub map is
`audit_call_targets.py`'s own `bank_switch_stubs`, and its `STUB_SITES` is the
answer that tool already pins under `--self-test`, so this census cannot
disagree with §2 of
[`bank-call-audit.md`](../../ec/annotations/bank-call-audit.md). The stub
addresses it selects on are found in the image, not written here.

The three classes are exhaustive and there is no fourth. `no-listing` means
**not found by this method**: no committed export names that address in that
bank. It is never "absent" or "undecodable" — an unseeded function and a
function Ghidra declined to cut are one thing to a method that only reads what
is on disk, and landing the missing listings needs a `--report` run on the
pinned assembler ([`ec/ghidra/README.md`](../../ec/ghidra/README.md)), not an
inference from their absence.

## The whole family

A count over the committed image, so it moves only if the firmware does.

| stub | selects | forwarders | distinct targets | entry | operand | no-listing |
|---|---|---:|---:|---:|---:|---:|
| `0x1100` | bank 0 | 350 | 350 | 43 | 0 | 307 |
| `0x1114` | bank 1 | 53 | 53 | 11 | 0 | 42 |
| `0x1128` | bank 2 | 0 | 0 | 0 | 0 | 0 |
| `0x113C` | bank 3 | 0 | 0 | 0 | 0 | 0 |

The two stubs at zero are printed rather than dropped, so the sweep over the
four sites is visibly complete rather than visibly incomplete.

**No target in the family is an operand byte in the bank its stub selects.**
Every one of them is either the entry of its own committed listing or has no
listing at all. The `operand` column is not there because it is expected to be
zero — it is there because the withdrawn reading fills it, and a census that
had no way to say the word could not show that the difference was the bank.

**The mirror direction.** The withdrawn census counted only the `0x1100`
direction. Stub `0x1114` is bank 1's and carries the second row above: 53
forwarders, 53 distinct targets, and their listings are bank 1's. It cost the
same code path to measure and it is a result rather than an omission. One
address, `0x8294`, is the target of a forwarder in *each* direction —
`bank1,19E4` through stub `0x1100`, and `0x1894` through stub `0x1114`, which is
a forwarder this image holds and carries no `ghidra-functions.csv` row of its
own — so the census reads the same target against both banks and answers
`entry` in one and not-found-by-this-method in the other. That is the kind of
overlap a per-bank reading has to handle rather than assume away.

## The annotated subset, and the replacement for 19 / 7 / 22

`ec/annotations/ghidra-functions.csv` `bank1,19A8` withdrew a census of "the 48
bank1 forwarders in this file whose listing is the BL51 stub" and asked for a
replacement. The subset is selected by rule rather than by a string: rows scoped
`bank1`, typed `forwarder`, whose own comment names a stub address this image
holds and quotes the immediate the listing loads DPTR with. Keying on the
literal `ljmp 0x1100` would select only some of them, because these rows spell
the tail-jump more than one way — so a string rule answers a narrower question
while reading as though it had answered this one.

| listings read | entry | operand | no-listing |
|---|---:|---:|---:|
| **the bank the stub selects (bank 0)** | **25** | **0** | **23** |
| the bank the row is filed under (bank 1) — *withdrawn, issue #255* | 19 | 22 | 7 |

The two rows differ only in which bank's `.asm` files were asked. The withdrawn
reading is reproduced here rather than restated from memory, which is the only
way a reader can tell that the replacement changed the population's reading and
not its membership.

The shape of the change: **not one of the 22 addresses the withdrawn count
called an operand byte is an operand byte in bank 0**, and in bank 0 the class
does not occur at all. Nine of the 22 are real entries and thirteen have no
committed listing. Conversely four of the seven it called "not covered by any
committed bank1 listing" are entries in bank 0 — `0x8294`, `0xA747`, `0xC349`
and `0xC48F` — and three have no listing in either bank (`0x8567`, `0x8588`,
`0x85FB`).

Where a `ghidra-functions.csv` row carries the bank-0 listing, the symbol that
row gives: `0xC1E7` is `test_1664_bit0`, `0xC389` is `clear_1607_bit2`, `0xC349`
is `test_1667_bit0`, `0xC0AD` is `init_1615_1807_then_clear_1601_bit5`, `0xC48F`
is `clear_160a_bit0`. Of the subset's bank-0 listings, the two that carry no such
row are `0x8294` and `0xC4C9`, both still `FUN_CODE_*` in
`ec/decompiled/listing-index.csv` because they were seeded by a call-target byte
scan rather than annotated.

Three addresses are worth naming individually, because they are the ones that
would have been argued about:

- **`0xAA04`, the target of `bank1,1A14`, has no listing in bank 0 at all** and
  is an instruction start inside `ec/decompiled/bank1/A9B4.asm` in bank 1.
  One address, two answers, and nothing about it that does not depend on which
  bank is asked.
- **`0xC389`, the target of `bank1,19B4`, is an entry in bank 0 and an operand
  byte in bank 1** — the third byte of the `lcall 0xc41d` at `0xC387` in
  `ec/decompiled/bank1/C352.asm`. Same shape, opposite way round.
- **`0xC1E7` is an entry in *both* banks with entirely unrelated bodies**:
  `test_1664_bit0` in bank 0, `latch_0498_bit1_or_bit3` in bank 1. The name
  `bank1,198A` renders its forwarder with is the bank-1 one, which the bank the
  stub selects never runs.

### The boundary, printed

More `bank1` annotated rows sit at a forwarder entry this image holds and are
**not** in the subset: `bank1,1A98`, `1A9E`, `1AA4`, `1AAA`, `1AB0`, `1AB6`
and `1ABC`, every one of them typed `dispatch` rather than `forwarder`. They are
in the whole-family table and in the CSV. The boundary is the `type` column, and
the tool prints which side of it each of them is on, so a rule that quietly
narrowed would be visible rather than silent.

## The unlisted targets, read off the image

`no-listing` is the class, not a verdict, so the bytes are printed beside it.
Two of them were already transcribed by hand and are what
`ghidra-variables.csv` `bank1,0xA4CF` and the `bank1,19A8` row rest on:

- `0xC118` is `12 c0 e7 ef 60 03 7f 01 22 7f 00 22` — `lcall 0xC0E7` then the
  six-instruction restatement of its answer in R7 as 1 or 0. That is an entry
  by any reading; it simply has no committed export.
- `0xC10C` is the same seven instructions with `lcall 0xC0C9`.

The rest read as ordinary Keil output — `0xC2EF` is
`90 16 06 e0 54 fb f0 22`, `mov DPTR,#0x1606; movx A,@DPTR; anl A,#0xfb; movx
@DPTR,A; ret`, a read-modify-write that clears bit 2 of `0x1606` and has no
listing — but that is a reading of eight bytes and nothing more. **Landing the
missing listings is a separate change** and the addresses are carried in
`ec/annotations/forwarder-targets.csv` for it.

## What this is not

- **Not a behavioural claim.** No hardware, no Windows, no live run. Every input
  is a committed file.
- **Not a claim that an unlisted address has no code.** "Not found by this
  method" is the whole of it, and it is the caveat
  `ec/annotations/registers.yaml` and `census_ff_fill.py` both carry.
- **Not a claim about what any of these routines does.** Several now carry
  names from bank-0 listings that were already committed; those names were
  earned elsewhere and this change only records which bank they belong to.
- **Not a claim that a `forwarder` row and a `dispatch` row mean different
  things.** The `type` boundary here is the annotation file's, and this census
  reports it rather than ruling on it.