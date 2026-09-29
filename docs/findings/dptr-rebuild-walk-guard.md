# `walk()`'s reload guard covers every way an 8051 rebuilds DPTR, and 21 sites in the image render their `access` cell with the wrong direction, 2 of them in a committed table

(2026-09-28, issue #517. Static reading of committed bytes through
`trace_xdata_refs.py`'s own `walk_why()` and `classify()`. No capture opened,
no EC, no hardware, no Windows, no `registers.yaml` row touched.)

`trace_xdata_refs.walk()`'s reload guard tested one opcode:

```python
if d[i] == MOV_DPTR:
    break  # DPTR reloaded: whatever follows is a different access
```

On an 8051 that comment is true of one of six ways to rebuild the pointer. A
walk ran straight past `mov DPL,A`, past `pop 0x83`, past `mov 0x83,#imm` and
past the rest, so `classify()`'s `reads`/`writes` counters charged the
`movx` **behind** a pointer rebuild to the address the **original** `MOV
DPTR,#imm16` named. The guard is now `is_dptr_rebuild()`, which names all
six.

**The number this exists to record: 21 sites in the image render their
`access` cell with the wrong direction**, across 14 XDATA addresses, 7 in the
common area, 4 in bank 0 and 10 in bank 1. **Two of the 21 are rows in a
committed table** — file offsets `0x16372` and `0x164AE`, both in
`xdata-1c3x-consumers-sites.csv`, the two §6 measures. The other 19 are sites
in the image that no committed table carries, so the 21 is a claim about what
this method renders over the image, not a census of the committed CSVs. The
`0x1C00`-`0x1C3F` page alone carries 197 sites over 26 addresses and three of
its rows changed direction, across two addresses. The whole-image sweep moves
197 of 10,414 mapped `MOV DPTR,#imm16` sites; the other 176 move only the
`terminator` token.

## 1. The six constructions, and the ones that are not among them

| opcode | instruction | length | how often it fires here |
|---|---|---:|---:|
| `0x90` | `mov DPTR,#imm16` | 3 | the pre-existing guard |
| `0xF5` | `mov 0x82,a` / `mov 0x83,a` | 2 | 141 |
| `0xD0` | `pop 0x82` / `pop 0x83` | 2 | 25 |
| `0x88`-`0x8F` | `mov 0x82,rN` / `mov 0x83,rN` | 2 | 29 |
| `0x75` | `mov 0x83,#imm` | 3 | 1 |
| `0x85` | `mov 0x83,0xnn` | 3 | 1 |

`0x85` names its **destination** at `d[i+2]` and its source at `d[i+1]`, the
reverse of every other entry, which is why the predicate's bounds check is
not one index for all of them and why `walk_budget_census.dptr_store_byte()`
asks the opcode before it says which half of DPTR a store wrote.

**`swap` (`0xC4`) is not one of them, and issue #517's own list says it is.**
There is no 8051 instruction that swaps DPTR; `0xC4` exchanges the nibbles of
the accumulator and never touches `0x82` or `0x83`. Adding it would truncate
windows on an instruction that changes nothing. `xch a,0x82` (`0xC5`) *does*
write DPL, and is excluded for the reason in §3. The issue's list is
otherwise right about the constructions — this paragraph is here because a
reader checking the guard against the issue rather than against the opcode
table will find `0xC4` in it.

**The guard keys on bytes, never on the mnemonic text**, and the reason is a
defect that is already in the tree: `disasm8051.mnemonic()` renders the
`0x44`/`0x45`/`0x54`/`0x55`/`0x64`/`0x65` group as **A-operand** forms, so
`54 82` prints as `anl a,#0x82` where the machine writes DPL, and
`OPCODE_LEN` gives that opcode two bytes where `anl direct,#imm` is three. A
text-matching guard would therefore be wrong on exactly the in-place-modify
instructions §3 declines to cover. Fixing the table is out of scope — it
would change text other tools' committed output depends on — and the byte
keying makes it harmless here.
`test_dptr_rebuild_guard.py` asserts the disagreement as a fact about the
tree rather than as a note about it.

