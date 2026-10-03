# `inc dptr` was not tracked, so every store behind one lost its address, and the arms tables attributed a two-byte store to one byte of it

(2026-10-03, issue #242. Static reading and arithmetic over
`ec/firmware/GMxMGxx_11.800`. No capture opened, no EC, no hardware, no
Windows.)

`walk_branch_arms.py`'s `descend()` handled `inc dptr` by crediting the current
DPTR a read and then setting the pointer to unknown, so the `movx` after it
reached no address at all. That is not a rare encoding: it is how this firmware
writes a 16-bit value as two bytes, and it is what the eight `0x8038` handlers
and the `0xB730` pair-store in `0xB716` both do. `descend()` now follows the
increment, and the two committed arms tables name both halves of each pair
where before they named one.

**None of this is a hardware result.** A `write` in these tables is an
instruction storing to an address, not evidence the EC acts on the byte or
that the value is ever anything but the accumulator's. The addresses that
appear below are the machine code read correctly, and `manual-fan-ctrl-0751.md`
§9's negatives — no arm writes a PL register, no arm reaches `0x0F00` — are
unaffected: those are about arms, and the arms of `0x0751` still write no PL
byte. `XDATA_089F` and the slot bytes stay `present-untested`.

## The shape, on the bytes

`0xB730` in bank0, as `manual-fan-ctrl-0751.md` §8a's own listing has it:

```
0xb730  90089e   mov  dptr,#0x089e
0xb733  f0       movx @dptr,a            ; 0
0xb734  a3       inc  dptr               ;   -> 0x089f
0xb735  f0       movx @dptr,a            ; 0
0xb736  22       ret
```

The `inc dptr` at `0xB734` is not a separate access. It is the high byte of
the same 16-bit store, and the machine holds DPTR in DPL at `0x82` and DPH at
`0x83` — so `0x089E` followed by an increment is `0x089F`, with the low byte
carrying into the high one when it is `0xFF`, and `0xFFFF` wrapping to
`0x0000` because DPTR is sixteen bits. Nothing here needs a heuristic; it is
arithmetic on a register the walk already tracks.

The old behaviour gave that store no address, and `0x089F` was reachable only
through a direct `mov dptr,#0x089f` at `0xB6B7` — which is why
`XDATA_089F`'s `static_refs: 1` counts one site while two distinct
instructions write the byte. §8a had to explain the `unattributed` count as a
tool limitation, which was correct about the tool and wrong about the
firmware.

## What changed, and what it is worth

`descend()` credits the byte walked over a read and sets the pointer to
`dp + 1`. Three things about that arithmetic are worth stating rather than
leaving to the code:

- **The carry is not a special case.** DPL is the low byte, so a low byte of
  `0xFF` bumps the high byte, and `(dp + 1) & 0xFFFF` is the whole of it.
- **The wrap is the hardware.** `0xFFFF` increments to `0x0000`, not to an
  address outside the map.
- **A result at or above `CODE_FLOOR` is refused**, and recorded in
  `code_immediates` instead of being charged as an XDATA address. The
  `mov dptr` case records the immediate and *keeps* the pointer, so the two
  deliberately differ, in the safe direction: charging a store to an address
  the map says is not XDATA is the wrong-address failure, and losing a
  possible store is the direction `_dptr_write()` already takes.
  `IncDptrTests::test_the_increment_and_a_mov_dptr_of_the_same_value_disagree`
  pins that difference so neither answer is changed by accident. Neither case
  occurs over the committed tables — no `xdata` cell in either is at or above
  `CODE_FLOOR` — so this is a property of the code and not of a row.

**The addresses that gained a credit**, from the two committed tables, are
below, each with the direction its cell reads. Two shapes are in the list, not
one, and the table records which is which:

| table | addresses newly attributed, by direction |
|---|---|
| `manual-fan-ctrl-0751-arms.csv` | `write`: `0x089F` `0x0A48` `0x0A51` `0x0A53` — `read`: `0x08E7` |
| `bank0-8038-handler-arms.csv` | `write`: `0x08D1` `0x08D3` `0x08D5` `0x08D7` `0x08D9` `0x08DB` `0x08DD` `0x08DF` — `read`: `0x0A57` `0x0A5A` — `r+w`: `0x0A59` |

The `write` cells are the shape the issue named: each is the high byte of a
two-byte store whose low byte was already named. The `read` and `r+w` cells are
the same arithmetic seen from the other side, because **the increment also
credits a read of the successor when the `movx` behind it is a `movx a,@dptr`**.
`0xBC4F` is `mov dptr,#0x08e6 ; movx a,@dptr ; mov r7,a ; inc dptr ; movx
a,@dptr` — it reads `0x08E6` into R7 and `0x08E7` into A, so `0x08E7` gains a
`read` and not a store. `0xB9EA` and `0xBDD2` are the same shape, giving
`0x0A57` and `0x0A5A`. `0x0A59` is credited twice in the same callee `0xB965`,
read behind the increment at `0xB96B` and written elsewhere on the path, which
is why its cell reads `r+w`; `0x0A51` and `0x0A53` are likewise written by the
increment in `0xE389` and read on another path.

The `0x08D1`–`0x08DF` run is one fact about the eight handlers: each seeds a
`0x06xx` slot with `mov dptr,#slot ; movx @dptr,a ; inc dptr ; movx @dptr,a`,
so the low byte of every accumulator pair in the table was named and the high
byte was not. `bank0-8038-handler-flow.md` §6.2 already described them as word
slots written with `r6` at the lower address; the table now agrees with it.

