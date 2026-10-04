# The BIOS's EC index/data writes, and what `0x07A6` is not among them

**Everything here is static.** No laptop was opened, no EC register was read
back, no setup variable was written, and no BIOS load-defaults was performed.
Every claim below is a reading of the committed listings under
`bios/ghidra/listings/`, re-derivable offline with one command.

The negative this file records is **not found by this census over these
listings and these call sites**. It is not "the BIOS does not write
`0x07A6`", for the reason §1 is about: on this channel an address is a *pair*
of bytes, so the question "does the BIOS reference `0x07A6`" has no answer to
give until someone asks about the pair. §5 gives the pair census, §6 the
verdict, and §7 the two boundaries the negative stops at — the rows the census
could not read, and an encoding of the same channel it does not read at all.

## 1. The channel, and why the literal patterns could never match it

The EC is reached over the ACPI EC port pair — command/status `0x66`, data
`0x62` — with four command bytes. [`bios/annotations/ghidra-functions.csv`](../../bios/annotations/ghidra-functions.csv)
row `OemOcDxe,0xF38` (`EcWriteCommandData`) already records what each does,
and this file takes that row as given rather than re-deriving it:

| command | carries | effect |
|---|---|---|
| `0xA3` | the high byte | selects the high half of an EC RAM address |
| `0xA2` | the low byte | selects the low half |
| `0xA4` | — | read the byte at the selected address |
| `0xA5` | a value byte | write that value at the selected address |

So an access is `0xA3 <hi>` then `0xA2 <lo>`, then `0xA4` or `0xA5 <val>`, and
the address it reaches is `<hi><lo>`. `Setup 0x1BA3C` is exactly that with the
base fixed at `0x07`:

```
0001BA4B mov  DIL, R8B          ; the caller's index byte, kept aside
0001BA4E mov  DL, 0xa3
0001BA50 mov  R8B, 0x7          ; high byte 0x07
0001BA53 mov  CL, 0x62          ; the 0x62/0x66 port pair
0001BA58 call 0x0001b8d8
0001BA64 mov  R8B, DIL          ; low byte, whatever the caller passed
0001BA67 mov  DL, 0xa2
0001BA6B call 0x0001b8d8
0001BA75 mov  R8B, SIL          ; the value byte
0001BA78 mov  DL, 0xa5
0001BA7C call 0x0001b8d8
```

**That is one encoding of the channel, and the census reads only that one.**
The committed listings reach `0x62`/`0x66` a second way as well — by loading
the port into `EDX` and issuing `out DX, AL` inline, with the byte coming from
a register rather than from a `mov DL, <command>` literal. §7 names where that
stands alone and says what is and is not known about it.

**That is the whole reason a literal scan misses.** A write to `0x07A6` over
this channel carries `0xA6` against a `0x07` base. The strings `7A6`, `0x7A6`,
`1958` and `0xFE4107A6` are all a *joined* address, and nothing here ever joins
one. `docs/findings/oem4-bit-map-and-bit0.md` §6 searched exactly those, so
its BIOS negative was scoped to a channel on which the address is never
spelled; §6 of that file now says so.

The one place the two readings can be checked against each other is
`OemOcPei 0xFFF827F3`, which is **named** `ec_read_reg_0741` in its own
listing header. `bios/tools/ec_io_census.py` derives `(0x07, 0x41)` for it
from the instructions alone, with the name nowhere in the derivation. That is
not proof the whole scheme is right, but it is one address where an
independent reading and a committed name agree.

## 2. Two ABIs, and the one that is easy to miss

The value byte is not beside the port byte; it is in a register or on the
stack. Both modules that use the 32-bit TE ABI (`OemOcPei`, `OemHooksPei`)
push it:

```
FFF827BE push 0x7               ; high byte
FFF827C0 mov  DL, 0xa3
FFF827C2 mov  CL, 0x62
FFF827C4 call 0xfff8277f
FFF827CE push 0x41              ; low byte
FFF827D0 mov  DL, 0xa2
FFF827D4 call 0xfff8277f
```

A census that reads only `mov R8B, <imm>` beside `mov DL, <port>` covers the
x64 modules and misses both PEI modules silently — the `push 0x41` is nowhere
near a `mov`. The tool replays the pushes and pops of the window and reads
what the `call` finds on top of the stack, which is also what makes
`OemOcPei 0xFFF827F3` come out right: it pushes `0x7`, pushes `0x62` and pops
that straight back into `EBX`, so the command carries the byte underneath.

## 3. The register-passed form, and why call sites are load-bearing

