# The 107 `inc DPTR`-only bytes, the rule for admitting one, and why 73 of them are declined (issue #707)

Issue #707 asked a static-admission question: is `MOV DPTR,#addr` the right
admitting encoding, or is "some committed routine dereferences it as XDATA" --
and, whichever the answer, it wanted the 73 such bytes listed rather than
counted. This page is the answer, the list, and the accounting.

**Two of the three, and the split is not one number.** §4.7 of
[`xdata-register-map.md`](xdata-register-map.md) established that 107 of the 214
addresses the pair pass reaches are *only ever* the `inc DPTR` half of an
accessor's pair, and that 73 of those have no `MOV DPTR,#addr` encoding in
`common`, `bank0` or `bank1`. The 107 split **73 / 34**, and the 34 split
**7 entered / 27 not**. All 107 are in
[`xdata-inc-dptr-only.csv`](xdata-inc-dptr-only.csv), one row each, and §1
prints the command that regenerates it.

**The rule is stated below and the 73 are declined**, on a ground that does not
depend on any of these counts (§3). The census is a per-`.c`-file lower bound
on the machine code, and admitting a register list on it would make the census
an authority on the thing it is a lower bound for. That is a statement about
what the two files are *for*, so it survives a re-derivation that moves every
figure on this page.

**Nothing was observed.** No register `status:` moved, no entry entered or left
`registers.yaml`, no `static_refs*` count moved, and no hardware or Windows
machine was involved. Every number re-derives from the committed firmware and
the committed decompiled tree.

## 1. How to re-derive all of it

```console
$ cd ec/tools
$ python3 inc_dptr_sites.py ../firmware/GMxMGxx_11.800
$ python3 inc_dptr_sites.py ../firmware/GMxMGxx_11.800 --csv \
        > ../annotations/xdata-inc-dptr-only.csv
$ python3 inc_dptr_sites.py ../firmware/GMxMGxx_11.800 --check
$ python3 -m unittest test_inc_dptr_sites.py
```

`--check` diffs the committed table byte for byte against a fresh generation and
needs no Ghidra, no network and no hardware. The suite is **not** wired into
`.github/scripts/agent-gates.sh`: that file lives under `.github/`, which this
branch's push token cannot write, so the two-line registration is a human's
change. Until it is made, the suite is run by hand and this page does not imply
CI runs it.

**Why a tool, when the census CSV exists.** `xdata-registers.csv` cannot answer
the question. `scan()` folds a pair call into one `pair-literal` row covering
`addr` and `addr + 1` under the same spelling
(`xdata_register_map.py:2241-2242`), so 174 of the 214 rows have a `+1` neighbour
spelled identically and the seed/`+1` distinction exists only inside
`pair_sites()`. "Which 107 of the 214 are only the `inc DPTR` half" is therefore
not a query against a committed artifact, and §4.7 was right to state a count
and a recipe rather than a list.

**The population, and the arithmetic under it.** `S` is every `addr` a call site
passes and `S1` every `addr + 1`. On the committed tree |S| == |S1| == 107 and
`S & S1` is **empty**, so `S1 - S` is the whole 107 and 107 + 107 ==
`PAIR_ROWS` == 214. The disjointness is measured on every run rather than
assumed, and the tool prints the two halves' sizes and their intersection: a
tree where an address is a seed in one call *and* an `inc DPTR` half in another
would shrink `S1 - S` and the summary would say so.

## 2. The 107, and the four populations

| population | count | what makes it that one |
|---|---:|---|
| no `MOV DPTR` site in any image | **71** | the §3 rule has nothing to admit on, and the byte scan found nothing anywhere |
| pd-image sites only, none in the main EC | **2** | `0x043B` (2 sites), `0x04A5` (3 sites) -- another program's byte at the same address number |
| **= the 73** | **73** | no main-EC `MOV DPTR` site; §3 declines them |
| main-EC `MOV DPTR` site, entered in `registers.yaml` | **7** | `0x030F 0x0403 0x0435 0x0437 0x0439 0x04A7 0x0523` |
| main-EC `MOV DPTR` site, **not** entered | **27** | the shape §6's rule admits; §5 |
| **total** | **107** | |

