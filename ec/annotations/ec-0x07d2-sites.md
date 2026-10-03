# `0x07D2` — the reference sites, enumerated

`0x07D2` is the byte the DSDT's ECMG field list steps over. That list reads
`Offset (0x7D0), DBD1, 8, DBD2, 8, Offset (0x7D3), , 4` and `GFID, 3`
(`evidence/acpi/dsdt.dsl:52248-52252`, quoted with the field names inline
because the line numbers move): `DBD1` is `0x07D0` and `DBD2` is `0x07D1`, so
the two 8-bit fields end where `0x07D2` begins, and the next `Offset` is
`0x7D3`. **This address is in no DSDT field at all** — not an unnamed field,
outside the list. It is absent from `windows/decompiled/v3.1.6.0/ECSpec.cs`,
no row in the service's `ec-callsites.csv` names it, and the only spelling any
committed input gives it is `DAT_EXTMEM_07d2`, this repository's generic
placeholder for an unnamed XDATA byte. So there is no DSDT name to borrow, no
vendor constant, and no committed writer anywhere. This file is the site-by-site
walk it has never had, in the shape
[`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) and
[`ec-0x07d1-sites.md`](ec-0x07d1-sites.md) got for the two addresses either side
of it.

**Read the headline before the tables.** Every site is in the `ITE8850-PD`
image at file `0x20000` — a second 8051 program with its own XDATA map. This
file therefore characterises *the PD firmware's variable at its XDATA `0x07D2`*,
which is not a byte the DSDT writes, because the DSDT does not write it at all.
Nothing below is evidence about what the EC does with its own `0x07D2`, and
nothing below makes writing that register any safer. §7.

Within the PD image the address does two different jobs, and §4 is the finding:
it is the low byte of a 16-bit quantity in nine of its sites, and a standalone
index in four others. `ec-0x07d1-sites.md` §4.3 declined to choose what the
`0x07D0`–`0x07D2` field is, and this walk does not overturn that; it shows why
the choice is hard, because both readings are real and they are in different
routines.

## 1. Reproducing the map

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07D2
0x07D2  refs=47    ec=0     pd=47    referenced in the PD image ONLY, not by the
EC   in_data_region=0   0x07D2

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D2 --counts-only
0x07D2: 47 direct MOV DPTR site(s)  pd-image=47

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D2 --csv \
          --terminator-column \
          > ec/annotations/ec-0x07d2-sites.csv
```

The trailing `terminator` column says which of the guards `walk_why()` stopped
on, so a window the instruction budget cut is not in the same shape as one that
stopped on a real terminator. The rows here that the budget truncates are
listed in `walk-budget-census.csv` and counted by
`../../ec/tools/walk_budget_census.py`; the write-up is
`../../docs/findings/walk-window-terminators.md`.

That is the reconciliation this file rests on, and it is the same one
`ec-0x07d1-sites.md` §1 rests on: the enumerated rows are the ones
`registers.yaml` (`static_refs`/`static_refs_main_ec`/`static_refs_pd_image`
= 47/0/47) quotes, their per-region counts sum to it, and
`check_register_counts.py` re-derives all three from the image, so the site
table cannot silently disagree with the number everything else cites.
`static-refs-audit.md` §6 is *not* part of that for this address — that
section is the write-up of `0x07D1`'s own addition to the register file and
carries no `0x07D2` row; `ec/annotations/` has no generated table for this
address that needed one.

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d2-sites.csv')))
print(collections.Counter(r['region'] for r in rows))
print(len({r['file_offset'] for r in rows}), 'distinct file offsets')"
Counter({'pd-image': 47})
47 distinct file offsets

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
```

The per-region split is the load-bearing half of that. A bare `refs=47` adds the
two programs' address spaces together and reads as an EC-side count;
`pd-image: 47` with the EC column at 0 is what makes the row a PD-image finding.
This is the conflation §3a of `../../docs/findings.md` records, and `pd-image`
is the column that prevents it.

**The other census indexes a different unit, and the two figures do not
conflict.** `xdata-registers.csv`'s `0x07D2` row reports 53 references, against
47 here. That file attributes each reference to the *enclosing named function*
— it reads the decompiled C, not the byte stream — where this walk records the
*site address* where `MOV DPTR,#0x07D2` appears. The two agree under one number
when a routine's `MOV DPTR` is its own first instruction (`0x8D41`,
`0xB311`, `0xC755` each appear in both under the same address), and under two
when it is a few bytes in: `0xF61C` is the function entry and `0xF628` is its
only site; `0x8A4A` is the entry and `0x8B70`, `0x8B81` and `0x8BAD` are its
sites. `0xA571` looks like the exception and is not — that export ends on
`jnz 0xA5B4`, a fall-through into `0xA5B3`, so `dispatch_on_state_07d0` and
`and_16bit_fields_write_07d2_07d3` are one routine split across two export
chunks. The reconciliation is the indexing unit, not a method reaching
different bytes, and no figure here is corrected to match the other.