**Correction (2026-09-29, issue #1027), leaving the paragraph above as it
was written.** The rendering defect is not the one that paragraph
describes. `0x54` is `anl a,#data`, two bytes, and the renderer is **right**
about it: `mnemonic(54 82)` is `anl a,#0x82` and `OPCODE_LEN[0x54] == 2`,
both correct for the instruction the machine executes. **`54 82` does not
write DPL** — it masks the accumulator — and `anl direct,#imm` is `0x53`, a
different opcode, not a three-byte spelling of `0x54`. The defect is
narrower than "the logical group is miscaptioned": it is confined to the
`direct,A` and `direct,#data` rows of that group, `0x42`/`0x43`/`0x52`/
`0x53`/`0x62`/`0x63`, which the renderer has no spelling for at all and
emits as `db 0x42` and `db 0x63` where the machine writes a byte address.
That is the half a mnemonic-matching guard cannot see, so the paragraph's
conclusion — that a text-matching guard would be wrong on exactly the
in-place-modify instructions §3 declines to cover — stands, and stands on
the corrected account rather than on the one above.
[`dptr-guard-census-vs-1027.md`](dptr-guard-census-vs-1027.md) §2 is where
the correct account is stated and this is worked out against the listings;
`test_dptr_rebuild_forms.py` asserts both halves of it, the `db 0x42` and
`db 0x63` the renderer emits for the direct rows and `OPCODE_LEN[0x53] == 3`
for the three-byte one, beside `anl a,#0x82` for the two-byte accumulator
row it gets right. Out of scope stays out of
scope: fixing the table would move text other tools' committed output
depends on, and the byte keying keeps it harmless here.

## 2. The three sites, read from the `.asm`

The listings settle these and the tool's column does not, which is
`ec/README.md`'s standing instruction. All three were re-read for this file.

**`0xE372`**, bank1, in `FUN_CODE_e2d3` —
`ec/decompiled/bank1/E2D3.asm:63`:

```asm
e372     90 1c 02   mov      DPTR, #0x1c02   ; <- the site
e375     f0         movx     @DPTR, A        ;    0x1C02 <- 0x03C4
e376     54 7f      anl      A, #0x7f
e378     f5 82      mov      DPL, A
e37a     75 83 03   mov      DPH, #0x03
e37d     e0         movx     A, @DPTR        ;    0x0300 + (A & 0x7F), NOT 0x1C02
```

The read is of **`0x0300+(A&0x7F)`**. Corrected cell: `write x1`.

**`0xE4AE`**, bank1, in
`stage_1c00_block_from_code_table_indexed_03c4` —
`ec/decompiled/bank1/E490.asm:27`:

```asm
e4ae     90 1c 02   mov      DPTR, #0x1c02   ; <- the site
e4b1     f0         movx     @DPTR, A        ;    0x1C02 <- the table's byte 2
e4b2     8c 83      mov      DPH, R4
e4b4     8b 82      mov      DPL, R3
e4b6     e0         movx     A, @DPTR        ;    the byte at R4:R3
```

R4:R3 is the CODE table's own two address bytes, read a few instructions
earlier. Corrected cell: `write x1`.

**`0xDE8E`**, bank1, in `FUN_CODE_de3c` —
`ec/decompiled/bank1/DE3C.asm:50`:

```asm
de8e     90 1c 04   mov      DPTR, #0x1c04   ; <- the site
de91     e0         movx     A, @DPTR        ;    a READ of 0x1C04
de92     8a 83      mov      DPH, R2
de94     89 82      mov      DPL, R1
de96     f0         movx     @DPTR, A        ;    a write to R2:R1
de99     90 1c 00   mov      DPTR, #0x1c00
de9c     f0         movx     @DPTR, A
```

Corrected cell: `read x1`. **`0x1C04` is read-only at this site**, and the
issue's own reading agrees with the listing here.

### What `R2:R1` addresses at `0xDE8E`

**Not established from static means, and this file does not guess at it.**
The chain was walked and what it shows is recorded rather than resolved:

- `0xDE8E` is inside `FUN_CODE_de3c`, which has exactly one direct call site
  in bank 1: the tail-jump at `ec/decompiled/bank1/AC36.asm:11`
  (`write_1c00_ff_and_0680_04`), itself reached only through the jump table
  at `0x98B4` that `dispatch_0680_low3_via_98b4_table` indexes with
  `0x680 & 0x7` — entry 3 is the `ljmp 0xac36` at `0x98BD`. That
  dispatcher's one caller is `call_8f6b_98cc` at `0xAB7F`, called from
  `0x8A22`.
- Decoding every instruction on that path (`0x8A04`-`0x8A26`, `0xAB7F`-
  `0xAB86`, `0x8F6B`, `0x98CC`-`0x98E5`, `0xAC36`-`0xAC43`, `0xDE3C`-
  `0xDE9E`) finds **no instruction that writes `R1` or `R2`**.
- So `R2:R1` is whatever the caller *above* `0x8A04` left in those registers,
  and that caller's arguments are not recoverable from this path.

**CORRECTION 2026-09-28, issue #1296: the second half of that last bullet is
wrong, and the walk above is what missed.** The reading above decoded the
*caller-side* path and stopped; the clobbering instructions are in a
**callee**, `bank1,0xB6DE`, reached over the `lcall 0xB6DE` at `0xDE89`
(`ec/decompiled/bank1/DE3C.asm:48`) — twelve bytes below the store and
inside the routine whose own frame the walk was reading. `mov R1,A` at `0xB6E2`
and `mov R2,A` at `0xB6E9` are what supply the two bytes, and a linear
window cannot cross the call, which is the same edge `walk()` stops at. So
`0xB6DE` sat outside the six decoded ranges and the omission was structural,
not a gap in the decode.

What the pointer holds is now established, and it is neither a caller's value
nor a single address: **`DPH` is the byte at XDATA `0x0564` and `DPL` the byte
at XDATA `0x0563`**, both staged by `0xDE3C` itself from two CODE tables, so
the store writes the 16-bit value that pair spells — a bounded set, not an
unconstrained pointer and not a constant. The argument, the enumeration and
the `test_de3c_store_target.py` negative that would falsify it are in
[`de3c-1c04-to-0563.md`](de3c-1c04-to-0563.md). The corrected `read x1` cell
at `0xDE8E` is **unaffected**: it was right, and it now rests on more than the
eight-instruction window it was read from. Nothing in §6 moved.

The decompile agrees and is explicit about it: `ec/decompiled/bank1/DE3C.c:50`
reads `*(undefined1 *)CONCAT11(param_2,param_1) = DAT_EXTMEM_1c04;`, with
`param_1`/`param_2` the un-initialised `R1`/`R2`. **The site's write is
therefore a write to a caller-supplied address, not to any byte of the
`0x1C00` block** — which is the strongest statement the bytes support, and it
is the statement the corrected `read x1` cell rests on. Naming the address
itself needs a caller-side walk and is not done here.

**CORRECTION 2026-09-28, issue #1296, continuing the one above: the decompile
is not a second witness here.** Ghidra named the routine's *incoming* `R1`/`R2`;
the store reads the values those registers hold *after* `0xB6DE` overwrote
them, so "the decompile agrees" was the same instructions read twice. And the
"caller-supplied address" is now named in the correction above, from the other
end of the chain. The claim that survives from this paragraph is the narrow
one: the `read x1` cell rests on `0x1C04` being *read* at this site, and that
is unchanged.

**What the block at `DE81`-`DE8C` does not establish.** The issue suggests
that block "reads/writes `0x0561` and does `anl A,#0x7f`, which is the shape
of a 128-entry indexed table", and asks whether `R2:R1` points at a byte the
same block owns. The shape is real — `0xDE81`-`0xDE88` is a read-modify-write
of `0x0561` masked to 7 bits — but `0x0561` is indexed by `R5` earlier in the
routine (`de46`-`de48`), not by `R2:R1`, and the masked value is never
written to DPTR. **So no: the block's own table is `0x0561`-indexed and
`R2:R1` is not derived from it.** That is a reading of the listing, not a
deduction, and it is stated here so the follow-up starts from it.

## 3. What the guard deliberately still does not stop

The instructions that **modify** DPTR in place rather than replace it:
`anl`/`orl`/`xrl direct,#data` (`0x53`/`0x43`/`0x63`) and the `direct,A`
half of the same group (`0x52`/`0x42`/`0x62`), `inc 0x82` (`0x05`),
`dec 0x83` (`0x15`), and `xch a,0x82` (`0xC5`). They change the address the
following `movx` reaches, so this is a real limit and not a clean line. (The
six opcodes are corrected from the list this section first gave, which named
`0x54`/`0x44`/`0x64` — the accumulator `#data` rows, which touch A rather
than DPTR at all. `IN_PLACE_FORMS` in `dptr_rebuild_forms.py` already named
the six correctly, and §1 carries the correction beside the sentence it
belongs to.)

They are excluded because they are masking or arithmetic **on the pointer
that is already there**, and the tool already treats the sequential `inc dptr`
(`0xA3`) as a span walk that `classify()` renders as
`walks N consecutive bytes` rather than as a terminator. Calling an in-place
mask a "reload" is a second judgement about what the word means, and the
`0x2C2FA` case in [`walk-window-terminators.md`](walk-window-terminators.md)
is the argument for what it would cost: that row's `mov 0x82,a` /
`mov 0x83,a` pair is an *indexed* access, and widening the guard to the
in-place forms is a different change with a different census behind it.

`xch a,0x82` is the honest edge — it does write DPL — and it is in the same
class as the rest of them, so it is out for the same reason rather than by
oversight. All of these are held as negative cases in
`test_dptr_rebuild_guard.py`, so a later widening is a deliberate edit to a
named test rather than a silent one. **The broader reading is a follow-up
issue.**

**And one form the guard does not stop which is not a decision at all.**
`mov direct,@Ri` (`0x86`/`0x87`) replaces DPTR's byte by exactly the
argument every form in `DIRECT_STORE_OPS` replaces it by, and neither
`is_dptr_rebuild()` nor the list above names it. That is an oversight rather
than a reading of the word "reloaded", and it is recorded here rather than
fixed here because widening the guard is a different change with a different
census behind it -- the same argument as the paragraph above, arrived at from
the other side. The measurement side is already done:
[`dptr-guard-census-vs-1027.md`](dptr-guard-census-vs-1027.md) §3 counts the
form and finds 11 byte pairs over the committed image, **all 11 of them
mid-instruction** -- each is the middle and last byte of an `lcall 0x8782` --
so no window this guard actually walks is affected today. That is a fact
about this image and not a reason to leave the list wrong:
`ec/tools/dptr_rebuild_forms.py` counts the form anyway, and
`test_dptr_rebuild_forms.py` holds the difference between the two opcodes
lists as `GUARD_GAP_OPS` so the census is not quietly inheriting it.

## 4. A second, narrower copy of the list, and the class that emptied

`ec/tools/walk_budget_census.py` carried its own
`DIRECT_STORE_OPCODES = (0xF5, 0x8F)` to split its class A/B verdicts. `0x8F`
is `mov direct,r7`, so that tuple covered `mov direct,a` and `mov direct,r7`
**only** — it missed r0-r6 entirely and `0x75`, `0x85` and `0xD0` outright.
The list now lives in one place: `is_direct_dp_store()` is a one-line
delegation to `is_dptr_rebuild()`, and a case in the new suite crosses all
256 opcodes with three operand bytes and holds the two names to one answer.

**The consequence is the strongest evidence in this file.** With the guard
widened, class A does not shrink — it **empties**:

| | rows | class A | class B | unchanged | cells that move |
|---|---:|---:|---:|---:|---:|
| before | 45 | 10 | 3 | 32 | 13 |
| after | **15** | **0** | 3 | 12 | 3 |

Thirty rows that used to run to the instruction budget now stop on `DPTR
reloaded` before the budget is gone, and the ten class-A rows were exactly
the ones whose `access` cell a larger budget would have got wrong. **A
verdict class that empties is the clearest available confirmation that the
diagnosis was right and that the guard was what needed fixing** — it is the
same finding `walk-window-terminators.md` reached from the other end, where
`pd-index-geometry.md` already held the contradicting reading for `0x2C2FA`.

## 5. Why no sixth terminator token

The issue offered a choice: break the walk on each construction, **or** record
a `DPTR rebuilt` category the way `movc` and `jmp @a+dptr` already are. The
first was taken, and no new token was added, for a reason the tool already
states: the terminator names were *lifted into* `trace_xdata_refs.py` precisely
so that the `--terminator-column` output and the 119530 of
[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) are one
measurement in two places rather than two vocabularies for one event. That
census counted the `d[i] == MOV_DPTR` disjunct's row and named it
`DPTR reloaded`; the other five forms were reloads the same name was silent
about, and the token now says what it always meant more often. A sixth token
would split one event in two. `--terminator-column`'s help text still reads
"which of the **five** `walk_why()` terminators", and it is still true.

Measured the way that census measured its four rows — `walk()` driven from all
262144 offsets of the image, both guards, §9 step 9b — the token's population
went from that census's own **26257** to **31655**, and the
`max_insns (8) exhausted` row went the other way, **119530** to **117520**.
The direction is stated rather than left to be inferred, because the opposite
is the intuitive one: a wider reload guard can only stop a walk *sooner*, so
it moves walks off the budget and off `flow opcode` (116347 → 112959) and onto
the reload row, never the reverse. The two deltas are 2010 and 3388, and they
sum to the 5398 the reload row gained.

The `terminator` column already carried `DPTR reloaded` at these rows; what
was missing is that the **default** `--csv` output has no `terminator` column,
so the `access` cell has to be right on its own. That is the whole of why the
guard is the fix rather than the column.

## 6. What changed in the committed data

Seven tables were regenerated **from the tool**, never by hand, each with the
command its own page prints:

| table | rows that moved | which cells |
|---|---:|---|
| `xdata-1c3x-consumers-sites.csv` | 2 | `access` **and** `window`: `read x1, write x1` → `write x1` (`0x16372`, `0x164AE`) |
| `ec-07c4-07d5-sites.csv` | 9 | `window` **and** `terminator` |
| `ec-07d6-07d7-sites.csv` | 10 | `window` and `terminator` (7 rows), `terminator` alone (3) |
| `ec-0x07d0-sites.csv` | 3 | `window` **and** `terminator` |
| `ec-0x07d1-sites.csv` | 8 | `window` **and** `terminator` |
| `xdata-086x-dispatch-sites.csv` | 1 | `window` alone: `0x0867` at pd-image `0x9056` loses `mov 0x82,a ; mov 0x83,0xf0 ; ljmp 0x0f65`; its `access` stays `read x1` and its `census` cell is `not recorded`, so `check_site_census.py` is unaffected |
| `walk-budget-census.csv` | 45 → 15 | §4 |
| `xdata-0400-045f-sites.csv`, `manual-fan-ctrl-0751-sites.csv` | 0 | unchanged, byte for byte |

Every `window` cell that moved is **shorter**, cut at the DPL store the
widened guard now stops on — which
`test_walk_budget_census.py::test_the_widened_guard_only_shortens_windows_and_moves_no_access_cell`
holds by rule rather than by a list of the 27 addresses, since a list would
be a value every re-cut has to edit.

**No `access` cell moved in the six tables that carry one**, and that is
stated as a measurement rather than an assertion: the diff of each of the six
against its pinned baseline contains no `access` cell, and
`test_walk_budget_census.py` holds it there by rule. The two `access` cells
that did move are in `xdata-1c3x-consumers-sites.csv`, which is one of the
three the earlier work deliberately did **not** re-cut under the
`terminator` column.

The default `--csv` output is unchanged — no column was added — so
`xdata-086x-dispatch-sites.csv`'s own `--check`, which the module docstring
names as the regression test, still reproduces byte for byte after a
regeneration that moved one of its `window` cells.

`MOV_DPTR` stays a named constant and `sites_for()` is unchanged. The
widened guard fixes the **direction** of rows at existing sites; it does not
create new sites. A `mov DPL,A` is not a reference to any address, and the
`static_refs` counts in `registers.yaml` do not move — which is why
`0x1C02`'s row there was already correct (0 read / 13 write, with a note
naming both misattributed sites) and needed no edit.