71 + 2 = 73, and 7 + 27 = 34, and 73 + 34 = 107. Every row of
`xdata-inc-dptr-only.csv` falls in exactly one of the four, and the
`population_of()` classification the summary prints is read back off the row
rather than recomputed, so this table and the CSV cannot drift apart silently.

**The 71 + 2 cut is a different question from the 73, and the two are not
merged.** "Found in no image" and "found in another program" are different
reasons to decline, and the pd-image-only pair is already a documented
population: `0x043B` is one of the eleven bytes §6 of
[`xdata-0400-045f.md`](xdata-0400-045f.md) lists as having PD-only sites, with
the same count of 2. Merging them would be the `0x07E2`-`0x07E5` mistake
`trace_xdata_refs.py`'s own docstring opens with -- a `MOV DPTR` in the pd image
says nothing about what the main EC does with that address number, because they
are not the same byte.

**The 73, in address order.** The first ten are the ten §4.7 spells, and the
list runs to `0x0647`:

```
0x0309 0x0311 0x0313 0x0317 0x031B 0x0333 0x0337 0x0341 0x0346 0x034F
0x0364 0x036F 0x0379 0x037B 0x037D 0x037F 0x0381 0x0385 0x039F 0x03A7
0x03AD 0x03B9 0x03D1 0x03D3 0x03DF 0x03E1 0x03E3 0x03E5 0x03E7 0x03E9
0x03EB 0x03ED 0x03EF 0x03F3 0x03F5 0x03FD 0x0405 0x0409 0x040B 0x040D
0x040F 0x0411 0x043B 0x04A5 0x04A9 0x04F3 0x04F5 0x04F7 0x04F9 0x050F
0x0511 0x0515 0x051D 0x051F 0x0521 0x052B 0x052F 0x0533 0x0535 0x0537
0x053B 0x053D 0x053F 0x0541 0x0543 0x0545 0x0547 0x0549 0x056D 0x056F
0x05B3 0x05C3 0x0647
```

### 2a. Ten, not eleven