**A third committed artefact already groups these two bytes as one unit.**
`xdata-clusters.csv` carries `pd-016` over `addrs` `0x07D2 0x07D3`, and its
`shared_functions` cell names the five routines that reference *both* — `0x8A4A`,
`0xA571`, `0xA5B3`, `0xC755` and `0xF61C`. Four of those are where §4.2's walks
live, and the fifth is the `0xA571` export boundary above, which is the same
routine as `0xA5B3`. That census clusters by co-occurrence and knows nothing
about this file's question; it put these two addresses in one bucket before
either was walked. It corroborates the pairing, not the direction §4.3 declines
to fix.

`register_ref_table.py` reaches the same split by an independent path, and its
`0x07D2` row exists only because the entry in `registers.yaml` does — the tool
tabulates addresses that file already names:

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1 \
  | grep -E '0x07D0|0x07D1|0x07D2'
| `0x07D0` | `DBD1` | 254 | 0 | 254 | 157 | 8 | 2 | 0 | 0 | 72 | 7 | 0 | 0 | 8 |
| `0x07D1` | `DBD2` | 76 | 0 | 76 | 46 | 13 | 0 | 0 | 0 | 14 | 3 | 0 | 0 | 0 |
| `0x07D2` | `DAT_EXTMEM` | 47 | 0 | 47 | 31 | 8 | 2 | 0 | 0 | 5 | 0 | 0 | 0 | 1 |
```

(columns after `jmp` are `handoff->read`, `handoff->write`, `handoff->r+w`,
`handoff->unresolved`, `none`.) Net: **37 of the sites read the byte and 10
write it** — the 37 being the 31 read at the site, the 5 handoffs, which
resolve one level deeper and all read, and the one `none` row, which §5 decodes
by hand and turns out to read as well.

The opcode tables the decode rests on are pinned by a self-test against the two
windows `charge-profile-flow.md` transcribed from r2 by hand, and the
load-bearing decodes below **were** produced by `r2 -a 8051` on a flat dump of
the PD image, which agrees with `disasm8051.py` at every one of them — the nine
`inc dptr` walks (§4.2), the four multiplies (§4.1), the five handoff callees
(§3) and the framing outliers (§5):

```console
$ python3 ec/tools/disasm8051.py --self-test
self-test passed: both charge-profile-flow.md windows decode identically, all 4
relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode
as transcribed

$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8bad; pd 6' /tmp/pd.bin
            0x00008bad      9007d2         mov dptr, #0x07d2
            0x00008bb0      e0             movx a, @dptr
            0x00008bb1      fc             mov r4, a
            0x00008bb2      a3             inc dptr
            0x00008bb3      e0             movx a, @dptr
            0x00008bb4      4401           orl a, #0x01
```

## 2. Where they are

All in the PD image, and clustered rather than spread. The `0x07D0` walk
reached eleven of the image's 4 KiB pages, `0x07D1` nine, and this one nine —
and none of the three sets is nested in another.

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d2-sites.csv')))
h = collections.Counter(int(r['runtime'], 16) >> 12 for r in rows)
print('  '.join(f'0x{k:X}xxx:{v}' for k, v in sorted(h.items())))"
0x3xxx:4  0x4xxx:5  0x6xxx:10  0x7xxx:1  0x8xxx:11  0xAxxx:6  0xBxxx:2  0xCxxx:7  0xFxxx:1
```

The differences run in both directions. This address reaches `0x6xxx` and
`0xCxxx`, which `0x07D1` never touches, and it never reaches `0x9xxx` or
`0xDxxx`, which `0x07D1` does, and it is the only one of the three to reach
neither `0x5xxx` nor `0xExxx` (`0x07D0` reaches both). So the three addresses
are not three samplings of one footprint.

Every one of these sites is a distinct offset, which is the "distinct sites, not
one function called repeatedly" answer `ec-0x07d1-sites.md` §2 reached for its
address. The same qualifier applies: distinct sites are not independent logic.
5 of them hand DPTR to a shared accessor routine (§3), 9 walk into `0x07D3`
(§4.2), and several sit in one routine — the `0xC755` export alone contains
seven.

## 3. What the sites do

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d2-sites.csv')))
k = collections.Counter()
for r in rows:
    a = r['access']
    k['handed to a helper' if a.startswith('DPTR handed') else
      'read-modify-write' if 'read' in a and 'write' in a else
      'read' if 'read' in a else 'write' if 'write' in a else
      'no movx in window'] += 1
