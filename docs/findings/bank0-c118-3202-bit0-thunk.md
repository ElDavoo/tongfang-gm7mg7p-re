# bank0 `0xC118` is a thunk on `test_3202_bit0`, and it is one of four in an unexported run

`bank0 0xC118` is now a committed listing. It is the address bank1's
`trampoline_to_c118` reaches, so it is a **bank-0** address read in bank 0, and
the bank is what made it worth seeding: the two programs hold different bytes at
the same address, and an earlier reading took bank 1's. This is the write-up for
issue #337, which asks for the address to become a citation rather than a
reading.

Everything here is a static decode of `ec/firmware/GMxMGxx_11.800`. No
register was read back, no hardware was involved, and nothing below is a claim
about what the EC does with the value at run time.

## 1. The forwarding, and why the address is a bank-0 one

`ec/decompiled/bank1/19A8.asm` is two instructions:

```
19A8     90 c1 18 mov      DPTR, #0xc118
19AB     02 11 00 ljmp     0x1100
```

`0x1100` is the common-area stub this tree names `bl51_bank_select_0`, and
[`ec/annotations/bank-call-audit.md`](../../ec/annotations/bank-call-audit.md) §2
counts the trampolines that route through it. The `imm16` is therefore
resolved *after* the bank switch — in bank 0, not in the bank the forwarder
sits in. `ec/annotations/bank-call-targets.csv` records the target site
independently at the row for file offset `0x0C118` as a bank0 `lcall` entry.

## 2. The bytes, in each bank

Read straight out of the image; the bank images put a CODE address at the same
offset as its file offset, so these are both 0xC118.

| read from | file offset | bytes |
|---|---|---|
| bank 0 | `0x0C118` | `12 c0 e7 ef 60 03 7f 01 22 7f 00 22` |
| bank 1 | `0x14118` | `f3 4d f0 22` |

The bank-1 bytes are **byte 1 of the `anl A,#0xf3` at `0x14117`**, in a program
that has nothing to do with the routine bank 0 holds there. A decode anchored at
bank 1's `0xC118` therefore lands mid-instruction, which is the whole of the
withdrawn reading: from those four bytes it was correctly said that no
instruction writes R7, and that said nothing about what runs, because those
four bytes are not what runs.

`ec/decompiled/bank0/C118.asm` is the bank-0 reading:

```
C118     12 c0 e7 lcall    0xc0e7
C11B     ef - -   mov      A, R7
C11C     60 03 -  jz       0xc121
C11E     7f 01 -  mov      R7, #0x1
C120     22 - -   ret
C121     7f 00 -  mov      R7, #0x0
C123     22 - -   ret
```

Seven instructions in twelve bytes. It calls `0xC0E7`, copies the answer into A,
and **restates it in R7** as a 1 or a 0 — it adds nothing to what the callee
returned, and the four instructions between the call and the branch are that
restatement rather than a second test. `0xC0E7` is annotated
`test_3202_bit0` and reads bit 0 of XDATA `0x3202`, so **what the callers of
`0x19A8` branch on is bit 0 of `0x3202`**, carried out of a call rather than
tested here.

The decompiled C drops the R7 return entirely — `C118.c` prints
`test_3202_bit0(); if (param_1 != '\0') { return; } return;`, with no
assignment to R7 anywhere — so the `.asm` is the only statement of the result.
That is the same defect `0xC0E7` and `0xC0C9` record in their own comments, and
it is why the annotation row points at both files rather than the C alone.

The `sdas8051` re-encode of this listing agrees with the firmware: the row in
[`ec/ghidra/reassembly.csv`](../../ec/ghidra/reassembly.csv) reads `match`, with
every instruction in the function re-encoded and compared.

## 3. The four-thunk run, and the 36 bytes still not exported

The gap is wider than one thunk, and measuring it was part of the work.
`ec/decompiled/index.csv` puts `0xC0E7`'s listing at 13 bytes, so it ends at
`0xC0F3`, and the next bank0 row is `0xC124`. **`0xC0F4`-`0xC123` is 48 bytes**,
and they are four identical twelve-byte thunks:

