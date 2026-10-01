# What the assembler's listing holds for `bank0/801F` and `bank0/AB6D` (2026-10-01, issue #229)

`ec/ghidra/reassembly.csv` records both rows as `assembler-gap`, with the
detail `no bytes emitted at 801F` and `no bytes emitted at AB6D`. That detail
is written from inside `verify_reassembly.check_one()`'s comparison loop, so it
says what the tool did **not** find: an entry for that address in the `.lst`
that `read_lst()` parsed. It is not a statement that the assembler emitted
nothing, and the two rows are the cheapest place to show the difference,
because each is a single instruction and an ordinary form — `movx @dptr,a` and
`ret`.

These are the source `check_one()` generates for those two rows and the listing
the available assembler produced from it. Both are committed verbatim; the
source is two instructions of the tool's own `check_one()` and is reproduced by
the tool rather than transcribed.

- `2026-10-01-bank0-801F.s51`, `2026-10-01-bank0-801F.lst`
- `2026-10-01-bank0-AB6D.s51`, `2026-10-01-bank0-AB6D.lst`

## The environment, captured before the run

`sdas8051` from PATH, the one `.github/actions/project-setup` installs on a
GitHub-hosted runner, which is what `evidence/ec-reencode/2026-09-23-sdas8051-versions.md`
measured against too:

```
$ sdcc --version
SDCC : mcs51/z80/z180/r2k/r2ka/r3ka/sm83/tlcs90/ez80_z80/z80n/ds390/TININative/ds400/hc08/s08/stm8/pdk13/pdk14/pdk15/mos6502 4.2.0 #13081 (Linux)

$ command -v sdas8051
/usr/bin/sdas8051

$ sdas8051 | head -2
sdas Assembler V02.00 + NoICE + SDCC mods  (Intel 8051)
Copyright (C) 2012  Alan R. Baldwin
```

**This is not the build the committed report was measured with**, which carries
`sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14`. That difference is the whole reason
this file cannot close the question; see the last section.

## The generated source

`check_one()` anchors at `insns[0][0]`, opens an absolute `.area`, and emits
one line per translated instruction. For a one-instruction listing that is
three lines, and they are the two committed `.s51` files:

```
	.area CODE (ABS)
	.org 0x801f
	movx	@dptr,a
```

```
	.area CODE (ABS)
	.org 0xab6d
	ret	
```

Both are `to_sdas()`'s output verbatim — `movx @DPTR, A` lower-cases to
`movx @dptr,a`, and `ret` carries Ghidra's trailing blank operand. Neither
instruction is declined, so neither row has a skipped instruction and both
report `instructions_unchecked` 0 in the committed CSV.

## What the assembler did with them

`sdas8051 -lxosgff f.s51` — the flags `check_one()` passes — **exits 0 on both**.
There is no diagnostic, no `?` line and no error. Each listing carries one
addressed, byte-bearing entry, and the entry is what `read_lst()`'s regex
requires: an address, a byte run, and the bracketed relocation class, all on
one line.

```
      00801F F0               [24]    3 	movx	@dptr,a
      00AB6D 22               [24]    3 	ret	
```

Fed back through `read_lst()` as `check_one()` reads it:

```
801F -> {'801F': 'F0'}
AB6D -> {'AB6D': '22'}
```

And through `check_one()` itself, with the same `check_one()` call the report
was written from and the rebuilt bank images. The tuple is the landed
seven-value return — `outcome, detail, compared, checked, skipped, digest,
anchor` — so the two `1`s on `bank0 801F` are one byte compared and one
instruction translated, which is the distinction `docs/findings.md` §11's
correction is about:

```
bank0 801F store_1901     -> ('match', '', 1, 1, 0, '1a65642b94ed06db', 0x801f)
bank0 AB6D shared_noop_ret -> ('match', '', 1, 1, 0, 'b8f13374c6a2662b', 0xab6d)
```

Both digests are the committed CSV's own, so the listing text `check_one()`
parsed is the text the committed report was measured from; the only thing
that differs between the two measurements is which build answered.

## What this does not establish

**It does not say the pinned build emits the same listing.** The committed
report was measured with `05.50.4+NoICE+SDCCmods-WIP-R14` and records both rows
as `assembler-gap`, and nothing here has that build on it. What is measured is
that on `02.00` the forms are expressible and the listing parses — which
removes *`sdas` refusing the form* as an explanation for these two rows on this
build, and leaves the two candidates that a build difference would explain:
the listing's shape differing under the pinned build, or the `.area`/`.org`
anchoring producing something `read_lst()`'s regex cannot see **there**. The
second is not it on this build — `.org 0x801f` is what puts `00801F` on the
line above — but that is a statement about `02.00`, not about the build the
committed rows came from.

`evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv` already records both
rows moving `assembler-gap` → `match` under this build, and `bank1/D946` with
them. It records the outcomes; it does not commit a listing, which is what it
would take to read one.

`D946` stops at 0xDA6E after 148 instructions in, and that 148 is walked off
the committed `ec/decompiled/bank1/D946.asm` rather than read out of the row:
the listing runs 0xD946–0xDAAC, the 148 instructions below the 0xDA6E its
`detail` names end at 0xDA6D, and 28 further instructions follow them. The
listing is not exhausted at the address the comparison stopped at, so running
out of source is not among the candidates.

## Reproduce

No hardware, no Windows, no Ghidra, no network. Needs an `sdas8051` on PATH and
nothing else.

```
$ scratch=$(mktemp -d)
$ python3 ec/tools/verify_reassembly.py --work "$scratch" --limit 4
```

`--limit 4` covers neither row; the two are the `bank0,801F` and `bank0,AB6D`
rows of `ec/decompiled/listing-index.csv`, well past it. To get exactly these
two, generate the source with `check_one()`'s own loop over
`ec/decompiled/bank0/{801F,AB6D}.asm`, write it to `f.s51`, and run
`sdas8051 -lxosgff f.s51` beside it.