print(sorted(k.items(), key=lambda x: -x[1]))"
[('read', 31), ('write', 8), ('handed to a helper', 5), ('read-modify-write', 2),
('no movx in window', 1)]
```

| at the site | sites |
|---|---|
| reads it (`movx a,@dptr`) | 31 |
| writes it (`movx @dptr,a`) | 8 |
| hands DPTR to a subroutine — direction not resolvable at the site | 5 |
| read-modify-write | 2 |
| no `movx` in the decoded window | 1 |
| `movc a,@a+dptr` / `jmp @a+dptr` (CODE pointer) | 0 |

This is the same picture `ec-0x07d1-sites.md` §3 found for its address — a
read-mostly byte, with the `movc` and `jmp @a+dptr` columns at 0 as they are
there — but with two read-modify-writes where `0x07D1` had none and a
`no movx` cell where `0x07D1` had none either, which is what gives §5 and §6
real work here.

The 5 handoffs go to 5 distinct entry points. Decoding each callee's first
instructions resolves the direction one level deeper, and **all five read** —
unlike `0x07D1`, whose three write-handling callees included `0xACF4` and
`0xB18D`:

| helper | site | direction | first instructions (`disasm8051.py --at <0x20000+helper>`) | stride → base |
|---|---|---|---|---|
| `0x3509` | `0x6816` | read | `movx a,@dptr ; mov r7,a ; mov 0xf0,#0x5e ; mul ab ; add a,#0xf4` | `0x5E` → `0x08F4` |
| `0x3760` | `0x8D5C` | read | `movx a,@dptr ; mov dptr,#0x042c ; mov r7,a ; mov 0xf0,#0x60 ; ljmp 0x10bc` | `0x60` → `0x042C` |
| `0x34A5` | `0x8DBF` | read | `movx a,@dptr ; mov dptr,#0x0420 ; mov r7,a ; mov 0xf0,#0x60 ; lcall 0x10bc ; mov a,r7 ; ret` | `0x60` → `0x0420` |
| `0x365C` | `0x8E6B` | read | `movx a,@dptr ; mov r7,a ; mov 0xf0,#0x5e ; mul ab ; add a,#0xf3` | `0x5E` → `0x08F3` |
| `0xAD3F` | `0xC7C1` | read | `movx a,@dptr ; mov r3,a ; mov 0xf0,#0x17 ; mul ab ; add a,#0x31` | `0x17` → `0x0A31` |

Two of these are the `0x07D1` file's stride geometry reached from a third index
byte: `0x3509` resolves the same `0x5E` → `0x08F4` as `0x07D1`'s `0xB18D`, and
`0x34A5` and `0x3760` are the `0x60`-stride pair that reload DPTR with a
*different* structure base before multiplying, so the byte indexes `0x0420` /
`0x042C` and the caller's own DPTR is not what is scaled. `0x34A5` returns the
byte in `A` as well, so it both reads and hands the value back.

`0xAD3F` is the only callee of the five whose base, `0x0A31`, is in neither
`pd-access-strides.csv` nor `pd-base-strides.csv`. The other eight bases §4.1
reaches are already in one or both; this is a base those censuses have not
recorded, and recording their contents is `#75`'s, not this file's.

## 4. What the value is used as

### 4.1 The address arithmetic

Four sites carry the multiply inline, and the four are not all the same shape —
the fourth has no stride and no base at all.

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x24A6D --runtime 0x4A6D -n 6
0x4a6d  9007d2   mov  dptr,#0x07d2
0x4a70  e0       movx a,@dptr
0x4a71  ff       mov  r7,a
0x4a72  75f004   mov  0xf0,#0x04
0x4a75  ef       mov  a,r7
0x4a76  a4       mul  ab
```

`0x4A6D` reads the byte into `R7`, multiplies by `4`, writes the product
straight into `DPL` and the high half into `DPH` with `mov 0x83,0xf0` — there
is no `add a,#base`, so **DPTR is the byte scaled by four and nothing else**.
That is a pointer scale rather than a structure stride. It is worth being
precise about what is new in it, because a multiply with no base add is *not*
new to the trio: [`ec-0x07d0-sites.csv`](ec-0x07d0-sites.csv) carries one for
`0x07D0` at `0x98A1`, which reads the byte, multiplies by `0x0C` and hands the
16-bit product back in `R7`/`R6` without building a DPTR at all — that row is
in the table, though `ec-0x07d0-sites.md` does not discuss it. What is new here
is the last step: `0x4A6D` turns the product into the *address* rather than
returning it, where `0x98A1` leaves the choice to its caller. The other three
sites here are ordinary strides. `0x35FF` and `0x373C` are the same two
`0x5E`-stride multiplies `0x07D1` also uses, reached from this byte instead;
`0xC7A8` is the `0x17` stride. All four, with the eight bases they resolve
across this file and §3:

| site | stride | base | | source |
|---|---|---|---|---|
| `0x35FF` | `0x5E` | `0x08F6` | | inline |
| `0x373C` | `0x5E` | `0x08F7` | | inline |
| `0xC7A8` | `0x17` | `0x0A2A` | | inline |
| `0x4A6D` | *none* | *none* | | inline; `DPTR = 4 × value` |
| `0x3509` | `0x5E` | `0x08F4` | | §3 callee |
| `0x365C` | `0x5E` | `0x08F3` | | §3 callee |
| `0x3760` | `0x60` | `0x042C` | | §3 callee |
| `0x34A5` | `0x60` | `0x0420` | | §3 callee |
| `0xAD3F` | `0x17` | `0x0A31` | | §3 callee |

**The strides and bases are not new; the index that drives them is.** Every
base but `0x0A31` already appears in a committed census — `0x08F3`, `0x08F4`,
`0x08F6` and `0x08F7` in the `0x5E,access` row of `pd-access-strides.csv`,
`0x08F3`, `0x08F4` and `0x08F6` also in the `0x5E` row of
`pd-base-strides.csv`, `0x0A2A` in the `0x17,construction-only` row of the
former, and `0x0420` and `0x042C` in the `0x60` row of the latter.
`pd-index-geometry.md` §7/§8 already decoded the `0x5E` and `0x17` sites behind
`0x07D0` and `0x07D1`; what moves this address out of that file's
`unresolved,anchor-access` bucket is naming the index, not the geometry. This
file records only *which* bases already appear there and leaves their contents
to `#75`.

Of the 37 read sites, 9 reach a multiply — 4 inline and 5 through a callee —
and **28 have no multiply in the decoded window**. That is the honest form of the
negative: not "not an index", because a linear walk stops at the first branch
and the multiply may be past it. `ec-0x07d1-sites.md` §4.1 makes the same point
in the same words, and `pd-xdata-overlap.md` §3 makes it about the `10BC`
family for `0x04A6`.

### 4.2 The nine `inc dptr` walks

Nine sites reach past their own byte, and nine is what the *table* records. §5
names a tenth site the walk's window stops short of; the code after its store
reaches a computed address rather than `0x07D3`, so it does not join this set.
**All nine put `0x07D2` in the low position** — none reads or writes it as the
second half of a pair, and the one that runs to three bytes runs upward from it.
This is the strongest single piece of evidence in the file, and it is evidence
about one direction only.

| site | what it does | reaches |
|---|---|---|
| `0x8B70` | `orl a,#0x08` on `0x07D2`, then `inc dptr`, read, write it back unchanged | `0x07D3`, identity store |
| `0x8B81` | read `0x07D2`, write it back unchanged, then `inc dptr`, `orl a,#0x02` | `0x07D3`, bit 1 |
| `0x8BAD` | `mov r4,[0x07D2]`, then `inc dptr`, `[0x07D3] | 0x01` into `R5` — **stores nothing** | `0x07D3`, into `R5` |
| `0xA5DD` | store `R6` to `0x07D2`, `inc dptr`, store `R7` to `0x07D3` | `0x07D3`, one 16-bit store |
| `0xA61C` | `mov r5,[0x07D2]`, `inc dptr`, `[0x07D3]`, `xch a,r5`, `mov B,r5`, `lcall 0x9920` | `0x07D3`, as a 16-bit operand |
| `0xA660` | `inc dptr` **first**, read `0x07D3` into `R7`, `lcall 0xEEAE` | `0x07D3` only |
| `0xC755` | store `R7` to `0x07D2`, `inc dptr`, store `R5` to `0x07D3`, call `0xAD67`, store `R5` again | `0x07D3`, one 16-bit store |
| `0xC780` | `mov r7,[0x07D2]`, `inc dptr`, `mov r5,[0x07D3]`, `lcall 0xEE68` | `0x07D3`, as `R7:R5` |
| `0xF628` | store `R7` to `0x07D2`, `inc dptr`, store `R5` to `0x07D3`, `clr a`, `inc dptr`, store `0` | `0x07D3` **and `0x07D4`** |

All nine sit inside a routine `ec/decompiled/pd` names, and the committed `.asm`
listings say more than the CSV windows do. `0x8A4A` holds the three bit
operations, `0xA5B3` holds `0xA5DD`, `0xA61C` and `0xA660`, `0xC755` holds itself
and `0xC780`, and `0xF61C` holds `0xF628`.

