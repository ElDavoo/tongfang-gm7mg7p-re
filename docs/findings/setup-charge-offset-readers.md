# Who reads the charge-relevant setup offsets, and what a negative here means

`docs/findings/ifr-charge-and-battery-options.md` asked, for four
charge-relevant offsets and three `UniWillVariable` bytes, whether a read site
exists in the committed BIOS listings. This file is the answer, and the answer
is a scoped negative for all seven — with the method named, the sites it could
not search named, and one positive control that says the method works.

**Nothing here is a live observation.** No ROM was opened, no Ghidra project
was built, no setup variable was read. Every statement is read out of a
committed listing by `bios/tools/setup_offset_xrefs.py`, and no sentence below
claims or implies that writing any of these offsets changes charging on this
machine. That needs issue #86's charge trace at the physical machine.

## The answer

| Offset | IFR prompt | Reader found? | What this method could not search |
|---|---|---|---|
| `Setup[0x4F3]` | `Charging Method`, Normal/Fast | **not found by this method** | every `Setup`-named site whose GUID this listing does not carry — four different reasons, broken down under *The wide blind spot* — plus `Setup`'s wrapper path |
| `Setup[0x3D2]` | `Charger participant` | **not found by this method** | as above |
| `Setup[0x65D]` | `Battery Participant` | **not found by this method** | as above |
| `CpuSetup[0xC3]` | `AC Brick Capacity` | **not found by this method** | as above |
| `UniWillVariable[0x30]` | `BatteryLimitation` | **not found by this method** | as above, and no `UniWillVariable` site had its GUID in the listing at all |
| `UniWillVariable[0x31]` | `ChargeMaximumLimit` | **not found by this method** | as above |
| `UniWillVariable[0x32]` | `ChargeMinimumLimit` | **not found by this method** | as above |

`python3 bios/tools/setup_offset_xrefs.py` prints that table, and
`python3 bios/tools/setup_offset_xrefs.py --verbose` prints the per-module
breakdown of what it could not place. The rows above are the tool's output,
not a reading of it.

**What the negative is worth.** It is not "these offsets have no reader." It
is "no reader exists among the `GetVariable` sites whose GUID this method can
read from a code listing" — and that is a small share of the sites, for the
reasons under *The wide blind spot* below. On the tree this was measured
against, fewer than one site in ten was searched; `--list-skip-causes` prints
the total and the split, and it is the number to read before believing any row
above. §8's `Setup[0x7D7]` write is recovered by the same arithmetic, which
is what makes the negative credible rather than merely quiet.

## Why a grep is the wrong tool, stated as a measurement

A search for `0x4F3` over `bios/decompiled/*.c` turns up no `Setup[0x4F3]`
literal: the only matches are substrings of longer constants, such as
`local_14 = 0x4f3c34b8` in `OemHddHeadParkSmm.c`. That is §4c's blind spot
rather than an answer. A setup offset does not reach code as a literal. `gRT->GetVariable` is called with a **stack buffer**, and every later
access to the byte is a displacement against that buffer's base.

In `bios/ghidra/listings/OemOcDxe/000007A8.asm` the `Setup` buffer base is
`[RBP + 0x2e0]` — set up at `00000883` and passed as the fifth argument at
`0000088A` — and the store §8 publishes as `Setup[0x7D7]` is at `000008B6`:

```
000008B6 88 85 b7 0a 00 00 - - - - -      mov      byte ptr [RBP + 0xab7], AL
```

