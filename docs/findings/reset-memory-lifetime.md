# What the EC's reset path leaves in memory (issue #587)

The issue asked for the reset path's memory footprint as a table cross-referenced
against `ec/annotations/registers.yaml`, on the reasoning that a register the EC
wipes on every reset cannot carry a value across a suspend/resume, and that
nothing in the tree says which is which for any given byte. **That reasoning
holds and the table now exists** — `ec/annotations/register-boot-lifetime.csv`,
one row per named register, `boot_verdict` in
`cleared`/`spared`/`not-reached`.

Two of the issue's premises about the tree were wrong, and both corrections
change what this change is: the XDATA half it asked for was already measured and
committed, and the "no tool surveys direct-byte operands" gap is a **method** gap
rather than a missing row. The issue's wording is left visible beside each
correction rather than dropped, per CLAUDE.md's calibration rule.

> **Calibration, before anything else.** Every figure below is a static
> execution or byte scan of `ec/firmware/GMxMGxx_11.800`. **No EC was powered
> and no register or internal-RAM byte was read back.** The claim is *the reset
> path does this to these bytes*, not *these bytes behave this way*: whether
> anything re-clears them after boot, and whether the `0x07FD`-`0x07FF` window
> is load-bearing or incidental, are named as open at the end and both need the
> physical machine.

## Correction 1: the XDATA census already exists