Two accessors outside that set decide the question, and they are nine bytes
apart. `0xAD83` is `read_07d1_07d2_into_r7_r5` — `0x07D1` into `R7`, `inc dptr`,
`0x07D2` into `R5` — the little-endian load `ec-0x07d1-sites.md` §4.3 already
decoded from the other side, and it is *not* itself one of the nine, because its
`MOV DPTR,#0x07D1` is at its own entry and the `0x07D2` read belongs to the entry
nine bytes later. That entry is `0xAD8C` `read_07d2_into_r7_r5_zero`: read `0x07D2`
into `R7`, **clear `R5`**. One loading the pair and one loading the high half with
the low half zero-extended, from adjacent addresses — the pair is the unit, and
`0x07D2` is its high byte *in that window*.

`0xC755` `latch_07d2_07d3_then_zero_23bytes` opens with the `R7`/`R5` store in
this table and then reads `0x07D2` back three times, dispatching on the byte
value through `0xB73F`, `0xE15A` and `0xB9A1`, and calls `0xAD8C` three more
times paired with `0xD83D`, `0xD013` and `0xF65E`.

**Two routines set the high byte and then read the pair back.** `0x7580`
`set_07d2_and_return_r7_zero_or_one` and `0xB311` `write_07d2_then_dispatch_on_07d1`
open with the same three instructions — `mov DPTR,#0x07D2 ; mov A,R5 ; movx
@dptr,a` — so this byte is a *destination* at both, not only a source. Each then
points DPTR at `0x07D1` and calls `0xACF4`, which
[`ec-0x07d1-sites.md`](ec-0x07d1-sites.md) §3 decodes as that address's one
write-handling callee. Each loads the immediate pair `R2 = 0x11`, `R3 = 0x94`
into the call `0x775C` makes, and `0xB311` increments `R5` on the way past —
`inc R5` at `0xB322`. That is visible in the committed listing rather than in
the table's own window, and it is the only place a named routine advances a
value destined for this byte; like `0x07D0`, which
`ec-0x07d0-sites.md` §4 records at two of its sites, this address is **never
incremented in place** — a search of the three committed site tables for an
`inc` reaching a store returns `0x07D0`'s rows and none of this file's. After
the compare, `0x7580` calls `0xAD83`, which is the `0x07D1`/`0x07D2` word load of
the paragraph above.

The `0x9411` pair is worth naming on its own. `ec-0x07d1-sites.md` §4.3 records
`0x3E91` storing the literal `0x07D1 ← 0x11`, `0x07D2 ← 0x94`, "so the value
`0x9411`". Here the same 16 bits appear as an operand pair in two further
routines. Three appearances of one constant that is only meaningful if the two
bytes are read as halves of a number is not something a coincidentally-adjacent
pair of variables produces on its own — and it is still not a naming of the
field, which §7 leaves to `#26` and `#67`.

**A 16-bit window in the other direction, and a third length.** `0x8A4A`
`dispatch_on_07d1_bits_then_update_07d1_07d2` opens by storing `R7` to `0x07D1`
and then clearing `0x07D2` *and* `0x07D3` — three bytes moved together, which is
what `ec-0x07d1-sites.md` §4.3 records and this file confirms from the other
side. And `0xA5B3` `and_16bit_fields_write_07d2_07d3` stores an `R6`/`R7` pair
to `0x07D2` then `0x07D3` at `0xA5DD`, and later at `0xA605` reads `0x07D2` and
**only if it is zero** does it `inc dptr` and read `0x07D3` — the `0xAD8C`
idiom written inline.

### 4.3 The verdict

> On the PD side `0x07D2` is both: all nine of its `inc dptr` walks put it in the
> low position of a 16-bit — or, at `0xF628`, 24-bit — window with `0x07D3`,
> while four sites multiply it into an address on its own, so the address is a
> word's low byte in some routines and a standalone index in others, and no
> single reading of it holds everywhere.

That is the finding, and it is deliberately not one of the two the framing
offered. The 16-bit reading predicts only the first half and the three stride
multiplies predict only the second; the sites support both, so the choice the
framing poses is not well posed. `ec-0x07d1-sites.md` §4.3's refusal to choose
between a 3-byte counter, a packed field and a moved 16-bit value **survives**
this walk and is not overturned by it: `0x8A4A` clears three bytes at once,
`0xAD83`/`0xAD8C` load one or two, and `0x35FF`/`0x373C`/`0x4A6D`/`0xC7A8`
multiply it alone — and the site-by-site table is what tells those apart, which
is the most this method can deliver. Naming the field is `#26` and `#67`.

## 5. Are all these real instructions?

`scan_refs.py` counts the byte pattern `90 07 D2` with no instruction
alignment, so in principle some hits are operand bytes inside other
instructions or bytes inside a data table. `disasm8051.py --converge` reports
*evidence*, not a verdict: it decodes linearly from each of the bytes preceding
a site and counts how many walks land exactly on it versus step over it.

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d2-sites.csv')))
print(collections.Counter('syncs from every anchor' if r['frame_over'] == '0' else
      'syncs from none' if r['frame_onto'] == '0' else 'mixed' for r in rows))"
