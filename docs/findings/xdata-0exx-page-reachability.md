# The `0x0Exx` page, per address: what reaches it and what does not

`ec/annotations/dsdt-ecmg-field-sweep.md` §5 leaves the `0x0Exx` page as a
question rather than a result: 59 DSDT names sit on `0x0E0D`-`0x0ECF`, and the
ones with no direct `MOV DPTR` site were left open because the file correctly
refuses to read a zero as *absent*. This settles the question the sweep posed,
one address at a time, and answers the two halves §5 names.

Every address of `0x0E00`-`0x0EFF` is in
`ec/annotations/xdata-0exx-page-reach.csv`, each classified **`reached`** with
the site that reaches it, or **`not-reached-by-this-method`** — a statement
about five static passes, never about the byte. The table is the product of one
command:

```console
$ python3 ec/tools/xdata_page_reach.py ec/firmware/GMxMGxx_11.800 \
      0x0E00 0x0EFF --csv > ec/annotations/xdata-0exx-page-reach.csv
```

The headline is not a count, and it is not that the sweep's unreached addresses
turned out to be reached. **None of them is.** The table reaches only what a
site names, and on this page that is exactly the set the direct scan already
found — the walks add a method, not an address. What the sweep could not see is
one mechanism, and it is a good one: **`bank0:0xF2F8` — a routine absent from
`ghidra-functions.csv`, reached only as case `0x01` of the dispatch table at
`0xF257` — copies `0x0EC0`-`0x0ECF` into `0x0F61`-`0x0F70` sixteen times**,
which is how the sixteen `MGO0`-`MGOF` bytes are reached after all, and which
makes `0x0F61` a byte written by two different payloads in one routine.

Those sixteen are reached by *decoding the loop*, not by the table: the site
builds its DPTR from a register, so every pass here resolves the page and none
resolves the byte. The table records that as `page_site`, and the copy is
derived from the disassembly quoted below. Keeping those two apart is the whole
calibration of this page, and §"What this method cannot see" says so again.

## What the table says, and the shape of what it does not

The addresses a site reaches are `0x0E00`-`0x0E08`, `0x0E0B`, `0x0EA8`-`0x0EAF`
and `0x0EB8`. The runs with no reach are `0x0E09`-`0x0E0A`, `0x0E0C`-`0x0EA7`,
`0x0EB0`-`0x0EB7` and `0x0EB9`-`0x0EFF`.

One of those runs corrects the filed arithmetic, and the correction is worth
making here rather than reproducing the number. The issue that prompted this
describes "148 consecutive ones, `0x0E0C`-`0x0E7F`". The longest zero run on
the page is `0x0E0C`-`0x0EA7`; `0x0E7F` is inside it, but the run continues past
`0x0E80` to `0x0EA7` and stops only because `CTL0` is reached at `0x0EA8`. The
run is bounded by the CTL block, not by the page's middle.

The other correction is to the issue's premise, and it is not this write-up's
to make: the issue holds that "not one of those 59 names is referenced by any
ASL outside the field list itself". **That was already refuted on main.**
`docs/findings/ecmg-asl-references.md`, in *The `0x0Exx` page: 20 of 59
referenced, and that is a lead, not an answer*, records that 20 of the 59 are
ASL-referenced — `CCI0`-`CCI3` and `MGI0`-`MGIF`, all in `Method (UCEV)` — and
`dsdt_ec_fields.py --self-test` asserts it. The issue predates that correction.
Nothing here re-derives it or contradicts it.

## `bank0:0xF2F8`: one block builder, two payloads

The routine is not an unannotated orphan. `decode_index_table.py` names it
**case `0x01` of a seven-entry table at `0xF257`**, dispatched by the
`switch_case_dispatch` at `0x7151` that `0xF254` calls, and
`ec/annotations/index-table-entries.csv` carries the row. It is reached; it is
simply reached by no `lcall`, which is why a scan for call targets misses it
and why `code-map.csv` calls its bytes `unreached` — a label that tool's own
header defines as *not reached by this method*, and case-table bytes are the
case it names.