§4.7 of `xdata-register-map.md` writes "`0x0309 0x0311 0x0313 0x0317 0x031B
0x0333 0x0337 0x0341 0x0346 0x034F` and 63 more, running to `0x0647`" -- **ten**
addresses, and 10 + 63 = 73 closes on the count. Issue #707's prose called
them eleven, counting from that list. **The eleventh address in the 73 is
`0x0364`, which §4.7 does not name**; the list above is the measurement, and
`test_inc_dptr_sites.py` pins both ends of it so a reader who goes looking for
the eleventh finds `0x0364` and learns where the mismatch is.

### 2b. What the census says about them, and what it does not

The 73 carry **196 census references** -- 93 `read`, 103 `write`, and no
`read+write` on any of them. Per address, 15 are reached only by readers, 32
only by writers, and 26 by both. Four of the seven accessors reach them
(`read_xdata_pair_to_r1r2`, `read_xdata_pair_to_r3r4`,
`write_r1r2_to_xdata_pair`, `write_r3r4_to_xdata_pair`); the fifth,
`read_xdata_pair_to_b_and_a`, reaches one address of the 34 (`0x0835`) and none
of the 73. The two accessors the pass selects that reach nothing here,
`store_r1_r2_to_xdata_at_dptr` and the pd image's `read_be16_from_dptr`, are
still selected on their own `.asm` -- neither is dropped from the set because
this population does not happen to use it.

Three facts about those rows are load-bearing for §3 and are measured in
`TheCensusShape`:

- **all 73 are `pair-literal`-only.** No `DAT_EXTMEM_` token and no generated
  symbol name spells any of them anywhere in the main EC. They are reached as an
  argument, and by nothing else, so a census row for one is a pair row and
  nothing more.
- **none of the 73 is in the pd census.** The tool merges `common`, `bank0` and
  `bank1` and never reads the pd dict, so an address appearing there would be a
  different byte at the same address number and the row's single `addr` would be
  about the wrong one.
- **`census_refs` closes on the bucket columns on all 107 rows**, and the
  `passed-to-call` and `address-taken` buckets are zero everywhere on the 73. A
  pair-accessor call is the caller's only reference to the address, so it cannot
  also be a handoff.

**None of this is evidence the EC *acts* on any of these bytes.** A resolved
site is a **static** read or write, which §4.7 of `xdata-register-map.md` states
at length, and the direction is the accessor's rather than the caller's:
`write_r1_r2_to_xdata_pair(0x434,0,0)` stores a constant zero and the census
records that as a write of `0x0434` and `0x0435` without recording that it is a
clear.

## 3. The rule, in §6's own form

Stated here and edited into §6 of `xdata-0400-045f.md` in place, because a
second rule beside the first is the thing issue #707's fourth item rules out.

> **A byte is entered in `registers.yaml` if and only if the EC image has at
> least one direct `MOV DPTR,#addr` site for it.** A byte that some committed
> routine dereferences as XDATA *only* through a pair accessor's `inc DPTR` is
> **not** entered on that basis. The encoding is real -- the accessor's `movx`
> is committed bytes and `param_1 + 1` is a byte the firmware dereferences --
> and `xdata-inc-dptr-only.md` lists all 107, so the question is decided rather
> than left open. What stops them being entered is not that the encoding is too
> weak. It is that **`registers.yaml` is not the census**: a census row is a
> per-`.c`-file lower bound on the machine code, and in the overlapping-export
> case §4.7 measures it is an *upper* bound on it. Admitting on it would make
> the census an authority on the thing it is a lower bound for.

**So the answer to the issue's question is: the pair accessor is a second
admitting encoding, and the 73 are in the census on that basis rather than on
the byte scan's.** Those are two different claims and this page keeps them
apart. What the accessor establishes is a static access; what it does not
establish is that the byte is a register, that the EC acts on it, or that any
two sites agree about what the value means.

**The reason is about method roles, not about what either method found.** "The
byte scan finds no site" is a statement about a method, and `docs/findings.md`
§4c is this repository's retracted case of reading such a silence as absence --
which is why the issue's constraint on declining ("the reason must be one that
is still true after this pass") is not met by re-counting the zeros. The reason
given is that `gen_xdata_symbols.py`, the Ghidra project and an upstream driver
all treat `registers.yaml` as the register list, and the census has never been
what puts an address in it. No further pass changes that, and the reason does
not depend on 73, on 71, or on any other number here.

**What the admit branch would cost, since a human may want it.** It is not
modular, which is the load-bearing part of the decision. Adding 73 rows to
`registers.yaml` cascades: `gen_xdata_symbols.py` → `ec/ghidra/xdata-symbols.csv`
(+73 names) → `load_symbols()` → the `name` column of `xdata-registers.csv` and
the `named_addrs` column of `xdata-clusters.csv`, plus `ORACLE["named_in_tree"]`.
There is **no mechanism to withhold a symbol**, and `cluster_key` hashes
membership only -- so cluster ids survive, but two committed CSVs and an oracle
do not. Regenerating both census CSVs inside one PR is a large,
conflict-prone diff against a tree with open agent branches, for 73 rows a human
may well decide differently. The command that would do it is
`python3 gen_xdata_symbols.py` followed by `xdata_register_map.py --out-registers
… --out-clusters …`; it is named so the branch is reversible without
re-deriving anything, and it is not taken here.

## 4. `0x0420`, the counter-example that keeps the rule narrow