Counter({'syncs from every anchor': 34, 'mixed': 13})
```

No site here is unsynced from every preceding anchor. The 13 `mixed` rows are
the ordinary case for a walk that steps over the `lcall 0x104D` inline-argument
idiom, the full decode of which is in `ec-0x07d0-sites.md` §5 and
[`pd-inline-arg-trampoline.md`](../../docs/findings/pd-inline-arg-trampoline.md);
`0xC7C9` in this file's own window is one of them.

**The one `no movx` row is the walk stopping, not the site being inert.** The
classifier's guard is a flow opcode, and for `0x6757` the instruction after
`MOV DPTR,#0x07D2` is `cjne a,#0x02` — so the window is one branch long and has
no `movx` in it. The bytes above and below say what the site does:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x26753 --runtime 0x6753 -n 8
0x6753  9007f9   mov  dptr,#0x07f9
0x6756  e0       movx a,@dptr
0x6757  9007d2   mov  dptr,#0x07d2
0x675a  b40208   cjne  a,#0x02,0x6765
0x675d  1237de   lcall 0x37de
0x6760  7402     mov  a,#0x02
0x6762  f0       movx @dptr,a
0x6763  8006     sjmp 0x676b

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x237DE --runtime 0x37DE -n 9
0x37de  e0       movx a,@dptr
0x37df  75f05e   mov  0xf0,#0x5e
0x37e2  a4       mul  ab
0x37e3  24f5     add  a,#0xf5
0x37e5  f582     mov  0x82,a
0x37e7  e4       clr  a
0x37e8  3408     addc a,#0x08
0x37ea  f583     mov  0x83,a
0x37ec  22       ret
```

`0x6757` is inside `0x6673` `dispatch_on_07f5_record_after_staging_07d2`, and
both arms of its `cjne` call `0x37DE` before they store anything. That callee
opens with `movx a,@dptr`, so the byte is **read**, and it then rebuilds DPTR
out of the value it read, leaving it at `0x08F5 + 0x5E*[0x07D2]`. Each arm's
`movx @dptr,a` therefore stores to *that* address — `0x02` when `[0x07F9]` is
2, `0x01` otherwise — and `0x07D2` is not the byte either store reaches.

`0x37DE` is the `0x5E`-stride shape of §3's `0x3509` one base along, and like
those five it is a callee that replaces DPTR rather than using the one it is
given. It is not among §3's five only because the classifier scored this row
`no movx` rather than `handed to a helper`, so §3's table does not reach it.

So what this method's `no movx` cell records here is that the walk stopped
before reaching the access — a different statement from "no access happens
here" — and the direction the bytes give is a read.

**And `0x8D41` is a store the table's window cuts in half.**
`advance_07d2_counter_and_dispatch` opens by storing `R7` to `0x07D2` — a real
write, and not one of §4.2's nine. Everything after those three instructions
runs through callees that rebuild DPTR: `0x35AC` sets it to `0x0428`, `0x3632`
to `0x042F`, `0x3760` to `0x042C`, and `0x349B` and `0x3627` add to `DPH` and
`DPL`. So the `clr a` that follows reaches a computed cell rather than
`0x07D2`, and so does the `mov a,#0xff ; movx @dptr,a` after it.

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x28D41 --runtime 0x8D41 -n 15
0x8d41  9007d2   mov  dptr,#0x07d2
0x8d44  ef       mov  a,r7
0x8d45  f0       movx @dptr,a
0x8d46  1235ac   lcall 0x35ac
0x8d49  ef       mov  a,r7
0x8d4a  12349b   lcall 0x349b
0x8d4d  e0       movx a,@dptr
0x8d4e  fe       mov  r6,a
0x8d4f  ef       mov  a,r7
0x8d50  123632   lcall 0x3632
0x8d53  ef       mov  a,r7
0x8d54  12349b   lcall 0x349b
0x8d57  123627   lcall 0x3627
0x8d5a  e4       clr  a
0x8d5b  f0       movx @dptr,a
```

The `lcall 0x35FF` near the end is §4.1's `0x5E`-stride site, so it leaves DPTR
at `0x08F6 + 0x5E*[0x07D2]` and the `inc dptr` after it reaches
`0x08F7 + 0x5E*[0x07D2]` — not `0x07D3`. The byte read at `0x8D75` for the
`jnb acc.7` at `0x8D76` to test is that one.

So what the table's window cannot see here is not a further `0x07D3` walk but
the call chain: the window for `0x8D41` stops three instructions in, on the
`lcall 0x35AC` that immediately follows the store, and every later access in the
routine is at an address only those callees produce. That is §1's
`0x8D41`-versus-`0xF61C` entry split again, and the same blind spot §4c of
`../../docs/findings.md` retracted a claim over. It is why the nine of §4.2 are
"what this method found" and not a census of the walks that exist.

**The CODE-pointer blind spot, checked explicitly for this address.** `MOV
DPTR,#imm16` builds CODE pointers as well as XDATA ones, and the collision here
is the tightest of the three addresses: CODE `0x07D0` is the NUL terminator of
`"NaN"`, `0x07D1` is the `+` that starts `"+INF"`, and `0x07D2` is the **`I`
inside that same string** — three bytes into a live literal, where a table
pointer has no reason to stop but every reason to. The classifier names `movc`
and `jmp @a+dptr` separately precisely so this cannot hide, and both columns are
**0** for all 47. No site in this file is a table lookup in CODE.

