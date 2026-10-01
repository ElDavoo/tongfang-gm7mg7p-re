# What the cross-decoder's `vacuous` bucket is made of (issue #350)

`ec/ghidra/cross-decoder.csv` records, per sampled function, whether Ghidra's
exported C names the XDATA addresses `disasm8051.py` finds in the function's
opening straight-line instructions. `docs/findings.md` §14i gave it a sample,
a denominator and a ratchet. Its largest bucket is `vacuous` — a function
whose opening names no address, so the comparison had nothing to match — and
the denominator line prints how many of those there are and stops.

Issue #350's complaint is that they are not one thing. `outcome` answers *did
the comparison agree*, and for a window that found no address there was no
disagreement to report, so a row whose exported `.c` plainly names several
XDATA symbols reads `vacuous` beside a row that names none. Nothing in the tree
records which is which, so a reader of a ratcheted measurement is invited to
take "no address in the opening" for "nothing there".

This measures it. `ec/tools/cross_decoder_blindness.py` classifies every
`vacuous` row into what its absence is made of, and commits the classes as a
`blind` column in `ec/ghidra/cross-decoder-blindness.csv`, a sidecar over the
same `(program, addr)` keys. It adds nothing to `CROSS_DECODER_OUTCOMES`,
changes no outcome, and touches no register status.

```
$ python3 ec/tools/cross_decoder_blindness.py
  the 1008 vacuous row(s) are 356 entry-is-branch, 493 no-xdata-named, 62 named-past-first-branch, 97 no-literal-named, out of 2057 sampled function(s) of which 1047 were compared
  entry-is-branch        the export's entry is a branch, so the window stops on instruction one by design and the body is past it
  no-xdata-named         the C names no XDATA address at all, so there is no address in question -- not a blind spot, and not an absence either
  named-past-first-branch the opening is real and names no address, and the function's own listing extent holds one the C does name: a match one branch too late
  no-literal-named       the C names an address the function's own listing never loads into DPTR, so the pointer arrives from the caller or is built by arithmetic from a base -- which of the two is not decided here
```

The counts move whenever the export or the sample does; that line is where they
are read from, not from here.

## The issue's figures are stale, and its shape is not

§14i records the same staleness once already, for the same reason — the sample
grows as the annotation layer does, and every figure derived from it moves.
The committed report is 2,057 rows today, not the 1,901/1,957 the issue and
§14i quote. Splitting the 1,008 `vacuous` rows by the issue's own two axes:

| | C names no XDATA address | C names one |
|---|---|---|
| **window empty (`insns`=0)** | 223 | **133** |
| **window non-empty** | 493 | **159** |
| | 716 | **292** |

The issue's shape carries over intact: rows whose C names no XDATA address
outnumber the ones whose C does by about five to three, and the smaller half is
the population the `agree` figure says nothing about — the part worth
classifying. Every count has moved, and `docs/findings.md` §14i's denominator
paragraph is corrected in place with the old figure beside it, per §4a-4d.

What follows is the same split cut a second way: not "is the window empty" but
"what is the absence made of". The two questions are not redundant, because
223 of the 356 window-empty rows' C names nothing at all — their window is
empty for two independent reasons, and only one of them is a blind spot.

## The four classes, and one worked example each

| class | n | what it is |
|---|---|---|
| `entry-is-branch` | 356 | the byte at the function's entry is in `disasm8051.FLOW_OPCODES`, so the window is empty by construction and could be nothing else |
| `no-xdata-named` | 493 | the `.c` names no XDATA address at all — there is no address in question |
| `named-past-first-branch` | 62 | the opening is real and names nothing, and the function's own listing extent holds a literal its C *does* name: a match one branch too late |
| `no-literal-named` | 97 | the C names an address the function's own listing never loads into DPTR |

`entry-is-branch` is decided first, and the order is the measurement rather
than a preference. A decompile that names nothing still has an entry byte, and
for a function whose entry is a branch the empty window is accounted for twice
over — once by "the C names nothing", once and more strongly by "the window was
never going to hold anything". Deciding it the other way round puts 223 of the
356 in `no-xdata-named` and makes `insns`=0 stop meaning `entry-is-branch`,
which is the identity the class exists to assert.

### `entry-is-branch` — `bank0 0x8FDB state_0817_fallthrough`