In most modules the low byte and the value byte are the *function's own
arguments*, aliased in at entry. `OemHooks ec_write_reg_byte` (`0x9B8`), with
the `mov CL, 0x62` port-base lines and the status checks between calls elided:

```
000009C2 mov  DIL, R8B          ; value byte   (argument)
000009C5 mov  BL, DL            ; index byte   (argument)
000009C7 mov  R8B, 0x4          ; high byte 0x04 -- a literal, here
000009CA mov  DL, 0xa3
              mov  CL, 0x62
000009CE call 0x000008f0
              …  test RAX, RAX / js  …
000009D8 mov  R8B, BL
000009DB mov  DL, 0xa2
              mov  CL, 0x62
000009DF call 0x000008f0
              …  test RAX, RAX / js  …
000009E9 mov  R8B, DIL
000009EC mov  DL, 0xa5
              mov  CL, 0x62
000009F0 call 0x000008f0
```

The `0xA6` a reader is looking for would live at a **call site**, as the
argument a caller loads — not inside the helper. So the census resolves each
argument at every call site of the function in the committed listings, and
emits one row per call site that carries a literal, because the same function
reaches a different EC address from each of them.

Two rules keep that resolution honest, and both are the difference between a
row and a guess:

- **A register written twice in one window is not one byte.** `Setup 0x1A5C`
  sets `DL` to `0x10`, to `0xA0` or from a stack slot and passes whichever it
  reached. Reading the last `mov` backwards would report `0xA0` for all three,
  so the tool reports the register instead. Two writes that *agree* are not a
  conflict and do resolve — `OemKbLightDxe 0x5A4` sets `R8B` to `0x66` on both
  arms of a branch and passes `0x66`.
- **A window is bounded by the `call`s on either side**, because that is where
  a register stops being this function's to read. It is why the ubiquitous
  `test RAX, RAX` / `js` status guard between two calls costs nothing: it
  writes nothing, and a rule keyed on branches rather than on writes would
  throw away almost every byte in the tree.

## 4. The base is not always `0x07`

"Indexed by `0xA6`" means nothing without the base, and the modules do not
agree on one. There are two cases, and the second is why `--module` is worth
running rather than a partition of modules into "the `0x04` ones" and "the
`0x07` ones":

- **The base is a literal in the function.** `Setup 0x1B9A0` (`mov R8B, 0x4` at
  `0x1B9B5`), `OemHooks 0x9B8`/`0xA00` (`0x9C7`, `0xA15`) and `OemTurboModeDxe
  0x494` (`0x4AA`) write `0x04` and nothing else, so every row of theirs
  carries it. `OemSWBoardIDDxe 0x438` writes the same literal (`0x4C5`,
  `0x52A`) — its first row is the one §7 is about, for a reason inside its own
  window rather than about the base.