**The two budget-truncated rows are named rather than smoothed over.** `0xC7A8`
and `0xF628` carry `terminator == max_insns (8) exhausted`, so their windows are
shorter than the code, and `walk_budget_census.py` records what a larger budget
would show. For `0xF628` that budget *does* change the answer, and the table now
carries the larger one: the committed cell reads `write x3, walks 3 consecutive
bytes (inc dptr)` because the budget-8 window stopped at the second `inc dptr`,
one instruction short of the third store. That cell is the one entry
`access_cell_corrections.py` holds for this table — the mechanism issue #865
introduced for exactly this case — so it is re-derived from the image at its
recorded budget rather than typed in, and `ec/decompiled/pd/F61C.asm` is the
second method: the export `store_r7r5_0_to_07d2_if_6faf_zero` carries all three
stores, which is how §4.2 reaches `0x07D4`. For `0xC7A8` the budget makes no
difference — its own eight instructions contain the whole multiply (`mul ab`,
`add a,#0x2a`, `addc a,0xf0`), so the truncation costs the DPTR-construction
tail, not the stride.

## 6. The bit operations, and the field boundary

Three sites OR a single bit into the byte they load rather than replacing it, and
they are all in `0x8A4A`'s routine. The write-up that matters is the one about
what they span, because the two natural readings of the question are not equally
true.

| site | instruction | byte | bit |
|---|---|---|---|
| `0x8B70` | `orl a,#0x08` | `0x07D2` | 3 |
| `0x8B81` | `orl a,#0x02` | `0x07D3` | 1 |
| `0x8BAD` | `orl a,#0x01` | `0x07D3` | 0 |

Two of the three store what they set. `0x8B70` sets bit 3 of `0x07D2` and writes
it back; `0x8B81` reads `0x07D2`, writes it back unchanged, then after the
`inc dptr` sets bit 1 of `0x07D3` and writes that. So the firmware sets bit 3 of
`0x07D2` and bit 1 of `0x07D3` — a field that **straddles the byte boundary**,
written by two separate instructions rather than one. **They do not form the
DSDT's unnamed bit field**, and saying they did would be wrong twice over. The
ECMG field list draws its next `Offset` at `0x7D3`, so `0x07D2` is outside the
list entirely (§1), while bits 3:0 of `0x07D3` *are* inside the unnamed 4-bit
run that the list gives as `Offset (0x7D3), , 4` before `GFID, 3`. The firmware
therefore spans a field boundary the ASL draws one byte earlier: the two halves
of the bit field are in different named regions on the DSDT side and in one
instruction sequence on the firmware side.

`0x8BAD` is the third `orl` and **stores nothing**, as §4.2's table and the
committed row's `read x2` with no `write` already record. Its `orl a,#0x01` goes
into `A` and on into `R5`, beside `R4` holding `[0x07D2]`, and the pair is handed
to `0xDC29`, which writes `R4` to `0xFFFE` and `R5` to `0xFFFF`. So it is
evidence that the firmware treats the two bytes as one unit, not a third write
to this field: the field-boundary claim rests on the two sites that store.

Two of the three also carry a store that changes nothing. At `0x8B70` the byte at
`0x07D3` is read and written back unmodified, and at `0x8B81` the byte at
`0x07D2` is — which is why the classifier scores both rows `read x2, write x2`
while only one real bit of each is set. So each of those two rows carries a write
that stores the value it just read, and the `write` half of them should not be
read as two more writes to this byte.

**This is the PD side only.** The EC side of `0x07D3` is `#183`'s, in
`ec-07c4-07d5-sites.md`, and nothing here says anything about it. That file and
this one share an address and a firmware; they do not share a program.

## 7. What this does not establish