The issue asked for a new XDATA table. `ec/tools/boot_xdata_sites.py` already
executes the reset path with 8051 semantics and writes
`ec/annotations/boot-xdata-sites.csv`, whose `boot_verdict` column already
carries `cleared` / `written` / `written-unknown` / `spared` / `not-reached` for
every address the walk touched, and whose `--check` holds that table byte for
byte. All three XDATA ranges the issue listed are already rows there, and
[`charge-derating-counters-not-persisted.md`](charge-derating-counters-not-persisted.md)
(issue #90) has already applied a verdict to individual registers.

So the real gap was the **join**: `boot-xdata-sites.csv` is keyed by address and
`registers.yaml` is keyed by entry, and nothing connected them, so "does the
reset path clear this register" was a question a reader had to answer by hand,
one register at a time, out of a table that is not indexed by register. That
join is `ec/tools/register_boot_lifetime.py`, and it is the only new XDATA-side
thing here.

## Correction 2: the direct-byte tool exists; the `@Ri` method did not

The issue said "there is no tool that surveys direct-byte operands" for internal
RAM `0x20`-`0xBF`. **`ec/tools/intmem_refs.py` is that tool** — and its output
confirms it:

```console
$ python3 ec/tools/intmem_refs.py ec/firmware/GMxMGxx_11.800 0x84
... the caveat block the tool prints first, quoted in its own docstring ...
0x84  refs=0   ec=0   pd=0   in_data_region=0  NOT FOUND BY THIS METHOD (see the caveat above)
```

`0xAA` is not a clean zero, which is why it is worth stating separately: it
returns three unrelated `clr 0xaa` sites in `bank0` and a run of `inc`/`dec 0xaa`
pairs in the ITE8850-PD image — a separate 8051 program with its own memory map,
so none of them is an EC reference to byte `0xAA`. The `chan_init_*` write the
issue names does not appear among them, because it is not a direct operand.

The issue's *conclusion* still holds, for a reason it did not give.
`intmem_refs.OPCODE_TABLE` covers the **direct-addressing** forms only, and the
internal-RAM operands of the boot path's own IRAM loop are not direct-addressed
at all. `ec/decompiled/common/0F75.asm`:

```
0F8D     c8 - -   xch      A, R0
0F8E     ef - -   mov      A, R7
0F8F     c8 - -   xch      A, R0
0F90     e4 - -   clr      A
0F91     f6 - -   mov      @R0, A
```

The address is in a register. Recovering it needs the two-instruction pairing
followed **across a register** — `mov Rn,#imm` immediately followed by an `@Ri`
instruction naming the same register — which is a different method, not a missing
row. `ec/tools/iram_boot_sites.py` adds that form beside the delegated direct
one. The three `chan_init_*` writes the issue names are recovered by it, and by
nothing in the direct table:

```console
$ python3 ec/tools/iram_boot_sites.py ec/firmware/GMxMGxx_11.800 0x84
... the caveat block the tool prints first, quoted in its own docstring ...
0x84  refs=7   ec=7
    file 0x00164  common   runtime 0x0164   ri            write mov r0,#0x84 ; mov  @R0,#0x02  frame=24/0 in_data_region=not listed
    file 0x001C1  common   runtime 0x01C1   ri            write mov r0,#0x84 ; mov  @R0,#0x01  frame=24/0 in_data_region=not listed
    file 0x002DC  common   runtime 0x02DC   ri            write mov r0,#0x84 ; mov  @R0,A      frame=24/0 in_data_region=not listed
    file 0x0309B  common   runtime 0x309B   ri            read  mov r0,#0x84 ; mov  A,@R0      frame=24/0 in_data_region=not listed
    file 0x039BF  common   runtime 0x39BF   ri            write mov r0,#0x84 ; mov  @R0,#0xff  frame=24/0 in_data_region=not listed
    file 0x039EA  common   runtime 0x39EA   ri            read  mov r0,#0x84 ; mov  A,@R0      frame=24/0 in_data_region=not listed
    file 0x03A33  common   runtime 0x3A33   ri            write mov r0,#0x84 ; mov  @R0,#0xff  frame=24/0 in_data_region=not listed
```

Every row is `ri`: the direct table finds no site for `0x84` at all, so the
issue's three `chan_init_*` functions — `common 0x012F`
`chan_init_170a_then_jmp_11b6`, `0x018C` `chan_init_1709_then_jmp_11bc` and
`0x029B` `chan_init_1708_then_jmp_11c2` — are visible here only through the
pairing. Each writes `0x84` and `0xAA` the same way, and each pair is in the
committed listings: `012F.asm` at `0x0162`/`0x0164` and `0x017E`/`0x0180`,
`018C.asm` at `0x01BF`/`0x01C1` and `0x01D5`/`0x01D7`, `029B.asm` at
`0x02DA`/`0x02DC` and `0x02F0`/`0x02F2`.

## The footprint, as executed

```console
$ python3 ec/tools/boot_xdata_sites.py
  XDATA bytes written: 6142
    0x0000-0x07FC  (2045 bytes)
    0x0800-0x0FFF  (2048 bytes)
    0x1001-0x1001  (1 bytes)
    0x9000-0x97FF  (2048 bytes)
  walked but not written: 3
    0x07FD-0x07FF  spared
```

Two clearers and one store account for those four runs. `bank0,0xD96C` covers
everything below `0x1000` except `0x0000`-`0x00FF`: it alone stores 3,837 bytes
across `0x0100`-`0x0FFF` and spares `0x07FD`-`0x07FF`, which is the
hand-derivation [`reset-vector-dptr-targets.md`](reset-vector-dptr-targets.md)
reached by decoding the bytes. `common 0x0F75` is the other two XDATA runs,
`0x0000`-`0x00FF` and `0x9000`-`0x97FF` — and **nothing in the reset vector's
bytes points at it as an XDATA clearer at all**, so a survey that enumerated the
clearers by hand and found only `0xD96C` would have been right about
`0x0100`-`0x0FFF` and wrong about the boot path. The fourth run is a single byte,
`0x1001`, and it is not a clearer at all: `ec/decompiled/common/0070.asm` shows
the reset vector's own body putting `0x3F` there before it calls anything.
`bank0,0xD89F`, the first select's target, is a single `22` and stores nothing —
established by that same write-up and re-derived by `boot_xdata_sites.py
--report`.

**The internal-RAM clear is the one loop on this path that touches no XDATA at
all, so no XDATA table can see it.** `0x0F75`'s middle loop runs R7 from `0x20`
to `0xBF` and zeroes through `mov @R0,A`, bounded by the `subb A,#0xC0` at
`0x0F89`. That range is the subject of `iram_boot_sites.py`, and it is also why
the boot walk stops rather
than following `0x0F75`'s `ret`: `0x81` is SP, so the routine zeroes the stack
pointer it is standing on, and the walk records a named stop there
(`boot_xdata_sites.py --report` prints it on every run).

## The register join

`ec/annotations/register-boot-lifetime.csv` — one row per `registers.yaml`
address, columns `addr`, `symbol`, `from_register`, `boot_verdict`,
`boot_value`. `symbol` is `gen_xdata_symbols.py`'s own spelling, so it is by
construction the string `ec/ghidra/xdata-symbols.csv` already carries for that
address; `from_register` is the entry's name verbatim, because the two differ
(`OEM_4 (CHARGING_PROFILE_MASK)` is emitted as `OEM_4_CHARGING_PROFILE`) and a
reader reconciling them needs both.

What is true of the committed table without running anything:

- every `registers.yaml` address resolves to **exactly one** verdict, and every
  verdict is a token `boot_xdata_sites.py` defines — the vocabulary is delegated,
  not re-spelled, so a token added there reaches this table without an edit here;
- every named address below `0x1000` reads `cleared` **except** `0x07FD`,
  `0x07FE` and `0x07FF`, which read `spared`;
- **no named address reads `written` or `written-unknown`.** The reset path
  either zeroes a named register or leaves it alone; the one byte it writes a
  known value into (`0x1001`) and the one it copies an unestablished value into
  (`0x0004`) are not named by `registers.yaml`;
- every named address above `0x0FFF` reads `not-reached`.

That last token is the one this join exists to produce, and it is why the table
has a row for those addresses rather than no row. `boot_verdict`'s `not-reached`
is a token *the walk itself defines*, so it is a measurement rather than an
inference from a missing row — but only because this tool asks
`boot_xdata_sites.verdict()` about every address instead of looking the address
up in a CSV. An address with no row in `boot-xdata-sites.csv` is otherwise
indistinguishable from one nobody surveyed, and a reader could not tell which.

`python3 ec/tools/register_boot_lifetime.py --report` prints each verdict's
addresses as inclusive runs, which is the form to read the split in, and prints
the caveat about what `not-reached` does not exclude beside them — so it travels
with the numbers rather than sitting in this file alone.

**`not-reached` is scoped to this walk.** It does not exclude an indirect or
DPTR-handed store from a routine the walk never entered — that population is
`ec/annotations/xdata-0440-readers.md` §7.5, and neither this tool nor the walk
searches it. A register reading `not-reached` means *nothing in the executed
reset path stores it*, never *nothing does*.

**Issue #573 owns `0x07FD`/`0x07FE`/`0x07FF` and this absorbs none of it.** The
three `registers.yaml` rows are already on main; this records only that they read
`spared` where their named neighbours read `cleared`. Nothing here writes to those
rows, and no `status:` moves — lifetime is not a status.

## The internal-RAM survey

`ec/annotations/iram-boot-sites.csv` — one row per site, over three populations,
sorted so the direct rows come first, then the resolved `@Ri` rows grouped by the
byte they name, then the unresolved block as its own run. Columns: `addr`,
`form`, `file_offset`, `region`, `runtime`, `frame_onto`, `frame_over`,
`access`, `text`, `in_data_region`.

**`ri-unresolved` is the population that makes the other two readable.** It is
every `@Ri` site in the image whose register this method does not follow to a
`mov Rn,#imm`, and its `addr` cell says `unresolved` rather than carrying a
guess. **The boot path's own IRAM clear is in it** — at `0x0F91` the byte before
the site is `clr A`, and R0 got its value from the `xch a,R0` pair above, driven
by R7. So a table carrying only the resolved rows would let a reader conclude
the boot path names four bytes of `0x20`-`0xBF` and does nothing to the rest of
the range, which is close to the opposite of what the bytes say. The range is
taken from *executing* `0x0F75` and from that routine's
own annotation name, not from scanning for the bytes it writes.

The adjacency is the whole soundness argument, and it is why the window does not
widen. `mov Rn,#imm` is two bytes and the `@Ri` instruction that consumes it must
start at the next byte, so nothing can sit between them and clobber the
register. Widening to "the last `mov Rn,#imm` before this site" would recover
more rows and every one of them would be a guess — a register reloaded in between
carries a different address, and nothing at the `@Ri` site tells the two apart.
What that costs is stated in the tool's docstring and in
`test_iram_boot_sites.py`'s `PairingCases`, which lays the blind spot down as a
fixture.

Two labels ride on every row and **neither is a filter**: `frame` is
`disasm8051.converges_from`'s onto/over pair, which is evidence about framing and
not proof — an unframed byte scan cannot tell a misframed read from a real one,
and `intmem_refs.py`'s own SELF_TEST pins `24/0` at a site that is a run of
repeated single-byte values a linear walk steps straight through.
`in_data_region` is a LABEL from `ec/annotations/data-regions.yaml`, and
`not listed` means "no listed region contains this offset", never "there is
nothing there". Dropping either would make a future run's zero look like
absence — the `docs/findings.md` §4c failure `intmem_refs.py` cites, and the
one `data_regions.refuse_filtering()` exists to stop re-introducing.

**A zero is "not found by this method", never absent.** `intmem_refs.py` opens
with that caveat and this tool inherits it rather than restating it as a new
claim. `movx a,@Ri` / `movx @Ri,A` are XDATA and are excluded — in this dump
they are how the ITE8850-PD image reaches its own external RAM, and counting them
as internal-RAM references is the mistake `intmem_refs.py`'s header records for
`0x90`. `--self-test` asserts the exclusion and the disjointness of the two
opcode tables.

**Four rows on the boot path's own instruction stream name a byte of the
range, and the fifth is the loop itself.** Filtering the table to the offsets
the reset path actually executes — the vector at `0x0070`, its four callees
`0x110A`, `0x158E`, `0x0F75`, `0x1594`, and the two targets `0xD89F` and
`0xD96C` — leaves `0x81` at the reset vector's own `mov 0x81,#0xC0`, the first
instruction of `ec/decompiled/common/0070.asm`; **`0x90`, `0x91` and `0x92`,
whose three `clr`s are three of the four instructions of `common 0x110A`**
(`ec/decompiled/common/110A.asm`, whose annotation name,
`set_iram_08_0a_clear_p1_0_p1_2`, says the same — the routine's first
instruction writes `0x0A` to `0x08`, which is below `0x20` and so outside the
range); and the `ri-unresolved`
`0x0F91`. The executed-offset filter is the one that says "the boot path", and
it is reproducible — wrap `boot_xdata_sites._step` and run
`walk_boot(image, stubs=boot_stubs())`, then keep the CSV rows whose
`file_offset` is in the executed set. Filtering instead on the seven *entry*
addresses returns the `0x81` row alone, which is a different quantity: it
excludes `0x110A`'s body because the routine is entered at `0x110A` and the
`clr`s sit at `0x110D`/`0x110F`/`0x1111`.

Every other byte of the range is reached without a direct operand at all, and
**the IRAM loop then zeroes the stack pointer that first instruction set**. So
for this range the lifetime answer is not simply the reverse of the XDATA one:
the boot path both **initialises** part of the space and **erases** all of it.
`0x110A` runs before `0x0F75` and zeroes three bytes of the range by name;
`0x0F75` then zeroes the whole of `0x20`-`0xBF` without naming any of it, which
includes those three. The net lifetime is therefore unchanged by the
correction — every byte of `0x20`-`0xBF` reads zero once the executed walk
stops, which the walk's own `direct` space shows — but the claim "the boot path
does not name these bytes" was wrong, and `0x90`-`0x92` are the counterexample.

The sizes, from the committed image:

```console
$ python3 ec/tools/iram_boot_sites.py ec/firmware/GMxMGxx_11.800
  ...
  157 bytes in the range are named by at least one site this scan found;
  the 3 it does not name are NOT FOUND BY THIS METHOD, never 'absent'

  @Ri sites in the image: 180 resolved by the pairing, 2676 unresolved
```

The three unnamed bytes are **not** a claim that the firmware never touches them.
They are the bytes this byte scan finds no encoding of, and the boot path's own
loop over the range is one of the encodings it cannot see — which is the same
sentence said a second way, and the reason the number is not the interesting
one.

## What this does not establish

Named here rather than left to a reader, and none of it answerable from this
pipeline:

- **whether anything re-clears these regions after boot.** The walk ends where
  the reset path ends; `0x0070` tail-jumps to `0x00CF`, the scheduler, and that
  is a deliberate stop with its reason printed on every `--report`. A register
  cleared at reset and re-written later is a different lifetime, and only a live
  trace shows which registers those are.
- **whether the `0x07FD`-`0x07FF` window is load-bearing or incidental.** The
  walk shows it is stepped over; nothing committed says the firmware wanted that.
- **the parameterised "zero N bytes at DPTR" helpers are still invisible.**
  `ec/annotations/xdata-0440-readers.md` §7.5 names them and calls that
  population the largest remaining hole; none of them names a byte this method
  can scan for, because the address is a caller's and the count is an argument.
- **`bank0,0xD89F` and `bank0,0xD96C` get no decompiled listing here.**
  `ec/decompiled/bank0/D89F.asm` and `D96C.asm` are not in the tree: exporting
  them needs the pinned `sdas8051` toolchain, and
  `verify_reassembly.py --check` goes red on a fresh export without it. This
  write-up therefore re-executes the committed bytes and points at
  [`reset-vector-dptr-targets.md`](reset-vector-dptr-targets.md)'s hand-derived
  3,837 as the independent check. **No Ghidra seed row is added here**, and no
  claim in this file depends on a listing that is not committed.

## Not in any gate, for the reason

`.github/scripts/agent-gates.sh` and the rest of `.github/` are pipeline files
and this branch's token has no `workflow` scope, so a branch touching them fails
at the very end. Both tools are therefore **runnable and cited standalone**, the
way [`charge-derating-counters-not-persisted.md`](charge-derating-counters-not-persisted.md)
§"Not in any gate, for the reason" records for `boot_xdata_sites.py`. No
`docs/ci/*.patch` either, for the reason that section gives: the prepared set
rots, and a non-applying patch is worse than none.

What the cheap tier *does* pick up is `python3 -m py_compile` over
`ec/tools/*.py`, which only proves the new files compile. Each new CSV is held
by its own tool's `--check`, because `test_sites_csv_regeneration.py` only
picks up tables whose header begins with `trace_xdata_refs`' base columns — a
differently-shaped table is skipped rather than mis-checked, which also means it
is not covered by it.

**`register-boot-lifetime.csv`'s row set follows `registers.yaml`, so it goes
stale on any branch that names or drops a register.** The join is keyed by the
address `registers.yaml` holds, so a merge that brings in a new one leaves this
table without a row for it until it is regenerated. Nothing in the cheap tier
above notices, because `test_sites_csv_regeneration.py` skips this table for the
header reason just given. What catches it is
`test_register_boot_lifetime.py`'s `test_the_table_names_every_address_registers_yaml_names`,
which asks the question directly, and `register_boot_lifetime.py --check` beside
it. Both belong to this branch's own suite, so the branch that moves
`registers.yaml` is the one that has to run them.

## Reproducing this

```sh
# the join, regenerated and diffed against the committed table
python3 ec/tools/register_boot_lifetime.py --check
python3 ec/tools/register_boot_lifetime.py --self-test
python3 ec/tools/register_boot_lifetime.py --report

# the internal-RAM survey
python3 ec/tools/iram_boot_sites.py --csv --check
python3 ec/tools/iram_boot_sites.py --self-test
python3 ec/tools/iram_boot_sites.py ec/firmware/GMxMGxx_11.800 0x84 0xAA

# the walk both build on, unchanged
python3 ec/tools/boot_xdata_sites.py --report
python3 ec/tools/boot_xdata_sites.py --csv --check
python3 ec/tools/boot_xdata_sites.py --self-test

# correction 2, re-derivable
python3 ec/tools/intmem_refs.py ec/firmware/GMxMGxx_11.800 0x84
cat ec/decompiled/common/0F75.asm ec/decompiled/common/012F.asm

# the suites and the mechanical gates
bash tools/run-tests.sh ec/tools
bash .github/scripts/agent-gates.sh
```

No Ghidra, no network, no hardware.

## What this opens

- **The pointer the pairing cannot follow is now a named population** rather
  than an absence. `common 0x07B6`'s `zero_seven_xdata_bytes_from_200b` is the
  shape it has in its simplest form: repeated stores through one DPTR with no
  `inc` between them, so there is no per-byte address to scan for and no `@Ri`
  either. The `ri-unresolved` rows are where the `@Ri` half of that population
  shows up, and they are now countable rather than merely invisible.
- **A driver author can answer "is this byte firmware-initialised or residue?"
  for any named XDATA register**, which is the precondition for a
  read-modify-write to be safe across a suspend/resume. For the internal-RAM
  bytes the answer is the other way round and now says so: the boot path
  *clears* `0x20`-`0xBF` — naming four bytes of it and erasing the rest
  without naming them — so anything a driver leaves there is gone at the next
  reset.
- **A note that spells `PD_MARKER` in its own text is a read of it.**
  `check_pd_marker_contract.py` files a module that puts the marker's bytes into
  its output while nothing in the same function compares them as `unverified`,
  and this change tripped it by copying `intmem_refs.py`'s own missing-marker
  note instead of saying what *this* tool does with the boolean. The note now
  names no constant, and the census is back to its committed bytes — but the
  checker's `refuse`/`note` rows are read per function, so a module that
  delegates its comparison to a helper is invisible to it unless it also spells
  the constant somewhere. Worth knowing before the next tool delegates.
- **The `intmem_refs.py` renderer crashes on the reserved `0xA5` opcode**, which
  its own `OPCODE_TABLE` carries and its own `SELF_TEST` requires the census to
  keep. `intmem_refs.py <image> 0x2F` exits 1 with a `TypeError` rather than a
  census, because the reserved row's mnemonic names no address and so has no
  `%02x` to substitute. It is fixed locally in `iram_boot_sites.direct_text()`
  and left alone in the sibling: the fix belongs in the file that owns the
  rendering, on its own branch, and it is not this issue's.