```
8FDB     12 c3 56 lcall    0xc356
8FDE     ef - -   mov      A, R7
8FDF     60 14 -  jz       0x8ff5
8FE1     90 06 c5 mov      DPTR, #0x6c5
8FE4     e0 - -   movx     A, @DPTR
```

The entry is a `lcall`, which is in `FLOW_OPCODES`, so `compare_function()`
stops on instruction one and `insns` is 0. The body's `mov DPTR,#0x6c5` is
six bytes in, and `state_0817_fallthrough.c` names `XDATA_06C5`,
`DAT_EXTMEM_0817`, `DAT_EXTMEM_081e` and `DAT_EXTMEM_081f` and calls
`set_1605_bit5()` — four XDATA addresses, recorded `vacuous`. This is a
boundary artefact of the comparison's own rule and not a decompile problem.

`bank0 0x9007 word_nonzero_check_tail` is the same shape one listing further
on, and the pair is worth reading together because it is the whole
distinction in two addresses: `0x9006 read_dptr_byte` is one `movx A, @DPTR`
whose C names `DAT_EXTMEM_0817`, `DAT_EXTMEM_081e` and `DAT_EXTMEM_081f`, and
it reads `no-literal-named` instead.

### `named-past-first-branch` — `bank0 0x9C24 reset_08ad_08bf_and_clear_08e2_bit7`

```
9C24     e4 - -   clr      A
9C25     12 bd 20 lcall    0xbd20          <- the window stops here, insns = 1
9C28     54 7f -  anl      A, #0x7f
9C2A     f0 - -   movx     @DPTR, A
9C2B     90 04 90 mov      DPTR, #0x490
   ...                                      <- a branch at 9C2F ends the opening
9C3C     90 08 ad mov      DPTR, #0x8ad
9C3F     f0 - -   movx     @DPTR, A
9C43     90 08 bf mov      DPTR, #0x8bf
```

Here the opening is real — one `clr` — and the second instruction is a call.
The listing's own extent loads three addresses and the C names all three
(`DAT_EXTMEM_0490`, `DAT_EXTMEM_08ad`, `DAT_EXTMEM_08bf`). The comparison
reports `vacuous` about a function whose C names everything its machine code
names; the only thing between them is where the window was told to stop.

This is the one class that is a window definition rather than a shape of the
code, and it is why the class is worth having separately: it is the part of
the blind spot that a longer window would close by itself.

### `no-literal-named` — `bank0 0x9006 read_dptr_byte`

```
9006     e0 - -   movx     A, @DPTR
```

The whole listing. DPTR arrives from whoever called it, and the C says so — it
takes a `char *`, reads `*param_1` and `param_1[1]`, calls `set_1605_bit5()` and
then stores `DAT_EXTMEM_081e`, `DAT_EXTMEM_081f` and `DAT_EXTMEM_0817`, all
through a pointer this function never loads. `bank0 0xB939
store_a_to_dptr_b939` and `bank0 0x801F store_1901` are the same shape, and the
class spans the size range rather than sitting at one end of it — `0xACB4`, at
238 bytes, is `named-past-first-branch` instead, which is the point of measuring
over the listing's extent rather than the window: the class is about *no
literal in the function*, not about a short one.

### `no-xdata-named` — `bank0 0x2A6C clear_4c_bits_4_5_7`

```c
void clear_4c_bits_4_5_7(void)
{
  DAT_INTMEM_4c = DAT_INTMEM_4c & 0x8f;
  return;
}
```

The function does touch a byte; it is `0x4C` in **internal** RAM, and neither
`DAT_INTMEM_` nor a `DAT_EXTMEM_`/`XDATA_` symbol is the comparison's
vocabulary for it. This row is neither a blind spot nor an absence — there is
no XDATA address in question — and it is a class of its own precisely so that
the other three are not read as one thing. It is also the largest class, and
saying so plainly is the reason it is in the vocabulary: 493 of the 1,008 rows
named nothing, and a census that only counted the interesting ones would make
the interesting ones look like the population.

## The residue, and the split that is not made here