- **Nothing about the EC's `0x07D2`.** The byte the DSDT steps over lives in
  the main EC image's XDATA, which references `0x07D2` zero times by this
  method. These are a different program's variable, and a PD-image walk cannot
  move an EC-side grading. The new `registers.yaml` entry carries
  `unknown-not-absent` and its note says so in those terms; `present-untested`
  is not available to it because `static_refs_main_ec` is 0, which is rule 2 of
  that file's header and the reason `0x07CC` was re-graded.
- **The entry carries no `DO-NOT-WRITE-BLIND` suffix, and that is not an
  invitation.** The suffix's declared warrant is a byte Windows demonstrably
  writes with no traceable EC-side handler. The DSDT does not name `0x07D2` at
  all, so there is no committed writer to warn about — which is a statement
  about the inputs, not about the safety of writing it. No tool here writes it,
  no value for it is known, and its meaning is open.
- **The walk's `no movx` cell is a method artefact, not a measurement.**
  `0x6757` is a read (§5): the `0x37DE` helper it hands the byte to reads it and
  rebuilds DPTR around the value, so the two stores visible after the branch
  reach a computed address and not `0x07D2`. The cell names no access where one
  is reached, and by the site rather than by its callee. Nothing about the
  other 46 rows is thereby in doubt; they each carry an access in their own
  window.
- **47 is a lower bound, and a zero would have meant "not found".**
  `trace_xdata_refs.py` finds direct `MOV DPTR,#imm16` sites only. Anything
  reaching the byte through a computed DPTR — a register-held address, a table
  of pointers, an indirect `movx @a+dptr` or `movx @r0` — is invisible to it.
  That blind spot is the one §4c of `../../docs/findings.md` retracted a claim
  over, and it is why "47 sites" and "the PD firmware references this byte 47
  times" are not the same sentence.
- **"47" is what this method found, not what the firmware does with the byte.**
  Nor is it a count of distinct decisions: 5 sites hand DPTR to 5 shared
  accessors, 9 walk into `0x07D3`, and several sit inside one routine.
- **Nothing observed on hardware.** No register was read back, no write was
  attempted, nothing was run on the machine. This is static analysis of a
  committed firmware image and that is all it is. In particular §4.3 says the
  PD firmware treats these bytes as neighbours; it does not say the EC does, or
  that writing one would produce any of it.
- **No control-flow recovery.** `disasm8051.py` decodes linearly and stops at
  the first branch; "47 distinct sites" counts *static* sites and says nothing
  about how many execute, how often, or in what order. The `0xA571`/`0xA5B3`
  export boundary in §1 is a direct instance of a linear walk's blind spot.
- **The handoffs are resolved one level only.** All five read, and none hands
  DPTR on again at depth 1, but depth 2 is not attempted.
- **What the windows mean is not identified.** §4.2 establishes that `0x07D2`
  participates in a 16-bit window with `0x07D3` and in 24-bit clears with
  `0x07D3`/`0x07D4`, and §4.3 declines to choose between the readings that is
  consistent with. What the indexed arrays contain is likewise unrecorded, as
  it is for `0x07D0` and `0x07D1`.
- **Nothing from the Windows side was re-derived here.** The absence of an
  `ECSpec` constant and of an `ec-callsites.csv` row is cited as it stands from
  the `registers.yaml` entry; no anti-tamper-protected method body was involved
  (`../../windows/antitamper/README.md`).

## 8. What would settle the rest

There is no prepared door procedure for this byte, and there is a reason rather
than an omission: the DSDT names `0x07D0` and `0x07D1` as `DBD1`/`DBD2` and
`0x07D2` as nothing at all, so there is no committed writer to drive an
experiment from. The `GPU` door procedure
(`../../docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`, graded by
`grade_gpu_door.py`) captures `0x07C4`-`0x07D7` in one clock and so would
record this byte's movement under the same `Arg0 == 0x1173` branch that writes
`0x07D0` and `0x07D1`. It is `#184`'s procedure and this file does not extend
it; designing a dedicated one would mean inventing a writer for the ASL, which
is a different piece of work and is not proposed here.

Three questions this walk opened, and deliberately did not answer:

- **What is the `0x07D0`/`0x07D1`/`0x07D2`/`0x07D3` field, and why does one
  routine read `0x07D2` as a high byte and another multiply it alone?** §4.3
  states both and chooses neither. The call graph and the surrounding PD
  structures are `#26` and `#67`.
- **Does the bit field `0x8B70`/`0x8B81` sets have any DSDT
  counterpart at all?** §6 establishes that it straddles a boundary the ASL
  draws one byte earlier, which means there may be nothing to collide with. A
  live observation would say more than another static pass, and no live
  observation is possible from here.
- **Does the EC firmware read `0x07D2` at all?** The EC image references it zero
  times by this method, which is the §4c signal and not a verdict.