The tempting rule -- "any literal first argument names an XDATA address" -- is
wrong, and `0x0420` is why. It is passed to `add_full_product_to_dptr(0x420,
0x60, *param_1)` at `pd/34A5.c:19`, the same bare-hex spelling that resolves the
73. The callee is the difference, and the committed `.asm` decides it:

```console
$ cd ec/tools
$ cat ../decompiled/pd/10BC.asm
10BC     a4 - -   mul      AB
10BD     25 82 -  add      A, DPL
10BF     f5 82 -  mov      DPL, A
10C1     e5 f0 -  mov      A, B
10C3     35 83 -  addc     A, DPH
10C5     f5 83 -  mov      DPH, A
10C7     22 - -   ret
```

**No `movx` at all.** The routine adds a product to DPTR and returns; it
dereferences nothing, so `pair_accessor()` does not select it and the address
space is never established. The six accessors the pass *does* resolve through
are two `movx @DPTR` an `inc DPTR` apart, which is what the discriminator reads
and what `0x0420`'s callee fails. `0x0420` stays a `NOT_IN_TREE` entry in
`xdata_register_map.py` with its own wording, and nothing here changes it.

**The address space is a property of the callee's body, not of the token.** That
is the whole discriminator, and `CounterExample` in the test suite holds it
from both sides: `add_full_product_to_dptr` is not a selected accessor and
`pair_accessor()` returns `None` for its listing, while every accessor the table
names still reads back as the direction the table recorded, out of the committed
`.asm` rather than out of the accessor table.

## 5. The 27: entered by §6's rule, and left for a follow-up

The 34 that *do* have a main-EC `MOV DPTR` site are 7 already entered and 27
not, and the 27 are:

```
0x0315 0x0319 0x0344 0x0383 0x0389 0x0393 0x03F7 0x03F9 0x04A1 0x04A3
0x04AF 0x04BF 0x0503 0x0505 0x0507 0x0509 0x050B 0x050D 0x0519 0x051B
0x0529 0x0609 0x060B 0x060D 0x060F 0x0835 0x0837
```

They have the shape §6's existing rule admits, and they are not entered here for
a reason that is about coverage rather than about the rule: **none of the 27 is
on the `0x0400`-`0x045F` page**, and no other page's rule covers them. The four
page addresses among the 34 are `0x0403`, `0x0435`, `0x0437` and `0x0439`, and
**all four are already entered** -- which is why §6's rule, applied to this
population, changes nothing on the page at all.

So each of the 27 needs its own `name`/`note` decision, off-page, with no
existing rule to lean on. That is an issue, not a footnote, and it is named as
the follow-up this pass opens rather than folded in as a silent extra diff
against a file several other branches are editing.

## 6. The seven on the page, and §6's 50

`xdata-0400-045f.md` §6's 50 and this population overlap in exactly seven
addresses -- `0x0405 0x0409 0x040B 0x040D 0x040F 0x0411 0x043B` -- which §4 of
that page already names as "reached only as `param_1 + 1` inside an accessor".
Those seven are why §6's membership rule and §3's are **the same rule and not
two**, and the overlap is pinned in `test_inc_dptr_sites.py` so the two pages
cannot drift apart silently.

The page's 50 therefore splits the same way this population does:

| | count | |
|---|---:|---|
| reached as an `inc DPTR` half (the seven above) | **7** | declined by §3, as the page already declines them |
| reached by no accessor at all | **43** | not the same cut as §6's, and not a subtraction from it |
| **total** | **50** | |

**§6 splits the 50 by *site* and this one by *reach*, and the two are not the
same partition.** §6's is 39 with no site in any image plus 11 with pd-image
sites only, which are disjoint by definition; this one is 7 the pair pass
resolves plus 43 it does not. So 39 + 11 = 50 and 7 + 43 = 50 both close, and
neither figure is derived from the other. The two partitions cross at exactly
one address, `0x043B` -- one of the seven *and* one of the eleven -- which is
worth naming because it is the only byte on the page that appears in three of
this repository's lists at once, and reading it as two would over-count the
page by one.