`no-literal-named` is 97 rows, and the issue asked for it to be divided into
*reached through a caller-supplied pointer* and *DPTR built by arithmetic from a
base*. **That split is not made here**, and the reason is the same one
`CROSS_DECODER_OUTCOMES` gives for leaving `disagree` as one bucket: guessing
which of a function's C reads is a fold would manufacture the very distinction
the comparison is meant to measure.

Telling the two apart means reading each `.c` and deciding what its pointer
algebra means. A regex proxy does produce buckets — `*param_N`, `+ 0x..`,
neither — but they are not the issue's two, because **a function is not
reliably one or the other**: `bank1 0xED02 data_run_1a_1e` takes five `byte *`
parameters and stores through `*param_4`, and in the same body folds
`BANK3_R6` and a carry chain into a pointer offset. Three of the 97 rows carry
both shapes. The proxy would be a guess about intent wearing a count's
clothes.

So the class states the thing that is true of every row in it — the function
holds no `mov dptr,#imm` naming any address its C names, so the address is
supplied by the caller or built from a base — and the finer split is named here
as the thing a future method has to earn. The issue asked for four buckets and
the measurement supports these four plus that documented residue; the
mechanism that would close the residue is a DPTR-tracking walk, discussed
below.

## A correction to the issue's own example: `bank0 0xACB4`

The issue filed `reset_xdata_flags_and_07d5_to_ff` as the residue, on the
ground that it "walks 37 instructions and builds its pointer as
`cVar1 * '\x03' + 0x2e`, naming neither `0x07C5` nor `0x075E`, both of which its
own annotation comment lists". On this tree it reads
**`named-past-first-branch`**, and the difference is worth stating rather than
rounding off.