Disassembled from a bank image, the first half is a counted copy:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/disasm8051.py /tmp/bank0.bin --at 0xF2F8 -n 24
0x0f2f8  900f60   mov  dptr,#0x0f60
0x0f2fb  74a0     mov  a,#0xa0
0x0f2fd  f0       movx @dptr,a
0x0f2fe  e4       clr  a
0x0f2ff  ff       mov  r7,a
0x0f300  74c0     mov  a,#0xc0
0x0f302  2f       add  a,r7
0x0f303  f582     mov  0x82,a
0x0f305  e4       clr  a
0x0f306  340e     addc a,#0x0e
0x0f308  f583     mov  0x83,a
0x0f30a  e0       movx a,@dptr
0x0f30b  fe       mov  r6,a
0x0f30c  7461     mov  a,#0x61
0x0f30e  2f       add  a,r7
0x0f30f  f582     mov  0x82,a
0x0f311  e4       clr  a
0x0f312  340f     addc a,#0x0f
0x0f314  f583     mov  0x83,a
0x0f316  ee       mov  a,r6
0x0f317  f0       movx @dptr,a
0x0f318  0f       inc  r7
0x0f319  ef       mov  a,r7
0x0f31a  b410e3   cjne a,#0x10,+0xe3
```

`R7` runs `0x00`-`0x0F`: sixteen iterations, source `0x0EC0`-`0x0ECF`,
destination `0x0F61`-`0x0F70`. Two constructions, one counted walk, and the
second DPTR is built the same way as the first — which is why
`computed_dptr_sites.py` names `0xF306` for page `0x0E` and `0xF312` for page
`0x0F`, each with the low byte unresolved. The tool reports them as **reached
pages, not reached addresses**, which is the honest reading: no site in this
image resolves a computed low byte, so crediting the page to its 256 addresses
would claim every one of them.

### The MGI/MGO split is one run and one unreached half

The loop's source run is exactly `MGO0`-`MGOF`. The issue reads the
`MGI0`-`MGIF` / `MGO0`-`MGOF` arrangement as a 31-of-32 split and calls it "a
shape, not a coincidence"; the sweep it builds on declined to go that far,
recording only that `MGI8` is "the only byte of the 32" with any direct site
and that "sixteen neighbouring bytes and one site is a shape this file does not
explain". So this is not a correction of a claim the sweep made — it is an
answer to the question the sweep left open: the sixteen `MGO` bytes are reached
as one block by a base-plus-index construction, which is what a paired array
looks like from outside. That much is settled — by decoding the loop, not by the
table.

The `MGI` half is not. `MGI0`-`MGIF` sit at `0x0EB0`-`0x0EBF`, in the
`0x0EB0`-`0x0EB7` zero run, and no pass here reaches them. `MGI8` at `0x0EB8` is
reached, by the read-modify-write at `bank0:0xF228` — one byte, in passing, not
as a run. So the arrangement is one run reached and one unreached, which is a
different statement from "31 of 32", and the unreached half stays unreached.

## `0x0F61` has a second writer, earlier in the same routine

`CTL0`'s note in `ec/annotations/registers.yaml` describes the eight-stanza copy
at `bank0` `0xF335`-`0xF374` into `0x0F61`-`0x0F68` and calls it the only one.
It is not. Two things write that window, and both are *in the same routine* —
the counted loop first, then the straight-line copy below it:

- `0xF32F` stamps `0x98` to `0x0F60`, and `0xF335`-`0xF374` copies
  `0x0EA8`-`0x0EAF` into `0x0F61`-`0x0F68`, one `mov dptr` / `movx` pair per
  byte.
- The counted loop above writes the same eight bytes — and eight more — from
  `0x0EC0`-`0x0ECF`.

One block builder, two payloads: a computed walk, then a straight-line copy, in
a single routine, each stamping a byte at `0x0F60` first — `0xA0` at `0xF2F8`,
`0x98` at `0xF32F`. The loop's destination run `0x0F61`-`0x0F70` is *wider*
than the copy's `0x0F61`-`0x0F68`. That is a "register with a second writer",
which is the shape CLAUDE.md asks a change to surface.

What the two stamps *select* is not established, and the obvious reading is
worth refusing explicitly: no pass run here resolves a read of `0x0F60`, so "a
type byte the consumer dispatches on" would be a story about a byte this method
could not resolve a reader for. It may equally be read through the same
published pointer the destination is, and that is the open question below rather
than a settled mechanism.

It is also not the only writer, and the tool's walk pass is what shows it. Run
over the destination window rather than the page:

```console
$ python3 ec/tools/xdata_page_reach.py ec/firmware/GMxMGxx_11.800 0x0F60 0x0F70
```

`0x0F61` is reached by `bank0:0xF339` (the copy) **and** by seven `inc dptr`
walks whose seeds are at `0x0F60` — `bank0:0xE8A0`, `0xE8C8`, `0xEA27`, `0xF0C5`,
`0xF151`, `0xF18A` and `0xF4C1`. Each writes `0x0F60` and increments onto
`0x0F61`, so all seven *reach* it — but reaching it and storing to it are two
different claims, and `trace_xdata_refs.classify()` keeps them apart. Four of
the seven (`bank0:0xE8C8`, `0xEA27`, `0xF0C5`, `0xF4C1`) go on to store a
second byte, which is what their `write x2` cell says; `bank0:0xE8A0`,
`0xF151` and `0xF18A` `inc dptr` into an `lcall` or a `ret` and are `write x1`,
so their reach is a walk onto the byte rather than a store to it. `0x0F62`
picks up one of the four (`bank0:0xE8C8`, which walks three). **So the
second-writer claim is true and understates the case**: the loop and the copy
both store `0x0F61` in one routine, and the walks reach it from outside that
routine entirely.

### What reads `0x0F61`-`0x0F68`

No reader found by this method, and what the routine does next is where one would
have to come from. After the loop it calls `bank0:0xF499`:

```console
$ python3 ec/tools/disasm8051.py /tmp/bank0.bin --at 0xF499 -n 7
0x0f499  900a56   mov  dptr,#0x0a56
0x0f49c  740f     mov  a,#0x0f
0x0f49e  f0       movx @dptr,a
0x0f49f  a3       inc  dptr
0x0f4a0  7460     mov  a,#0x60
0x0f4a2  f0       movx @dptr,a
0x0f4a3  22       ret
```

It writes `0x0F` to `0x0A56` and `0x60` to `0x0A57`: a little-endian pointer to
the block the routine has just filled. The routine therefore **publishes a
pointer to that block, and both bytes of the pointer have read sites** —
`0x0A57` has them across the common area and `0x0A56` has more still
(`trace_xdata_refs.py --counts-only` on each). That is the same blind spot the
writing side has, and it is where a reader of this window would have to come
from; whether any of those sites dereferences into `0x0F61`-`0x0F70` is **not
established here**, so the publish site is a lead and not a decoded consumer.

Following the published pointer into the common area's readers is a separate
sweep over a different region — its own piece of work, which this write-up does
not do. It is named here as the next step with the publish site cited.

## What writes `0x0EA8`

Unchanged, and now with the whole page searched rather than one scan's worth.
`0x0EA8` has three direct sites and **all three are reads**: the `0x12`
comparison at `bank0:0xF221`, its own branch target at `0xF234`, and the copy's
source read at `0xF335`. No pass in this tool writes it.

So the byte is read at every site that names it and written by nothing found
here. The place to start is the one §5 already named: the `0x12` comparison at
`bank0:0xF221` reads a value something chose, and the writers that choose it
are not on this page. Naming that is not the same as finding the writer, and the
entry's `status:` is unchanged: `present-untested` is warranted by its reference
count, and a read is not a write.

## What this method cannot see

Named, because a zero in the table is only worth what the method behind it is
worth:

- **A page reached is not an address reached.** Every computed DPTR site in
  this image leaves its low byte at run time, so `page_site` is separate from
  the verdict throughout. `bank0:0xF306` reaches page `0x0E` and names no byte
  in it; the `0x0EC0`-`0x0ECF` run is decoded from the disassembly above, not
  read out of the table.
- **The `SN1T`-`SN5T` stride is unresolved, and the method cannot settle it.**
  `0x0E10`, `0x0E12`, `0x0E14`, `0x0E16`, `0x0E18` sit in the `0x0E0C`-`0x0EA7`
  zero run. Neither the `inc dptr` walk (which needs a two-byte seed) nor the
  pair-accessor pass reaches the page from a seed, and a stride-2 shape with
  unnamed gaps is equally consistent with a base-plus-index access and with a
  subsystem nothing touches. Inventing an answer from the spacing is the error
  `CTL0`'s note already records making once.
- **An `inc dptr` walk needs a two-byte seed.** A walk entered with DPTR handed
  over by an `lcall` is not followed — `trace_xdata_refs.py`'s
  `DPTR handed to ...` cell is that case, and it appears in this page's rows.
- **The same cell leaves the direction unresolved.** `classify()` reports
  `DPTR handed to ... -- direction unresolved here` because it stopped at the
  `lcall` without seeing a `movx` to decide read or write, so a site in that
  state is neither a reader nor a non-reader as far as this method is concerned.
  It is where a reader of `0x0F60` would hide if one exists: three of that
  address's sites carry the cell, which is why the note on the stamp byte above
  says no pass run here *resolves* a read rather than that none exists.
- **`movx @Ri` needs both halves literal.** All the sites in this image leave
  at least one unresolved, which is why the `indirect` column is empty
  everywhere here rather than because the mode was skipped.
- **An `lcall`-supplied accumulator is a refusal `addc_dph_sites.py` already
  names.** Four such sites have `0x0E` in their two-element page set; they
  appear in `page_possible`, which is a page the scan could not rule out and
  deliberately not a reach.
- **Nothing here is a behavioural claim.** No register was read back and no
  hardware was involved. Every statement above is a static measurement over
  `ec/firmware/GMxMGxx_11.800`, reproducible with the commands quoted.

## Reproducing it

```console
$ python3 ec/tools/xdata_page_reach.py ec/firmware/GMxMGxx_11.800 0x0E00 0x0EFF \
      --csv --check ec/annotations/xdata-0exx-page-reach.csv
$ python3 -m unittest discover -s ec/tools -p test_xdata_page_reach.py
```

The first is the table's own check; the second holds it to the tools it joins,
and is where the verdict vocabulary is asserted to stay out of
`registers.yaml`'s `status:` values.