- **The base is an argument, so the caller's to choose.** `OemPowerModeDxe
  0x89C`, `OemServiceDxe 0xF58`/`0xFB8` and `OemGlobalNvsDxe 0xCC4` each alias
  `DL` in at entry (`mov R8B, DL` at `0x8B0`, `0xF6C`/`0xFCC`, `0xCD8`), and
  the committed table reaches each of them with `0x04` **and** with `0x07` from
  different call sites.

`--module <name>` prints the rows either way, and that is the check to run
before repeating a base for a module. Under `0x04`, index `0xA6` addresses
`0x04A6`, a different register — so the census keys every verdict on the pair,
and the base column is one of the two things the answer turns on.

## 5. The table, and what it holds

[`bios/annotations/ec-io-writes.csv`](../../bios/annotations/ec-io-writes.csv)
is generated from the committed listings, so `--check` re-derives it and fails
on any difference; a hand-edited table cannot survive.

```sh
python3 bios/tools/ec_io_census.py            # the census, printed
python3 bios/tools/ec_io_census.py --addr 0x07A6
python3 bios/tools/ec_io_census.py --unresolved
python3 bios/tools/ec_io_census.py --check    # the committed CSV is current
```

A row is one **access sequence** — the `0xA3`/`0xA2` run with the `0xA4` or
`0xA5` that terminates it — because the base and the index mean nothing apart
and a row per command byte would put them in different rows. Columns: the
module and the function the sequence is in, the address of the `0xA3`, the
port helper it calls, the ABI, `base` / `index` / `data`, `direction`, the
`caller` a caller-supplied byte was resolved at, and `resolved`.

`resolved` says **which column** the tool could not read, as `no:data:BL` or
`no:index:DL`, and the row leaves that column empty. That distinction is the
point of the column: the question this table answers is whether a *pair*
appears, and that turns on `base` and `index` alone, so a row whose only
unreadable byte is the value written is not a row whose address is in doubt.

The EC RAM addresses the BIOS reaches over this channel, from the base and
index columns of the committed table:

```
0442 0458 0462 049F 073C 073D 0740 0741 0748 0749 074A 074B 074C 074E
0750 0751 0756 0765 0766 076C 076D 076E 0782 078C 07A3 07A4
```

These are over every module with such a run in the committed listings, both
ABIs. A few are already named elsewhere in the tree; the rest are not, and
**this file does not claim to know what any of these bytes is for**, only which
pair the BIOS sends a byte to.

- `0x0741` is the register the `OemOcDxe,0xF38` annotation row records, and
  `ec/annotations/subsystems.md` §9 discusses.
- `0x0740` is the byte `OemUniWillVariableDxe 0x84C` reads — with that row's own
  caveat, which this file carries rather than drops: the `+0x700` base between
  the low byte sent and the EC map "is not visible in this listing", so the
  `PROJECT_ID` reading is the annotation's inference, not a confirmed address.
- `0x0748`-`0x074B` are the lightbar registers `subsystems.md` §8 records
  having been written live on this chassis.
- `0x0750` is written from `OemHooks` and `OemHooksPei`, `0x0751` from
  `OemPowerModeDxe` and `Setup`. That is what the table shows and no more.

## 6. The verdict

**Not found by this census: no row carries `(0x07, 0xA6)`, and no row carries
`(0x04, 0xA6)` either.**

That is the whole claim. It is a statement about the `ec-io` runs in the
committed listings and about the call sites of the functions that take their
bytes as arguments — not about the BIOS's behaviour, and not about the
`0xFE41xxxx` memory window, which this census does not read at all and which
is a separate survey.

It is also not the last word, for three reasons worth keeping separate:

- **The channel has a second encoding the tool's site pattern does not match.**
  `OemI2cDevices` reaches the same `0x66`/`0x62` pair by `out DX, AL` rather
  than by a `mov DL, <command>` literal and a helper call, so no row names it
  at all. §7 has this as its second boundary; it is the one most likely to
  hide a write, because the byte there is a caller's argument.
- **One `0xA6` in the tree is a displacement, not a command byte.**
  `Setup 0xD400` contains `test word ptr [RBX + 0xa6], AX`. A scan for the
  byte finds it and it means nothing; the tool's site pattern is
  `mov DL, <command>`, and the suite holds the memory-operand case so the
  distinction cannot be lost later.
- **The base is a real part of the answer**, so a negative over `0x07` alone
  would be the narrower claim. It is stated over both bases the modules select
  for that reason.

## 7. Where the negative stops

Two boundaries, and they are not the same kind of thing. The first is the rows
the tool read but could not resolve; the second is a shape of code the tool
does not read at all.

### The rows the tool could not read

Each of these is in the table with that column empty and the register named,
and they are listed here rather than left for a reader to discover:

| module | function | why |
|---|---|---|
| `Setup` | `0x1B9A0` | the index is its `DL` argument and **no listing in the committed tree calls it**, so nothing settles the byte. Its base is `0x04`, which is what leaves `0x04A6` open. |
| `OemGlobalNvsDxe` | `0xCC4` | the base is its `DL` argument; at the call from `0x741` the caller's window writes `DL` twice (`0x725` from memory, `0x73F` to `0x07`), so the byte is path-dependent. |
| `OemServiceDxe` | `0xF58` | same argument, and the caller at `0xD20` writes `DL` three ways in its window. |
| `OemSWBoardIDDxe` | `0x438` | `R8B` — the base — is written twice between the function's entry and the `0xA3` at `0x4C8`, `0x2` at `0x497` and `0x4` at `0x4C5`, and the two disagree. There is no `call` in that span, so the whole entry-to-`0xA3` range is one window and §3's two-writes rule is what leaves the column empty — not a branch, and not a register name the tool could not follow. |

That last row is worth reading a step further, because the reason it is empty
is narrower than it looks. No branch targets `0x4C5` or `0x4C8`, and the `jz` at
`0x4BF` leaves forward to `0x56B`, so the only path to the `0xA3` is the
fall-through — and the last write on it is `mov R8B, 0x4` at `0x4C5`. The byte
that `0xA3` sends is therefore `0x04`, and filling the column in would yield
`(0x04, 0x9f)`, which §5's address list already carries. So this row is the
tool declining a window it cannot prove single-valued, not an address in
doubt, and §6's verdict is the same either way. The tool does not fill it in
because a rule that special-cased this window is the rule §3 exists to avoid.

Rows whose only unreadable byte is the *value* written are not in this table;
`--unresolved` prints them, and §5's `resolved` column is what separates the
two.

### The encoding the tool does not read at all

The rows above are unresolved: the tool found the access and named the byte it
could not follow. What follows is not in the table at all, and that is a
different claim. The tool's site pattern is `mov DL, <command>` followed by a
helper call, so a function that reaches the same two ports by loading `EDX`
with the port and issuing `out DX, AL` produces **no row naming it** — not an
unresolved row, no row. `OemI2cDevices` is written entirely in that shape: it
contains no `0xA3`, `0xA2`, `0xA4` or `0xA5` literal anywhere, so the whole
module is invisible to the census, and `rows()` returns nothing for it.

Two functions there do the writing, and both annotation rows already record the
mechanism:

- `write_port_66_wait_d1_clear` (`0x5CC`) writes its second argument's low byte
  to `0x66`: `mov EDX, 0x66` at `0x618`, `mov AL, DIL` at `0x61D`, `out DX, AL`
  at `0x620`, with `DIL` aliased from `DL` at entry.
- `write_port_62_between_d1_polls` (`0x6DC`) writes its second argument to
  `0x66` through the `0x5CC` call and its third to `0x62` inline: `mov EDX,
  0x62` at `0x745`, `mov AL, SIL` at `0x74A`, `out DX, AL` at `0x74D`, with
  `SIL` aliased from `R8B` at entry.

What is known, and what is not: the bytes these two send are the **function
arguments**, so they are the caller's to choose and the committed tree does not
settle them. `0x5CC` has exactly one caller in the listings — `0x6DC` at
`0x70D` — and `0x6DC` has none, so nothing resolves either byte. **A byte
supplied by a caller's argument is exactly what this census cannot read**, and
that is where a `(0x07, 0xA6)` write would most plausibly hide if one exists in
this encoding rather than the one §5 tabulates. Whether the pair either reaches
is a question this file does not answer, and nothing here should be read as
saying it cannot.

So §6's negative is bounded by the rows the tool could not read **and** by this
encoding, which the tool does not cross at all. The second boundary is wider
than the first, and it is stated here rather than left implicit in the tool's
site pattern.

## 8. The load-defaults path, and the part that cannot be followed by name

The issue asked which of these writes a load-defaults issues, and on what
event. **There is no `LoadDefault` symbol anywhere in `bios/decompiled/`**, so
the path cannot be followed by that name: EDK2's load-defaults is
variable-service machinery, and it does not appear under a name in these
modules. Following it would need a live trace at the machine, which this
pipeline cannot produce and which is named as a human's step rather than
implied here.

What *is* readable is the shape such a path takes, and one instance of it is
already annotated: `Setup 0x7C50` `update_ec_82_from_setup_byte_7cd` reads a
Setup variable through `0x1EA50`, reads EC RAM `0x82` through `0x1BA9C`,
rewrites the byte from a Setup byte, writes EC `0x82` back through `0x1BA3C`,
and writes the variable back through `0x1EBD4`. The census resolves that
middle write to the pair `(0x07, 0x82)`, attributed to the call at
`Setup 0x00007CFB`:

```sh
python3 bios/tools/ec_io_census.py --addr 0x0782
```

So a Setup-variable-driven EC write to `0x07A6`, were one to exist, would
surface in this table the same way — as a `(0x07, 0xA6)` row with a
Setup-driven call site. None does. **Whether that would fire on the
load-defaults event specifically is a question for a live run**, and this file
does not answer it.

## 9. Two citations this file does not repeat

Both were checked against the tree rather than carried over, and neither
source file needs changing for it:

- **`Setup 0x1BA03` and `0x1BAFF` name no function.** The EC-writing helpers
  in `Setup` are `0x1B9A0`, `0x1BA3C` and `0x1BA9C`; `0x1BA03` is an
  instruction *inside* `0x1B9A0` (`mov EDX, 0x66`).
- **`ec/annotations/subsystems.md`'s index/data passage is at its §9 heading**,
  not at a line range. The content there is right and is left alone: it
  already records the `0xA3`/`0xA2` mapping and the `ec-io` type, and it is
  this census that makes those rows enumerable as addresses.

## What this does not establish

- **What any of these bytes means.** The table says which pair the BIOS sends
  a byte to; it does not say what the EC does with it, and a write being in
  the table is not a write being confirmed to take effect.
- **Anything about the `0xFE41xxxx` window**, which this census does not read.
- **Whether bit 0 of `0x07A6` is cleared on a load-defaults.** That question
  is unchanged by this file; §7 of `docs/findings/oem4-bit-map-and-bit0.md`
  still leaves it open, and closing it needs a trace at the machine.