**One of the two addresses in that premise does not hold.** `ACB4.c` does name
`0x075E`: `DAT_EXTMEM_075e = DAT_EXTMEM_075e | 0x10;` is its own line. Only
`0x07C5` is missed, and that half is right — `0x07C5` is in the function's
listing extent and the C does not name it. The pointer arithmetic quoted
alongside it is a copy loop into **internal** RAM (`DAT_INTMEM_b7` /
`DAT_INTMEM_b8`, per the function's own annotation comment), so it is not an
XDATA pointer built from a base either.

What the function actually does, measured:

| | |
|---|---|
| addresses its 238-byte listing extent loads into DPTR | 21 |
| addresses its C names | 10 |
| of those 10, present in the extent | **10** |
| in the extent but not named | 11, among them `0x07C5` |

Every address `ACB4.c` names is loaded in the function, and none of the ten is
in the opening the window walked — 37 instructions before it stopped. That is
`named-past-first-branch`, not the residue.

The class cannot express *which* address was missed, because it is a property
of the function and that is a property of a (function, address) pair.
Answering it for `0x07D0` or `0x07C5` across the whole sample is a different
measurement and needs a register named. `KNOWN_ANSWERS` in the tool pins
`0xACB4` at what it actually reads, and
`ec/tools/test_cross_decoder_blindness.py` asserts the disagreement is still
the measurement — that its extent holds more literals than its C names — so a
later change that quietly made it fit the issue's reading would fail there.

## What this says about 0x07D0, and what it does not

§14i leaves `ec/annotations/registers.yaml`'s 0x07D0 at
`unknown-not-absent-DO-NOT-WRITE-BLIND`: the widened comparison finds 0x07D0 in
seven PD functions' openings, all `agree`, and says nothing about whether the
*main EC image* acts on the byte. This census does not move that, and the way
to say so is a number rather than a reassurance.

Searching the 1,008 `vacuous` rows' decompiles for 0x07D0 **as a symbol the
body names**, two rows come back, and **both are `pd`** —
`pd 0xA5B3 and_16bit_fields_write_07d2_07d3` and
`pd 0xC398 set_r7_r5_from_iram_then_read_07d0`, both
`named-past-first-branch`. No `bank0`, `bank1` or `common` row in the bucket
names it.

So the population this issue asked about is, for the main EC image, **empty by
this method** — which is "not found by this method" and never "absent". The
bucket is half of a ratcheted measurement and it contains no EC-image function
whose decompile mentions 0x07D0, so nothing here is evidence for or against the
byte's being acted on. The status stays where §14i left it, and 0x07D0 is not
promoted on any of this.

## Does the blind spot need a second method?

A DPTR-tracking walk would follow DPTR through `mov dptr,#imm`, `mov dptr,a`,
`add a,#imm`, `mov dptr,r*` and the rest, and would attribute an `movx` to an
address the straight-line window cannot name. `walk_flow_follow.py`,
`walk_branch_arms.py` and `dptr_rebuild_forms.py` already do most of that
machinery over *sites*; nothing does it over the cross-decoder's sample. What a
walk of that kind costs in unattributed `movx`es is already on the record for
one address: `census_xdata_writers.py`'s own blind spot, where the arm walk
charges 100 stores to no address over its 171 rows for 0x0751.

The case for it rests entirely on the 97. `named-past-first-branch` (62) would
be closed by a longer window and nothing else; `no-xdata-named` (493) is not a
blind spot; `entry-is-branch` (356) is a window definition. **So the second
method is worth exactly what the residue is worth, and the residue is the
smallest of the three classes that are blind spots at all** — 97 rows, of which
four are in the PD image. That is the honest size of the case for a DPTR-tracking
walk, and it is smaller than the issue expected.

Against that: a second walk over the same bytes is a second thing to keep in
step with `disasm8051.py`, which is what
`docs/findings/dptr-rebuild-walk-guard.md` is about, and its output would be a
judgement about which reads are folds — the same refusal `disagree` records.
Implementing the method is its own issue, and this is the write-up for the
number that would justify it rather than an argument for it.

## What was decided against, and why

**No new outcome.** `CROSS_DECODER_OUTCOMES` stays at four.
`denominator_line()` and `degenerate_sample_problems()` are untouched, so the
ratchet keeps meaning what it means today. The reasoning is the deliverable:
`outcome` answers "did the comparison agree", `vacuous` is a correct answer to
that, and *why* the row named nothing is orthogonal metadata about the row
rather than a different verdict. §14i is explicit that adding to that
vocabulary is a decision rather than a detail, so the decision is recorded here
— and it is "no".

**Not following the branch's target.** The issue's alternative for the 356 is
that the comparison should follow the branch rather than stop at it. That is
the larger change: it redefines what the window is, so every one of the 2,057
committed rows moves and the baseline has to be re-measured rather than
re-derived. It is a separate issue, and nothing here depends on it — the classes
describe the comparison as it is, which is what makes them a measurement of the
committed ratchet rather than of a proposal.

## Reproducing it

```sh
python3 ec/tools/cross_decoder_blindness.py            # the census above
python3 ec/tools/cross_decoder_blindness.py --check    # recompute and diff
python3 ec/tools/cross_decoder_blindness.py --report   # regenerate the CSV
python3 ec/tools/cross_decoder_blindness.py --self-test
# the denominator line the census is a cut of (--check ratchets on it silently)
python3 ec/tools/build_ec_decompile.py --work /tmp/ec --self-test --cross-decoder
```

`--check` recomputes every row cell-for-cell and fails on a row the sidecar
carries that the sample no longer has, a sampled row it does not carry, any
cell that moved, and a `vacuous` row that fell in no class at all. The
committed file is generated by `--report` and by nothing else, from committed
inputs alone, so refreshing it needs python3 and no Ghidra run.

## Limits

- **The four classes are a partition of one bucket, not a diagnosis.** They say
  what a row's absence is made of; they do not say the comparison is right, and
  a `no-xdata-named` row is not a claim that a register is unused.
- **"The C names an address" is the comparison's vocabulary**, the two
  spellings `build_ec_decompile._EXTMEM` matches. A function that loads 0x07D0
  and writes it through a pointer no symbol carries is `no-xdata-named`, and
  that is a statement about the vocabulary rather than about the function.
- **The walk is linear over the listing's extent.** It is a decode of bytes
  from the entry, not a traversal: a literal in a block this walk desyncs onto
  is not found, and the listing's extent is an upper bound where the boundary
  came from a call-target byte scan (`ec/annotations/bank-call-audit.md` 1).
- **The annotation comment is stripped, and the census does not depend on
  that.** `--self-test` asserts the four counts are identical when every block
  comment is removed instead, so the rule is a choice rather than a reading —
  but it is a choice, and a comment that named an address the body does not is
  prose, not a decode.
- **Nothing here is measured on hardware.** Every figure is a property of
  committed bytes, committed listings and a committed decompile.