**One modelling choice is visible and unchanged.** The byte the pointer walks
over is credited a *read*, so `0x089E` reads as `r+w` where the machine code
only writes it. That is defensible — the pointer does cross that byte — and it
is why the direction word on those rows is `r+w`. It is not what this issue
is about, so it stands; changing it would move the direction on rows nobody
asked about.

## The remainder, split by cause

An `unattributed` count with no cause is a number a reader has to take on
trust, and the causes are not interchangeable: an inherited pointer is
unknowable *from this row* while a rebuilt one is knowable in principle from
the same bytes. Every unattributed `movx` now records which, in the new
`dp_causes` column and in `Arm.unknown_causes`:

- **`DPTR built at run time`** — a store to DPL or DPH replaced the pointer.
  What the module docstring already documented, and the shape
  `manual-fan-ctrl-0751.md` §6 is eight sites of.
- **`DPTR changed in place`** — `dec dptr`, and `inc`/`dec`/`xch`/`anl`/
  `orl`/`xrl` on DPL or DPH. **Not in the issue and required by it:**
  tracking `inc dptr` keeps DPTR live across more instructions than before, so
  a `dec dptr` between two increments would otherwise be walked with the
  pre-decrement value and a store after it charged to an address the machine
  never touches. That is the wrong-address failure `_dptr_write()`'s own
  docstring rules out, reached by the walk that fixed the other half.
  `trace_xdata_refs.is_dptr_rebuild()` names the same forms as the ones it
  leaves out of *its* terminator set, which is the broader question of whether
  either tool should follow them rather than refuse.
- **`DPTR stepped to a CODE address`** — the increment crossed
  `CODE_FLOOR`. Described above; it occurs on neither committed table.
- **`DPTR never set on this path`** and **`DPTR inherited from the caller`** —
  the walk began with no pointer, and the two are told apart by the caller
  rather than inferred, because `dptr=None` says which applies to nobody.
  A callee row inherits; an arm that never issues a `mov dptr` does not.

`--census` prints the split over whatever a walk reached, and is the mode the
docstring points at instead of restating a total:

```console
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0751 --callee-depth 1 --census
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x1904 0x1906 0x1909 0x190C --callee-depth 1 --census
```

Over both tables the remainder partitions into those causes with nothing left
over, and `callee_row()`'s `partial:` reason now names the cause instead of
always saying "DPTR built at run time" — which for a callee that never builds
one was a claim about the row that was not true. `partial: DPTR inherited
from the caller` is the larger half of what is left on both tables, and it is
the half no reader could previously get anywhere else, because the caller's
pointer is exactly what a callee row does not carry.

`no_claim()` follows: an arm whose stores went unattributed because the
pointer was inherited now says so, instead of asserting a run-time build that
did not happen on it.

## Issue #197 is not closed, and the new credits say so

#197 is the other half: a store after an `lcall` is charged to the pre-call
DPTR, because the callee may have rebuilt it, and `0x8A53` writing `0x09E4`
where the machine writes `0x0460` is the instance of it. **This change does not
close that and does not worsen it.** The pointer is still carried across a call
and still charged, because dropping it would lose real addresses.

What it owes the reader is that such a credit is not presented as one of the
unquestioned ones. `descend()` marks the pointer when it walks past an
`lcall`/`acall` with a live DPTR, a later `mov dptr` clears the mark, and a
store charged while the mark is set puts `DPTR carried across a call` in the
row's `dp_causes` cell. That caveat is not a cause of an unattributed store —
those stores *were* charged — which is why it is the one entry in the cell
that is not part of the census's partition.

## `walk_flow_follow.py` is not affected

It reaches `trace_xdata_refs.classify()`, which already counts `0xA3` as a
span walk rather than a terminator
(`trace_xdata_refs.py`'s `is_dptr_rebuild()` docstring says so and names the
forms it deliberately leaves out). `inc_dptr_sites.py` is the other tool in the
tree that cares about this opcode, and it is independent of both: it derives
the two halves of a pair-accessor call from the decompiled C census and
`trace_xdata_refs.sites_for`, never from `descend()` or the arms tables. The
defect was `walk_branch_arms.descend()`'s alone.

`run_entry_map.py` calls `descend()` directly, so its write sets grew by the
same two-byte-store halves; `scheduler-run-8518-entries.md`'s cells were
re-derived and corrected in place.

## What this does not establish

- **No register gained a status.** `XDATA_089F`, `XDATA_089E` and the eight
  slot bytes stay `present-untested`. An address in an `xdata` cell is this
  tool's reading of the machine code and nothing more; whether the EC acts on
  any of them is open, and `XDATA_089F`'s `static_refs: 1` still counts
  direct `mov dptr` sites rather than writers.
- **No `registers.yaml` rows were added** for the addresses that gained a
  credit (the table above). A static attribution is not evidence a register
  exists; entering them is its own issue.
- **Nothing was read back.** No capture was opened and no hardware was
  observed. Every figure here is arithmetic over a committed image.

## Follow-ups

1. **Issue #197**, restated: the credits that crossed a call are now marked on
   the rows that make them, and the mark is where a fix would show itself.
2. **Whether the in-place DPTR mutations should be tracked** rather than
   dropped to `unattributed`, and whether `trace_xdata_refs.is_dptr_rebuild()`
   should revisit the same question — its docstring already flags that as the
   broader reading.
3. **The `r+w` on the pre-increment byte**, with the concrete consequence:
   `0x089E` and the eight slot low bytes read as `r+w` where the code writes.
4. **Whether a `mov dptr` at or above `CODE_FLOOR` should refuse as the
   increment does.** `IncDptrTests` holds the two answers apart on purpose; it
   is a question about the map, not about `inc dptr`.