`0x2e0 + 0x7d7 = 0xab7`. The offset is recoverable, and it is recoverable
from the **listing** rather than the C — which is what the listing header
itself says ("where the two disagree, this file is right and the C is a
reading of it") and what makes the arithmetic checkable by a reader.

## The method

Three things make a `gRT->GetVariable` site recoverable, and all three sit in
the listing a few instructions above the call:

- **Which variable.** The GUID is built in the frame as four dword stores at
  `RDX`'s target. `EFI_GUID` is mixed-endian, so `Setup`'s
  `EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9` reads as the immediates
  `0xec87d643, 0x4bb5eba4, 0x3e3fe5a1, 0xa90db236` — which is what
  `OemOcDxe`'s `00000832`–`0000084A` store. `CpuSetup`'s
  `B08F97FF-E6E8-4193-A997-5E9E9B0ADB32` appears the same way at
  `00000812`–`0000082A`.
- **How big.** `R9` points at a frame slot holding the byte count. That bounds
  which offsets are in range, and doubles as a check on the base: an offset
  recovered against the wrong base usually falls outside the size. A site with
  no recoverable size places **nothing**, because without a bound the whole
  frame is "inside the buffer" and the tool would claim readers it does not
  have.
- **Where.** The data buffer is the fifth argument, `[RSP + 0x20]`. Both base
  forms occur and both are handled: `RBP`-relative, as in
  `OemOcDxe/000007A8.asm`, and `RSP`-relative, as in
  `OemPowerModeDxe/00000494.asm`.

The tool then reads every memory operand in that function and subtracts the
base. A `mov`/`movzx` destination is a write; a source is a read; and `cmp` is
a read even though its operand sits in the destination position, which is the
commonest shape a setup byte is read in.

## The positive control, and why it is the load-bearing part

`docs/findings.md` §8 already publishes that `OemOcDxe`'s `SyncOcVariables`
writes `Setup[0x7D7]`. The tool re-derives that from the arithmetic rather
than from a fixture written to match:

```
$ python3 bios/tools/setup_offset_xrefs.py --check
  setup-offset-xrefs: Setup[0x7D7] resolves to OemOcDxe SyncOcVariables;
  variable table matches the committed IFR dump
```

`--check` is that, as a gate over committed text — it needs no ROM, no Ghidra
project and no network. `bios/tools/test_setup_offset_xrefs.py` adds the
shapes the committed tree cannot supply a second answer for: the
`RBP`-relative base, the register-indirect copy, the missing size, and the two
stores that share a GUID.

## The wide blind spot, and it is the one that bounds this answer

**A skipped site is not one thing, so the count is not given one cause.** The
recovery above needs the GUID built on the stack. The largest single shape is
instead

```
00000872 48 8d 15 a7 0c 00 00 - - - -     lea      RDX, [0x1520]
```

— a pointer into the module's `.data`. A **code** listing carries
instructions, not the contents of `.data`, so this tool cannot read those
bytes. It skips the site whole and counts it.

`python3 bios/tools/setup_offset_xrefs.py --list-skip-causes` prints the split
by what `RDX` actually points at, and it is worth reading rather than assuming:

| What `RDX` points at | What would recover it |
|---|---|
| a static address in `.data` | the module image, and nothing else |
| a frame slot holding a **pointer** | the *caller's* listing — the GUID is not in this one |
| computed or copied through a register | cross-function reach, or arithmetic this method does not model |
| no `RDX` definition in the function | code the listing does not show |

Only the first row is a matter of committing a file, and it is roughly half of
the skipped population — **not all of it**, which is why the count is printed
without a cause attached rather than under this row's name. The second row is
the one most worth not mistaking: it *looks* like a frame case the method
already handles, and it is not one. `Setup`'s wrapper hands a GUID pointer
down through a frame slot, so those sites are the cross-function case wearing
the costume of a case this tool can read.

`python3 bios/tools/setup_offset_xrefs.py --offset Setup:0x4F3 --verbose`
prints the per-module breakdown. Every query prints the total, because **a
negative from this tool is bounded by the number of sites it skipped, and that
number is the first thing to check before believing one.**

## Two smaller blind spots, counted

- **An access through a register the tool has lost track of.** Provenance
  closes the common case — a `mov` of the buffer pointer into `RBX`, reached
  afterwards as `[RBX + off]`, is followed — but a register that is
  reassigned from arithmetic the tool does not model is lost. Such accesses are
  counted per module and printed by `--verbose`.
- **An indexed operand**, `[R8 + RCX*0x1]` and its relatives. The address is
  computed at runtime, so no displacement can be subtracted. Counted in the
  same bucket, and deliberately not guessed at.

## Cross-function reach: `Setup`'s wrapper, and why it is the awkward one

`Setup` does not reach `gRT` directly for most of its variable traffic. It goes
through the module's own variable wrapper — `append_wide_component_and_parse`
at `0001EA50`, named in `bios/annotations/ghidra-functions.csv` — and that
wrapper calls through a **protocol** (`call qword ptr [RAX + 0x140]`, twice)
rather than through `gRT`'s table.

That has two consequences, and both bound this answer:

1. **The offsets `Setup` writes on Save are the form engine's own store**, not
   a charge-path consumer. `Setup` is the HII form engine; it writes a
   question's value on Save by construction. A "reader" found inside it would
   be that generic path. The tool marks this rather than leaving it to a note
   a reader may not reach — every `Setup` negative prints the scoping line.
2. **The access may not be in the same listing as the read.** When the wrapper
   fills a buffer and hands the pointer back, the displacement lives in a
   different function from the call. This tool reads one function at a time and
   cannot see it. The shape is not hypothetical: `Setup`'s
   `update_ec_82_from_setup_byte_7cd` is annotated in
   `bios/annotations/ghidra-functions.csv` as reading `Setup[0x7CD]` and
   rewriting EC RAM `0x82` from it, and its access at `00007CDC` is
   `[RAX + 0x7cd]` against a pointer the wrapper returned — a register-indirect
   base this method does not resolve.

So a reader of this table should treat the `Setup` rows as the weakest of the
four stores, for a reason that has nothing to do with `Setup[0x4F3]` and
everything to do with how `Setup` is built.

## What the same method does place, which is the cross-check

The tool's positives are the useful part: they say the arithmetic works on
offsets it was not aimed at, and they are where the next question should start.
`python3 bios/tools/setup_offset_xrefs.py --list-offsets Setup` prints them
per site.

`OemOcDxe`'s `SyncOcVariables` places one `Setup` offset — the `0x7D7` of §8 —
and three `CpuSetup` ones, at `0x1BD`, `0x1BF` and `0x1C0`. `OemKbLightDxe`
places four `Setup` writes in the frame below §8's, at `0x7D2`, `0x7D4`,
`0x7D5` and `0x7D6`. `OemNetworkDxe`'s
`read_modify_write_two_variables` places `Setup[0x742]` as a **read**, which is
the same neighbourhood as the `Setup[0x741]` question
`ifr-charge-and-battery-options.md` asks about elsewhere. None of these is a
charge offset; they are here because a method that found only the answer it
was aimed at would be worth nothing.

One site is recovered and deliberately **not** attributed:
`OemNetworkDxe`'s `read_modify_write_two_variables` reads an eight-byte
variable under `D1405D16-7AFC-4695-BB12-41459D3695A2`, which is not a store
this tool has an entry for. It is reported with its GUID rather than dropped,
so a variable missing from the tool's table shows up instead of reading as a
failed decode.

**No annotation row was added, and that is a decision rather than an
omission.** `OemKbLightDxe`'s `FUN_00000658` is the clearest new reader here —
it writes four `Setup` bytes, at `0x7D2`, `0x7D4`, `0x7D5` and `0x7D6`, in the
frame below §8's — so the natural next step is a row in
`bios/annotations/ghidra-functions.csv` naming the offsets, as
`bios/ghidra/README.md` describes. Adding one means also bumping the record
count that `bios_extract.py --check` holds the annotations file to, and that
count is a figure of the repository's own text: every branch that annotates
anything has to edit the same line, which is the collision CLAUDE.md's "no
totals" rule exists to prevent. One reader's worth of annotation is not worth
opening that. The row belongs with a change to that gate, which is a separate
piece of work and a human's call.

## How to extend this

`bios/ghidra/modules/` holds TE module bodies. Those are the precedent for
committing a module image, and they are what a follow-up that closes the
`.data` row of the skip breakdown would extend. With the PE32 bodies readable,
`--check` would hold the tool's `VARIABLES` table to the GUIDs actually in the
firmware rather than to the IFR dump alone.

**Committing the images is worth the most, but it is not most of it, and the
rest is not reachable by any cheaper tool-side change.** The obvious cheap win
would be to place offsets at sites whose GUID is missing but whose size and
base are both recovered, on the strength of the size alone. Measured over this
tree, that is 30 sites — and it would report them under the weakest evidence
the tool has, since several stores share these sizes. The `.data` row is
larger than that, and no amount of additional frame modelling reaches it,
because the bytes are simply not in a listing. The images are the biggest
single lever *and* the only one that reaches the largest bucket of it.

## What this does not settle

- **Whether writing any of these offsets changes charging on this board.**
  Issue #86's charge trace, at the physical machine. Nothing above implies it,
  and no reader of this file should infer it from the negatives.
- **The statics.** One row of the skip breakdown needs the PE32 module images,
  which are not committed. The other three rows need cross-function reach and
  no new committed input.
- **The wrapper path.** Following a pointer the form engine's wrapper returned
  needs cross-function dataflow rather than per-function recovery.
- **`SetupVolatileData`.** It shares `Setup`'s GUID and is told apart only by
  its 0x97-byte size, so the tool will not file a site under it on a GUID
  match alone. No site on this tree recovered both, so it has no rows. That is
  a statement about what was recovered, not about the store.

## New questions this opens

- **Can the PE32 module images be committed, so the static GUIDs become
  readable?** This is the largest single improvement available to this table,
  and the only one that reaches the largest part of the skipped population —
  the rows of the skip breakdown above say how much each would buy, and they
  do not all need the same thing. The TE bodies in
  `bios/ghidra/modules/` are the existing precedent for committing an image.
- **Do the sites whose `RDX` is a frame slot pointing at a caller's GUID share
  one wrapper?** That shape is `Setup`'s own wrapper handing a variable pointer
  down, and it is the cross-function case rather than the frame case this tool
  already handles. Following it means cross-function dataflow, which is the
  same question as the wrapper-path question below and probably the same piece
  of work.
- **What reads `Setup[0x741]`?** `OemNetworkDxe` places a read at `0x742` in
  the same store. Whether `0x741` and `0x742` are read together, and what the
  pair feeds, is a question this method can now answer exactly.
- **Does anything read `UniWillVariable[0x30]`–`0x32` outside the BIOS?** The
  BIOS half is now a scoped negative. `evidence/uefi/` carries committed dumps
  of the variable's post-BootServices contents; whether the offsets are ever
  non-zero after boot is a question about those dumps, not about listings.