| address | calls | callee is | exported |
|---|---|---|---|
| `0xC0F4` | `lcall 0xC0B8` | `return_1_unless_3202_bits_1_and_2` | no |
| `0xC100` | `lcall 0xC0DA` | `return_1_unless_3202_bit0` | no |
| `0xC10C` | `lcall 0xC0C9` | `return_1_if_3202_bits_1_and_2` | no (issue #255's) |
| `0xC118` | `lcall 0xC0E7` | `test_3202_bit0` | **this change** |

All four callees were already annotated before this one. All four thunks are the
same seven instructions over the same 1-or-0 restatement, so the run is one
pattern the firmware emits four times rather than four unrelated routines.

**Seeding `0xC118` leaves `0xC0F4`-`0xC117`: 36 bytes, three thunks.** Those are
*not exported*, which is not the same as *not code* — they are twelve bytes each
of the same shape, and the way to land them is the same export this one used.
`0xC10C` is issue #255's, per that issue's own instruction, and is not absorbed
here. No status anywhere moves on the strength of this section.

## 4. The callers: six annotated rows, and the census behind them

Six rows of [`ec/annotations/ghidra-variables.csv`](../../ec/annotations/ghidra-variables.csv)
branch on the R7 this address leaves, and all six now cite
`ec/decompiled/bank0/C118.asm` in their `evidence` cell. The set is the six
*addresses*, not a set of keys, and that distinction matters:

| address | key | covers |
|---|---|---|
| `0x90B8` | `r7_from_1984` | three callees at once, `0xC118` among them |
| `0x9199` | `r7_from_a_callee` | `0x1984` and `0x19A8` |
| `0x9CC0` | `r7_from_19a8` | `0x19A8` alone |
| `0xA064` | `r7_from_19a8` | `0x19A8` alone |
| `0xA4CF` | `r7_from_a_callee` | `0x1984` and `0x19A8` |
| `0xC614` | `r7_from_a_callee` | `0x1984` and `0x19A8` |

Five rows carry `r7_from_19a8` or `r7_from_a_callee`; the sixth, `0x90B8`, is
keyed `r7_from_1984` because that is the call its *name* comes from, while the
listing tests three callees. Reading the issue's "every `r7_from_19a8` /
`r7_from_a_callee` row" as the set would have missed it.

**These rows were not open questions.** Each was corrected on 2026-09-24 under
#255, and each already named `0xC118` as a real bank-0 entry lcalling `0xC0E7`.
What they said was *"None of the three is exported, so every statement about
them here is a reading of the image rather than of a listing"* (`0x90B8`). So
this change **upgrades a reading into a citation**; it does not answer a
question the rows had left open, and their `CORRECTION` blocks stay visible with
the citation beside them, per CLAUDE.md's calibration rule.

### 4a. Six is a count of annotated listings, not of callers

`ec/annotations/bank-call-targets.csv` records the `lcall 0x19A8` sites in
bank1, and there are more of them than the six annotated rows. Classifying each
site by whether it falls inside a committed bank1 listing:

- most of them do, and most of those are not among the six;
- **one, `0x8255`, is not covered by any committed bank1 listing**, so nothing
  in the tree says what that call site does with the answer.

Only `0x8255` is named here. The other sites' listings are already in the tree
and what they do with the R7 is their own rows' business, not this one's.

Reproduce by joining `bank-call-targets.csv`'s bank1 `lcall` rows targeting
`0x19A8` against the `addr`/`size` columns of `ec/decompiled/index.csv`. What
that leaves unstated is a census fact, not work done here: no listing is derived
for any site, and the one uncovered site is recorded rather than read.

## 5. What this does not establish

- **Nothing live.** The R7 described here is what the code leaves in a
  register, not a value observed on hardware. Whether the six callers' branches
  are taken in practice, and what `0x3202` bit 0 selects, are both open.
- **Nothing about `0x3202` itself.** It carries `XDATA_3202` at
  `present-untested`, with no writer found by that row's method — a gap in the
  search, not evidence that none exists. This change moves no register status.
- **Nothing about the 36 bytes still unexported** in §3, or about bank0 `0xC391`
  (named by the `0x1990` forwarder, the same shape of question, unmeasured
  here).
- **No project rebuild.** The committed `.gpr`/`.rep` was copied to scratch and
  never opened for writing; the annotation change is a CSV row and a text diff,
  not a binary one.

## 6. How to check this

The suite is [`ec/tools/test_bank0_c118_thunk.py`](../../ec/tools/test_bank0_c118_thunk.py),
which holds three claims: the listing's bytes are the image's bytes at that
address; the two banks' `0xC118` are not the same bytes, measured from the image
on both sides; and the six caller rows cite the listing and keep their
corrections.

```sh
python3 -m unittest discover -s ec/tools -p "test_bank0_c118_thunk.py"
```

The bulk of the proof is the existing gate rather than this suite:
`build_ec_decompile.py --check` / `--self-test` hold the listing bytes against
the image, every annotation row resolving to a real exported function, and the
`subsystems.md` recount; `verify_reassembly.py --check` holds the new report
row; and `call_graph.py --check` holds the new edge, which is `0xC0E7` gaining
its first caller.