## 7. Retraction: the 73 **are** a census figure

> **Correction, 2026-09-25 (issue #707).** Issue #707's text asserted that "the
> 73 are not a census figure", and that assertion is **wrong**. All 73 carry
> census rows in `xdata-registers.csv` with `spelled_as = pair-literal`; §2b
> measures 196 references across them. The wrong sentence is left here in the
> form it was filed so the claim and its correction stay together.
>
> The distinction the issue was reaching for is a different one, and it is real:
> the 73 are a census figure *and* a byte-scan figure, and **which method
> produced a number is not recorded in the census CSV**, because `scan()` folds
> the seed and its `+1` into one `pair-literal` row. A reader asking "which of
> the 214 are only the `inc DPTR` half" cannot answer it from the committed
> table at all, which is the gap `inc_dptr_sites.py` closes. `xdata-0400-045f.md`
> §4 and `xdata-register-map.md` §4.7 said "they have census rows and no
> `registers.yaml` entry", which was and is correct; nothing in the tree needed
> retracting, and the phrase "not a census figure" appeared only in the issue.

**`mov_dptr_main_ec = 0` is "not found by this method", never "absent".** It is
what `trace_xdata_refs.py` found by a byte scan of the committed image, over the
three regions the page's rule is written against. Two of the 73 are not even
zero file-wide -- `0x043B` and `0x04A5` have pd-image sites -- and the columns
are split so that stays visible rather than being summed away.

The same eleven bytes, confirmed through a second entry point rather than only
through the tool that made the list:

```console
$ python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 \
        0x0309 0x0311 0x0313 0x0317 0x031B 0x0333 0x0337 0x0341 0x0346 0x034F \
        0x0647 --counts-only
0x0309: 0 direct MOV DPTR site(s)  none
0x0311: 0 direct MOV DPTR site(s)  none
0x0313: 0 direct MOV DPTR site(s)  none
0x0317: 0 direct MOV DPTR site(s)  none
0x031B: 0 direct MOV DPTR site(s)  none
0x0333: 0 direct MOV DPTR site(s)  none
0x0337: 0 direct MOV DPTR site(s)  none
0x0341: 0 direct MOV DPTR site(s)  none
0x0346: 0 direct MOV DPTR site(s)  none
0x034F: 0 direct MOV DPTR site(s)  none
0x0647: 0 direct MOV DPTR site(s)  none
```

## 8. What this does not establish

- **Nothing was observed on hardware.** No byte was read back, no write
  accepted, no capture taken. Every claim here is about committed bytes in the
  image and committed text in the decompiled tree.
- **No `status:` moved, and none was invented.** `registers.yaml` is unchanged;
  the file is not in this pass's diff at all. The `status:` vocabulary is not
  extended, and no entry was added or removed.
- **A resolved site is a static access.** It is not evidence the EC acts on the
  byte, that the byte is a register, or that any two sites agree about the
  value. The direction is the accessor's body, which is stronger than reading an
  `=` in the caller and weaker than knowing what the pair is for.
- **"No site" is "not found by this method".** A computed DPTR, a
  register-indirect access and a table lookup are all invisible to
  `trace_xdata_refs.sites_for`, and `0x0440`'s three-record writer is this
  repository's own worked example of a byte with no `MOV DPTR` site that the
  firmware writes anyway (`xdata-0440-readers.md`).
- **The census is a lower bound on the machine code** and, over overlapping
  exports, an upper bound on it. 196 references is what the decompiled text
  says, not what the firmware does.
- **The 107 is what the committed export resolves.** A call site the exporter
  dropped, or a decompiler that spelled an address some other way again, is out
  of reach, which is the reason `NOT_IN_TREE`'s vocabulary has no word for
  absence.