## 7. What this does not establish

- **Nothing about what the EC does.** Every input is a committed file: a site
  table and `ec/firmware/GMxMGxx_11.800`. An `access` cell is a reading aid
  over at most 8 instructions of a linear window that cannot follow a branch.
  "21 sites render their `access` cell with the wrong direction" is a claim
  about what this method renders, not about the firmware's intent — and a
  window that ends earlier is not a window that is now right about everything
  behind it.
- **Nothing about the in-place-modify forms** (§3). A real limit, named.
- **What `R2:R1` addresses at `0xDE8E`** (§2). Not established, and not
  guessed.
  **CORRECTION 2026-09-28, issue #1296: established.** The high byte is the
  byte at XDATA `0x0564` and the low byte the byte at XDATA `0x0563`, both
  written by the callee `0xB6DE` and staged by `0xDE3C` itself from two CODE
  tables — so the store's target is a bounded set of addresses, enumerated
  from the image in [`de3c-1c04-to-0563.md`](de3c-1c04-to-0563.md). The line
  above is left as it was written; §2 carries the correction beside it.
- **A `registers.yaml` row for `0x1C04`.** None exists. Creating one is a
  status decision with a `static_refs` census behind it, gated by
  `check_register_counts.py` and `check_status_vocabulary.py`; the issue
  notes the row does not exist yet, and this records the corrected direction
  rather than inventing a row. **Natural follow-up issue.** The same goes for
  the direction totals the issue quotes for `0x1C04` ("8 reads and 14
  writes"): this sweep of the 23 sites gives **9 `read x1` and 14
  `write x1`**, which is 8 reads plus the `0xDE8E` read the pre-fix window
  had folded into a read-modify-write. The figure is stated here as this
  method's output; the committed table that would back it does not exist.
- **`disasm8051.mnemonic()`'s `0x42`/`0x43`/`0x52`/`0x53`/`0x62`/`0x63`
  rows**, which it emits as `db 0x42` and `db 0x63` where the machine writes
  a byte address (§1). A real defect, held harmless here by the byte keying,
  and changing it would move text other tools' committed output depends on.
  **Follow-up issue.** The accumulator half of the same logical group
  (`0x44`/`0x45`/`0x54`/`0x55`/`0x64`/`0x65`) was named here before it, and
  is **not** part of the defect: those render correctly. §1's first account,
  still visible there, is the version being corrected.
- **#399's `dptr-carried`.** Complementary, not overlapping: that is the
  `movx` in the **caller**, past the `lcall`; this is the `movx` in the
  **same** listing, after a pointer rebuild. Neither subsumes the other, and
  the two should be coordinated rather than merged.
- **Any hardware or Windows step.** None is needed and none is claimed. No
  capture was opened, no register read back, no EC or HID node touched. The
  toolchain needed is `python3` and the committed firmware — no Ghidra, no
  `analyzeHeadless`, no `ilspycmd`, no radare2.

## 8. The test, and where the regression gate is

`ec/tools/test_dptr_rebuild_guard.py` is the new suite: hand-built
`common`-region fixtures, no firmware image and no hardware, the house
pattern. **It fails on the pre-fix guard** — reverting the one line in
`walk_why()` turns 21 of its 27 cases red, which was checked rather than
assumed, by running the suite against `b0b0c09c`'s `walk_why()` with the new
predicate grafted onto it.

It holds the guard per construction, the negatives (`swap a`, `xch a,0x82`,
`mov a,0x82`, `push 0x82`, and the in-place forms) with `0xC4` asserted
absent *by name* so the issue's list cannot be re-copied in, the `0x85`
bounds case on a short buffer, the cross-tool agreement sweep, and the
`TERMINATORS` count staying at five. It asserts **no count of rows,
addresses or tables** — a figure every re-cut would have to edit is what
CLAUDE.md warns against — and the census numbers live in this file as prose.

The firmware-level regression stays where the repo puts it: the seven
`--check` runs against the regenerated CSVs, which is a stronger gate than a
fixture asserting a census number.

## 9. Reproducing it

All of it, from the repository root. The regenerated tables first, then the
checks that consume them, then the suite.

```sh
# 1-5. the five `--terminator-column` tables, each by the command its page prints
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x07C4 0x07D3 0x07D4 0x07D5 --csv --terminator-column \
  | diff - ec/annotations/ec-07c4-07d5-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x07D6 0x07D7 --csv --terminator-column \
  | diff - ec/annotations/ec-07d6-07d7-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 --csv --terminator-column \
  | diff - ec/annotations/ec-0x07d0-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D1 --csv --terminator-column \
  | diff - ec/annotations/ec-0x07d1-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --csv --terminator-column \
  | diff - ec/annotations/manual-fan-ctrl-0751-sites.csv

# 6-7. the two that carry no terminator column, one of which did change
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x1C39 0x1C3A 0x1C12 0x1C13 0x1C14 0x1C36 0x1C37 0x1C38 \
  0x1C01 0x1C02 0x1C03 --csv \
  | diff - ec/annotations/xdata-1c3x-consumers-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
  0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check

# 8. the census, whose class A is now empty
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --check

# 9. the whole-image sweep of §1's table, over the 10,414 mapped sites
PYTHONPATH=ec/tools python3 - <<'EOF'
import collections, importlib.util, sys, subprocess
import trace_xdata_refs as T
# b0b0c09c's walk_why: a before-state that is not this file's fix. A pinned
# SHA, this work's parent and the tip of main before it, rather than `HEAD^`:
# `HEAD^` names the pre-fix guard only on a branch's first commit, and a later
# fix round that does not touch this file still moves it onto a commit that
# already holds the widened guard -- this branch's own `5fb7581e` does -- at
# which point the sweep compares each walk with itself and prints 0.
src = subprocess.run(["git", "show", "b0b0c09c:ec/tools/trace_xdata_refs.py"],
                     capture_output=True, text=True).stdout
open("/tmp/old_tref.py", "w").write(src)
spec = importlib.util.spec_from_file_location("old_tref", "/tmp/old_tref.py")
OLD = importlib.util.module_from_spec(spec); sys.modules["old_tref"] = OLD
spec.loader.exec_module(OLD)
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
off, magic = T.PD_MARKER
pd = d[off:off + len(magic)] == magic
rows = collections.Counter(); acc = collections.Counter(); cons = collections.Counter()
n = 0
for o in range(len(d) - 2):
    if d[o] != T.MOV_DPTR:
        continue
    n += 1
    oi, ow = OLD.walk_why(d, o)
    ni, nw = T.walk_why(d, o)
    if oi == ni and ow == nw:
        continue
    rows[T.region_of(o, pd)[0]] += 1
    if T.classify(oi) != T.classify(ni):
        acc[T.region_of(o, pd)[0]] += 1
    at = ni[-1][0] + len(ni[-1][1])
    cons[f"0x{d[at]:02X}"] += 1
print(n, "sites;", sum(rows.values()), "rows move", dict(rows))
print(sum(acc.values()), "access cells move", dict(acc))
print("constructions:", dict(cons.most_common()))
EOF
# which prints, verbatim, and is the derivation of §1's table and the 197 / 21:
#   10414 sites; 197 rows move {'common': 25, 'bank0': 61, 'bank1': 18, 'pd-image': 93}
#   21 access cells move {'common': 7, 'bank0': 4, 'bank1': 10}
#   constructions: {'0xF5': 141, '0xD0': 25, '0x8F': 20, '0x8A': 5, '0x8D': 3, '0x75': 1, '0x8C': 1, '0x85': 1}

# 9b. §5's four rows under both guards. This is
# opcode-len-bounds-census.md's own all-offsets drive, re-run with the guard
# as a parameter rather than pasted in, so the 26257/119530 the census commits
# and the 31655/117520 §5 quotes are one script rather than two transcriptions.
python3 - <<'EOF'
import collections, sys
sys.path.insert(0, "ec/tools")
import trace_xdata_refs as T
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()

def census(buf, guard):
    ended = collections.Counter()
    for start in range(len(buf)):
        i = start
        for _ in range(8):
            n = T.OPCODE_LEN[buf[i]]
            if i + n > len(buf):
                ended["instruction does not fit"] += 1; break
            if buf[i] in T.FLOW_OPCODES:
                ended["flow opcode"] += 1; break
            i += n
            if i + 2 >= len(buf):
                ended[T.BUFFER_END] += 1; break
            if guard(buf, i):
                ended[guard.__name__] += 1; break
        else:
            ended[T.budget_end(8)] += 1
    return ended

def before(buf, i):
    """The census's `d[i] == MOV_DPTR` disjunct, the guard as it was."""
    return buf[i] == T.MOV_DPTR
before.__name__ = "d[i] == MOV_DPTR -- the DPTR test"

for guard in (before, T.is_dptr_rebuild):
    ended = census(d, guard)
    print("walk() driven from all %d offsets, %s:" % (len(d), guard.__name__))
    for why, n in ended.most_common():
        print("  %8d  %s" % (n, why))
    print()
EOF
# which prints, verbatim, the census's own four rows under `before` and the
# widened four under `is_dptr_rebuild`:
#   119530 max_insns (8) exhausted / 116347 flow opcode / 26257 the DPTR test / 10 end of buffer
#   117520 max_insns (8) exhausted / 112959 flow opcode / 31655 is_dptr_rebuild / 10 end of buffer

# 10. the suites: this work's own, the census's, and the runner's total
python3 -m unittest discover -s ec/tools -p test_dptr_rebuild_guard.py
python3 -m unittest discover -s ec/tools -p test_walk_budget_census.py
bash tools/run-tests.sh
```

Steps 6-7 are the two that would catch a mistake in the other direction. Step
7 is the fifteen-address `0x086x` sweep diffing against a table this work did
**not** re-cut under the terminator column, and it is what makes "the default
output has no column in it" checkable. Step 9's sweep is the only place the
whole-image figures are derived, and it takes its "before" from `git show`
rather than from a hand-copied loop. **The ref is the pinned SHA `b0b0c09c`**,
this work's parent and the tip of `main` before it, rather than anything
derived from where the branch happens to sit. The three relative refs each
fail, and each was checked rather than reasoned about:

- **`HEAD`** is this file once the work lands, so the sweep compares each
  walk with itself and prints `0 rows move` / `0 access cells move` while the
  figures this file reports stand.
- **`HEAD^`** holds the pre-fix guard only on a branch's *first* commit. This
  branch's review rounds are not: `5fb7581e` does not touch
  `trace_xdata_refs.py`, so from `2abd4cf5` onward `HEAD^` already holds the
  widened guard — the same `0 rows move`, arriving by the ref that was meant
  to exclude it. A fix round is exactly the event that moves a commit under
  a relative ref, and only one that edits this file would have kept it honest.
- **`git merge-base HEAD origin/main`** reads correctly today and fails the
  same way afterwards. Checked by merging this branch into `main` locally:
  the merge-base is `b0b0c09c` only while `origin/main` still sits behind the
  merge. Once it advances to the merge commit — which is what a merged tree
  looks like to the person running the recipe — the merge-base *is* that
  commit, and it holds the re-cut.

A SHA is the only one of the four that is the same object on the branch, in a
rebase, and on the merged tree, and `b0b0c09c` is reachable in the full-depth
`gates` job. It is the same remedy `tools/README.md` records for
`test_walk_budget_census.py`'s baseline ref, which pins `5672042a` for the
same reason: both `HEAD` and `origin/main` hold the re-cut once a change
lands, and a baseline that already contains the change pins nothing.
