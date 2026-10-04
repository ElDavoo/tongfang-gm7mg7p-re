# A trampoline target inside a `ret` run is a one-instruction far routine, and the bank-pointer reading does not survive the stub's bytes (issue #1090)

[`trampoline-target-census.md`](trampoline-target-census.md) (issue #574) gave
every entry in the BL51 block a decoded target, read in the bank its own
tail-jump stub selects, and stopped there. Its own words for what it would not
say: *"It does **not** say those calls are dead, that the addresses are
unreachable, or that the run is padding."* This is the other half — **what a
target inside a `ret` run is** — plus the one correction the tree needs before
any answer to it can be right.

The committed table is
[`ec/annotations/trampoline-target-reading.csv`](../../ec/annotations/trampoline-target-reading.csv),
one row per entry, adding two columns the census's could not carry: `ret_run`,
the run of identical bytes the target sits in, and `call_sites`, how many
committed call sites reach the entry that names it.

```console
$ python3 ec/tools/trampoline_target_reading.py --write
$ python3 ec/tools/trampoline_target_reading.py --check
$ python3 ec/tools/trampoline_target_reading.py          # the tables below
```

Entries, stubs, banks and target bytes are **imported** from
`trampoline_target_census.py` rather than re-scanned, and the call sites are
read out of the committed `bank-call-targets.csv`. So this table cannot
disagree with the census about a byte; a drift in either is a red run in both
suites, which cross-check the two committed tables against each other.

**Nothing here was observed on hardware.** No register was read back, no capture
opened, no Windows machine and no Ghidra run. Every figure is a static read of
`ec/firmware/GMxMGxx_11.800` and of files already committed, and no `status:` in
`ec/annotations/registers.yaml` moves on any of it.

## The correction: the trampoline hands back nothing

The reading this issue was opened with is that a target inside a `ret` run is
the Keil idiom for *handing a caller a bank pointer* — `lcall` an entry, it sets
DPTR to a bank address, switches the bank, and returns, so the caller reads a
pointer into the newly-selected bank. It is the reading that makes the 138-byte
run uninteresting and the 146 single-caller thunks exactly what to expect. It is
also **wrong on the stub's own bytes**, and the tree already says so.

The bank-switch stub at `0x1100` is 20 bytes:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x01100 --runtime 0x1100 -n 10
0x1100  c008     push 0x08
0x1102  7411     mov  a,#0x11
0x1104  c0e0     push 0xe0
0x1106  c082     push 0x82
0x1108  c083     push 0x83
0x110a  75080a   mov  0x08,#0x0a
0x110d  c290     clr  0x90
0x110f  c291     clr  0x91
0x1111  c292     clr  0x92
0x1113  22       ret
```

Reading the operands: `0x82` and `0x83` are DPL and DPH, `0x90`/`0x91`/`0x92`
are DPL/DPH/DPS again, and `0x08` is the direct byte the four stubs each write
their own bank value into. So the stub pushes the bank register, pushes a marker,
pushes DPTR, selects a bank, **zeroes DPTR**, and returns.

That `ret` consumes the two DPTR bytes just pushed and uses them as a **jump
target**. So control arrives *at the far address*; what the far routine's own
`ret` pops is the marker above it — the accumulator and the saved `0x08` — and
not the caller's return address. DPTR is `0x0000` on return, so there is no
pointer to read.

This is not a new reading.
[`scheduler-run-8518-entries.md`](scheduler-run-8518-entries.md) §2 derives it
from these bytes and `run_entry_map.py --self-test` re-derives the landing
window from them; `test_trampoline_target_reading.py` holds the shape, so a stub
that stopped having it would redden a run rather than leave this reading
resting on nothing.

**What follows for the 149.** A trampoline target is not an address a caller
*learns the contents of*. It is an address the CPU **jumps to**, in the bank the
stub just selected. So when that first byte is `0x22`, the far routine is **one
instruction long** — it returns immediately — and control resumes in the stub
window. That is the settled part, and it is a statement about mechanism.

The reading also survives a check the issue's framing did not ask for: the
entries reach their target by **`ljmp` 163 times to `lcall`'s 5**
(`caller_ops` in the table). A tail jump has no caller to hand a pointer back
to.

## What the run is, and what that decides

`ret` is one byte and ends a routine, and the tree holds named one-instruction
`ret` routines — `bank0,0xD9DB` `ret_stub`, `bank0,0xD2BE` `ret_only_d2be`,
and issue #559's `0xD89F` — so a single byte decides nothing. The **run**
decides, and the threshold is where the population stops moving rather than
where it first looks meaningful:

| threshold | 2 | 3 | 4 | 5 | 6 | 7 | **12** | 17 | 18 | 24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entries | 167 | 160 | 154 | 151 | 151 | 149 | **149** | 149 | 133 | 133 |

The count is **flat from 7 to 17** and bounded by a measured fall on each side:
at 6 a 6-byte run joins, at 18 the 17-byte run drops out while the 138-byte one
has not. `trampoline_target_reading.MIN_RET_RUN` is 12, strictly inside that
band rather than at either edge — at an edge it would be one step away from a
different population. `--self-test` walks *every* threshold from the shortest run
to the longest and derives both bounds, so the band is a property of the image
rather than of where a sweep stopped.

Two runs carry the whole population, and both are bank 0:

| bank | run | bytes | targets | call sites |
|---|---|---:|---:|---:|
| bank 0 | `0xBF54`-`0xBFDD` | 138 | 133 | 152 |
| bank 0 | `0xBF1B`-`0xBF2B` | 17 | 16 | 16 |

**Bank 1 has no counted `ret` run at all.** Its longest run of identical `0x22`
bytes is five, so the 149 are a bank-0 fact and the bank asymmetry is part of the
finding rather than a caveat on it. Over bank 0's `0xBF54`-`0xBFDD`, bank 1 holds
**49 distinct byte values and agrees with bank 0 at 6 of 138**; over the 17-byte
run it holds 14 distinct values and agrees at **none**. The far bank is not
holding a shadow of the missing code.

## Who calls them

`call_sites` counts rows of the committed `bank-call-targets.csv` whose
`calls_trampoline` cell is non-empty. **That is a byte-scan upper bound** —
`bank-call-audit.md` §2 calls the framing unsettled in both directions — so the
sentence is *the scan finds* one call site, not *there is* one.

| population | entries | call sites the scan finds |
|---|---:|---|
| inside a counted `ret` run | 149 | 146 with one, 2 with three, 1 with sixteen |
| every other target | 254 | 80 with none, 128 with one, 17 with two, 11 with three, the rest four to twenty-five |

The 80 entries the scan finds **no** caller for are all outside the runs, and
every entry inside a run is reached at least once. Three entries carry more than
one site — `0x1288` with sixteen, `0x12B8` and `0x1408` with three each — so the
runs are not uniformly single-caller and the shape is a tendency, not a rule.

## Answering the three readings

The issue asks for a plain statement of what a target inside a `ret` run is,
naming three candidates. Against the bytes:

- **A live routine the project has lost** predicts a *shared* entry — something
  other callers reach. 146 single-caller thunks are not that. The bank
  comparison above weighs against it too: the far bank holds different code at
  the same addresses rather than a copy of what bank 0 lost. That is a fact
  about this dump, **not** a proof the code was never there, and it is not the
  strongest evidence either way — a second image would be.
- **A stale thunk left by an earlier build** predicts something nothing calls,
  which a linker would have dropped. Every one of the 149 is called, so this does
  not fit either — though whether the *far routine* is live is exactly what is
  not settled.
- **A case label inside one routine** predicts a compiler-emitted jump table,
  which would put an instruction at the target. There is a `ret` there.

So the reading the evidence fits is the fourth one, and it is a narrower one than
the bank-pointer story it replaces: **these are one-instruction far routines.**
The bank switch happens, the far routine immediately returns, and control resumes
in the stub window. Whether the linker emitted 133 identical `ret`s because it
was padding a gap, or because 133 distinct routines each compiled to a bare
return, or because the targets were never distinct to begin with, **this does not
decide** — that is issue #1080's question and re-deciding it is out of scope
here. What this settles is the mechanism the three readings share a wrong
premise about, and it is the premise that decides the rest.

### What would distinguish them

Written down because neither input is committed:

- **A second EC firmware image.** If another dump's bank 0 holds code at
  `0xBF54`-`0xBFDD`, the padding reading is settled. Producing that dump is a
  human at a machine.
- **A `.M51`/map cross-reference or BL51 link listing for this build**, which
  would name the pre-relocation address behind each immediate and say whether
  133 entries were ever distinct symbols. Not obtainable from a hosted runner.

## The `+1` runs, and one naming question answered

Nine runs of consecutive `+1` targets cover 159 entries, and four of them — 17,
62, 4 and 64 entries — name `0xBF1C`-`0xBFD9` one byte at a time. That is a
group-by rather than a column: it is a property of the entry *sequence*, and
`trampoline-relative-branch-sites.md` §"The 170, and where they actually are" set
the precedent in the other direction, so `--self-test` holds the figures and the
CSV supplies the sites.

**Two figures in the issue as filed do not reproduce, and the corrections are
the ones this table carries.** The 147 named targets in that span are 149:
`0xBF93` and `0xBF94` are named by entries `0x14CE` and `0x14C8` and belong to no
`+1` run, because the entries either side of them jump. And the run is
`0xBF54`-`0xBFDD`, **138 bytes**; `0xBF55`-`0xBFD9` is 133 of them, and the run
extends four bytes past `0xBFD9` and one byte below `0xBF55`.

The issue also asks whether a common-area address listed under both banks is the
same routine exported twice. It is, and the answer is readable from committed
files: `ec/decompiled/bank0/031C.asm` and `ec/decompiled/bank1/031C.asm` decode
the same three bytes, `02 d2 36  ljmp 0xd236`, read from the common area at file
`0x031C`. The names differ (`poll_d6c2_then_branch` against
`call_d2a3_then_d274`) but the instructions do not. **No target of the 403 is a
common-area address** — the lowest is `0x8031` — so this names a property of the
export and settles nothing about the block.

## What this does not say

- **No live test, and no EC claim.** Every byte is read off one committed dump.
  No `status:` in `registers.yaml` moves, and no case in either suite asserts
  that any target is or is not code, or that any trampoline is ever called.
- **Not that the calls are dead.** A `lcall` into the middle of a `ret` run is
  possible, and `call_sites` says the scan finds a caller, not that one runs.
- **Not #1080's question.** Whether the run is padding, dead code or a shared
  return is settled there or nowhere; this reports the run's extent, the bank
  asymmetry and the callers, and stops.
- **`in_erased_run` reads `no` throughout, and that is kept as a result.** No
  target sits in a run of 16 `0xFF` bytes, which is
  `bank-call-audit.md` §4's own rule run at the target byte. It is **not found by
  this method**, not "there is no erased flash in these banks" — both banks hold
  erased runs, at addresses this table does not name.
- **The `index.csv` cross-reference is reported, not adjudicated.** Reading
  `index.csv` for a row *at* the target address rather than for a listing that
  *covers* it gives 55 entries with a row in the bank their own stub selects and
  8 whose only row is in the other bank; those 8 are different code at the same
  runtime address, so a row there is not corroboration of the trampoline's
  target. Adjudicating that naming belongs with whoever owns `index.csv`, and it
  is named as a follow-up rather than fixed here. The issue's own count for this
  (54, split 43/11) is not reproduced, and no figure from that file is asserted
  anywhere above — its row count moves on the next export, so repeating one
  would go red for no reason.

## Follow-ups this opens

- **Land the bank-0 `ret` runs in the Ghidra export** so `ghidra-functions.csv`
  can name what a linker called those addresses, if anything. The addresses are
  carried row by row in the committed CSV so that run needs no re-derivation.
- **The 19 entries whose target has a `bank1` row**, three of them inside a
  counted `ret` run (`0xBF93` → `forward_to_bd20_bf93`, `0xBFBB` →
  `FUN_CODE_bfbb`, `0xBFD9` → `zero_04ae_and_04be`). Bank 0 holds `0x22` at all
  three and bank 1 holds named code: the same runtime address, two banks, two
  different routines. That is the shape §4's `own_bank`/`other_bank` columns
  exist for, and no cross-bank claim rests on these rows today.

## Reproducing this

Every figure above comes from one command over committed inputs, or from the
committed CSV beside it:

```console
# the tables in this write-up, and the committed table's derivation
$ python3 ec/tools/trampoline_target_reading.py
$ python3 ec/tools/trampoline_target_reading.py --check
$ python3 ec/tools/trampoline_target_reading.py --write

# the refusals, the planted entries and the threshold's flat band
$ python3 ec/tools/trampoline_target_reading.py --self-test

# the stub's own bytes, which the correction above is read off
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x01100 --runtime 0x1100 -n 10

# the table whose columns this one adds to, and the call sites it joins
$ python3 ec/tools/trampoline_target_census.py --check
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test

# the suite
$ bash tools/run-tests.sh ec/tools
```
