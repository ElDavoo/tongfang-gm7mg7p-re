# `0x07D1` — the 76 reference sites, enumerated

`0x07D1` is `DBD2` in the DSDT's ECMG field list and has no vendor constant
at all: it is absent from `windows/decompiled/v3.1.6.0/ECSpec.cs` and no row
in the service's `ec-callsites.csv` names it, so nothing in the committed
Windows stack writes it. It is also the second half of the pair the DSDT's
`T1WR` `Arg0 == 0x1173` branch writes alongside `0x07D0` — `Arg1 * 8` into
`DBD1`, `Arg2 * 8` into `DBD2` (`evidence/acpi/dsdt.dsl:50685-50688`, field
list at `:52248-52250`). This file is the site-by-site walk its EC-side
counter part has and it does not: 76 direct `MOV DPTR` references, where each
one is, what the bytes around it do, and whether the two halves of the DSDT
pair are the same kind of PD variable.

**Read the headline before the tables.** All 76 sites are in the `ITE8850-PD`
image at file `0x20000` — a second 8051 program with its own XDATA map, per
`lightbar-bat-flow.md` §2. This file therefore characterises *the PD
firmware's variable at its XDATA `0x07D1`*, which is not the EC register the
DSDT writes; they share a number and nothing else. Nothing below is evidence
about what the EC does with its own `0x07D1`, and nothing below makes writing
that register any safer. `registers.yaml` keeps
`unknown-not-absent-DO-NOT-WRITE-BLIND` and this file does not move it. See §7.

Within the PD image the picture is consistent: a byte read at 60 of its 76
sites, written at 16, and used as a multiplier against structure strides
(`0x5E` and `0x17`) to index arrays — the same shape
[`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) found for `0x07D0`, with one
structural addition the `0x07D0` half shares rather than lacks (§4.3). "The
shape of an index" is the claim; naming what it indexes would be a guess and
is not made.

## 1. Reproducing the map

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07D1
This dump holds two 8051 programs; ec= counts sites in the EC firmware
(common area + CODE banks), pd= sites in the separate ITE8850-PD image,
whose XDATA map is unrelated. A pd-only count is not EC-side evidence.
A zero means 'not found by this scan', never 'absent' -- see the
indirect-addressing blind spot in docs/findings.md.

0x07D1  refs=76    ec=0     pd=76    referenced in the PD image ONLY, not by the EC   0x07D1

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D1 --counts-only
0x07D1: 76 direct MOV DPTR site(s)  pd-image=76

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D1 --csv \
          --terminator-column \
          > ec/annotations/ec-0x07d1-sites.csv
$ tail -n +2 ec/annotations/ec-0x07d1-sites.csv | wc -l
76
```

The trailing `terminator` column says which of the five guards
`walk_why()` can stop on ended this row's window, so a window the
instruction budget cut is not in the same shape as one that stopped on a
real terminator. This file's rows that the budget truncates are listed in
`walk-budget-census.csv` and counted by `../../ec/tools/walk_budget_census.py`;
the write-up is `../../docs/findings/walk-window-terminators.md`.

That is the reconciliation check this file rests on, and it is the same one
`ec-0x07d0-sites.md` §1 rests on: the enumerated rows are the 76 that
`registers.yaml` (`static_refs`/`static_refs_main_ec`/`static_refs_pd_image`
= 76/0/76) and `static-refs-audit.md` §6 both quote, and their per-region
counts sum to it, so the site table cannot silently disagree with the number
everything else cites.

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d1-sites.csv')))
print(collections.Counter(r['region'] for r in rows))
print(len({r['file_offset'] for r in rows}), 'distinct file offsets')"
Counter({'pd-image': 76})
76 distinct file offsets

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
69 entries / 101 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

The per-region split is the load-bearing half of that. A bare `refs=76` would
add the two programs' address spaces together and read as an EC-side count;
`pd-image: 76` with the EC column at 0 is what makes the row a PD-image
finding. This is the conflation §3a of `../../docs/findings.md` records, and
`pd-image` is the column that prevents it.

`ec-0x07d1-sites.csv` is committed next to this file; every table below is
derived from it, and each one names the command that re-derives it. The
opcode tables the decode rests on are pinned by a self-test against the two
windows `charge-profile-flow.md` transcribed from r2 by hand:

```console
$ python3 ec/tools/disasm8051.py --self-test
...
self-test passed: both charge-profile-flow.md windows decode identically and all 4 relative-branch sites resolve as hand-decoded
```

Unlike [`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) §1, some of the load-bearing
decodes here **were** produced by `r2 -a 8051` on a flat dump of the PD image,
and r2 agrees with `disasm8051.py` at every one of them — the 16-bit pair
shapes (§4.3), the eight inline stride multiplies (§4.1), the handoff callees
(§3) and the framing outliers (§5). That file's parenthetical claim that
radare2 is absent from the runner was corrected in place there; the commands
here are:

```console
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x3e6f; pd 10' /tmp/pd.bin
            0x00003e6f      9007d0         mov dptr, #0x07d0
            0x00003e72      123539         lcall 0x3539
            0x00003e75      ef             mov a, r7
            0x00003e76      12349b         lcall 0x349b
            0x00003e79      e0             movx a, @dptr
            0x00003e7a      fd             mov r5, a
            0x00003e7b      a3             inc dptr
            0x00003e7c      e0             movx a, @dptr
            0x00003e7d      9007d1         mov dptr, #0x07d1
            0x00003e80      cd             xch a, r5
            0x00003e81      f0             movx @dptr, a
```

## 2. Where the 76 are

All in the PD image, and clustered rather than spread: the `0x07D0` walk
reached eleven of the image's 4 KiB pages, this one reaches nine, and the two
sets are not nested.

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d1-sites.csv')))
h = collections.Counter(int(r['runtime'], 16) >> 12 for r in rows)
print('  '.join(f'0x{k:X}xxx:{v}' for k, v in sorted(h.items())))"
0x3xxx:2  0x4xxx:1  0x7xxx:18  0x8xxx:15  0x9xxx:5  0xAxxx:15  0xBxxx:10  0xDxxx:7  0xFxxx:3
```

76 distinct file offsets, from PD runtime `0x3E7D` to `0xF713`. Seven pages
are shared with `0x07D0`'s set, and the two differences run in both
directions: this address never reaches the four pages `0x5xxx`, `0x6xxx`,
`0xCxxx` and `0xExxx` that `0x07D0` does, and it reaches `0xBxxx` and
`0xFxxx`, which hold 13 of its 76 sites between them, where `0x07D0` reaches
neither. So the two addresses are not two samplings of one footprint.

Every one of this set's 76 sites is a distinct offset, which is the "254
distinct sites, not one function called repeatedly" answer
`ec-0x07d0-sites.md` §2 reached for its address. The same qualifier applies:
distinct sites are not independent logic. 17 of them hand DPTR to one of 8
shared accessor routines (§3), and 4 sit immediately after a repeated call
idiom (§5).

## 3. What the sites do

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d1-sites.csv')))
k = collections.Counter()
for r in rows:
    a = r['access']
    k['handed to a helper' if a.startswith('DPTR handed') else
      'read-modify-write' if 'read' in a and 'write' in a else
      'read' if 'read' in a else 'write' if 'write' in a else
      'no movx in window'] += 1
print(sorted(k.items(), key=lambda x: -x[1]))"
[('read', 46), ('handed to a helper', 17), ('write', 13)]
```

| at the site | sites |
|---|---|
| reads it (`movx a,@dptr`) | 46 |
| hands DPTR to a subroutine — direction not resolvable at the site | 17 |
| writes it (`movx @dptr,a`) | 13 |
| read-modify-write | 0 |
| no `movx` in the decoded window | 0 |
| `movc a,@a+dptr` / `jmp @a+dptr` (CODE pointer) | 0 |

The 17 handoffs go to 8 distinct entry points, which is a far tighter
concentration than `0x07D0`'s 79 handoffs across 26 callees. Decoding each
callee's first instructions resolves the direction one level deeper: 14 of
the 17 call a routine that begins `movx a,@dptr`, and 3 call one that begins
by storing.

| helper | sites | direction | first instructions (`disasm8051.py --at <0x20000+helper>`) | stride → base |
|---|---|---|---|---|
| `0xACBF` | 5 | read | `movx a,@dptr ; mov 0xf0,#0x17 ; mul ab ; add a,#0x35` | `0x17` → `0x0A35` |
| `0xACF4` | 2 | **write** | `mov a,r7 ; movx @dptr,a ; mov 0xf0,#0x5e ; mul ab ; add a,#0xfc` | `0x5E` → `0x08FC` |
| `0xACB7` | 2 | read | `mov r0,0x04 ; mov r1,0x05 ; mov r2,0x06 ; mov r3,0x07` then the `0xACBF` body | `0x17` → `0x0A35` |
| `0xAD10` | 2 | read | `movx a,@dptr ; mov 0xf0,#0x5e ; mul ab ; add a,#0x04` | `0x5E` → `0x0904` |
| `0xACE4` | 2 | read | `movx a,@dptr ; mov r3,a ; mov 0xf0,#0x17 ; mul ab ; add a,#0x2d` | `0x17` → `0x0A2D` |
| `0xACD1` | 2 | read | `movx a,@dptr ; mov r7,a ; mov 0xf0,#0x17 ; mul ab ; add a,#0x2c` | `0x17` → `0x0A2C` |
| `0x972E` | 1 | read | `mov r0,0x04 ; mov r1,0x05 ; mov r2,0x06 ; mov r3,0x07 ; movx a,@dptr ; mov 0xf0,#0x17 ; mul ab ; ret` | `0x17`, no base add |
| `0xB18D` | 1 | **write** | `mov a,r7 ; movx @dptr,a ; mov 0xf0,#0x5e ; mul ab ; add a,#0xf4` | `0x5E` → `0x08F4` |

Two of these are mid-routine. `0xACB7` is four instructions ahead of `0xACBF`
and falls into it, and `0x972E` is the same shape in a different part of the
image — ordinary Keil tail-sharing, which is why the entry addresses are
unaligned-looking. `0x972E` is the one callee that hands back a bare product
in `A`:`B` without adding a base, so its caller's base is decided elsewhere
and is not recovered here.

`register_ref_table.py --callee-depth 1` reaches the same split by an
independent path, which is the cross-check §5.2 of `static-refs-audit.md`
gives the `0x07D0` row:

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1 \
  | grep -E '0x07D0|0x07D1'
| `0x07D0` | `DBD1` | 254 | 0 | 254 | 157 | 8 | 2 | 0 | 0 | 72 | 7 | 0 | 0 | 8 |
| `0x07D1` | `DBD2` | 76 | 0 | 76 | 46 | 13 | 0 | 0 | 0 | 14 | 3 | 0 | 0 | 0 |
```

(columns after `jmp` are `handoff->read`, `handoff->write`, `handoff->r+w`,
`handoff->unresolved`, `none`.) Net: **60 of the 76 sites read the byte and
16 write it, and none is left unresolved** — the `0x07D0` walk's 229/15/2/8
had eight sites a linear walk gave up on, and this one has none. The three
`handoff->write` cells are the `0xACF4` and `0xB18D` sites, which is where
the 16 write count comes from rather than the 13 at the sites themselves.

## 4. What the value is used as

### 4.1 The stride each read site multiplies against

Read sites overwhelmingly feed the byte into address arithmetic, in the
canonical Keil form `DPTR = base + value × stride`. Eight sites carry the
multiply inline:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x296E8 --runtime 0x96E8 -n 9
0x96e8  9007d1   mov  dptr,#0x07d1
0x96eb  e0       movx a,@dptr
0x96ec  ff       mov  r7,a
0x96ed  75f017   mov  0xf0,#0x17
0x96f0  a4       mul  ab
0x96f1  2413     add  a,#0x13
0x96f3  f582     mov  0x82,a
0x96f5  e4       clr  a
0x96f6  340a     addc a,#0x0a
```

`0xF0` is `B` and `0x82`/`0x83` are `DPL`/`DPH`, so that is: read the byte,
multiply by `0x17`, point DPTR at `0x0A13 + value × 0x17`. All eight, with
the two strides and the eleven bases they resolve:

| site | stride | base | | site | stride | base |
|---|---|---|---|---|---|---|
| `0x76F9` | `0x5E` | `0x08FC` | | `0x96E8` | `0x17` | `0x0A13` |
| `0x8B8B` | `0x5E` | `0x08E9` | | `0xACE1` | `0x17` | `0x0A2D` |
| `0x973C` | `0x5E` | `0x08FC` | | `0xAD2A` | `0x17` | `0x0A39` |
| `0xB344` | `0x5E` | `0x08F6` | | `0xACBF`/`0xACB7` (7 sites) | `0x17` | `0x0A35` |
| `0xB370` | `0x5E` | `0x08E8` | | `0xACD1` (2 sites) | `0x17` | `0x0A2C` |
| `0xACF4` (2 sites) | `0x5E` | `0x08FC` | | `0xACE4` (2 sites) | `0x17` | `0x0A2D` |
| `0xAD10` (2 sites) | `0x5E` | `0x0904` | | `0xB18D` (1 site) | `0x5E` | `0x08F4` |

**The strides and bases are not new; the index that drives them is.**
`pd-index-geometry.md` §7/§8 already decoded the `0x5E` and `0x77` sites
behind `0x07D0`, and every one of the eleven bases above is already in its
censuses — `0x08E8`, `0x08E9`, `0x08F6`, `0x08FC` and `0x0904` in the
`0x5E,construction-only` row of `pd-access-strides.csv`, `0x08F4` and
`0x08FC` in `pd-base-strides.csv`'s `0x5E` row, `0x0A13` and `0x0A2C` in the
`0x17,access` row, and `0x0A2D`, `0x0A35` and `0x0A39` in the
`0x17,construction-only` row. `0x07D1` sat in that file's
`unresolved,anchor-access` bucket; what moves it out is naming the index, not
the geometry. `0x17` is new to the *pair* — `ec-0x07d0-sites.md` §4 records
`0x07D0` using `0x5E`, `0x60` and `0x77` — but not to the PD image, which has
61 `0x17` construction sites of its own.

Of the 60 read sites, 22 reach a multiply (8 inline, 14 through a callee) and
**38 have no multiply in the decoded window**. That is the honest form of the
negative: not "not an index", because a linear walk stops at the first branch
and the multiply may be past it. `pd-xdata-overlap.md` §3 makes the same point
about the `0x10BC` family for `0x04A6`, and §5.3 of `static-refs-audit.md`
about the three EC-side `none` cells.

### 4.2 The writes

13 sites store at the site and 3 more do so through `0xACF4`/`0xB18D`. Most
store a value already in a register. Three shapes are worth naming:

- **`0x8662`/`0x866A`** are the two arms of one branch — store `R7` or store
  a cleared `A`, then fall through to `0x866E`, which reloads `0x07D1` and
  reads it back into `R7`. A set-or-clear followed immediately by a read-back.
  The `R7` being stored was itself read from `0x07D0` eight bytes earlier
  (§4.3), so this arm is a copy of `0x07D0` into `0x07D1`.
- **`0xF70B`** and **`0xF713`** are byte-identical five-instruction accessors
  eight bytes apart: `mov dptr,#0x07d1 ; mov a,r7 ; movx @dptr,a ; mov
  r7,#0x01 ; ret`. Two copies of the same setter, which is what a
  double-sized inlined accessor looks like.
- **`0x3E91`** stores a literal pair, and is the reason for §4.3.

`0x07D0` is incremented in place at `0xA678` and `0xDC20`
(`ec-0x07d0-sites.md` §4), which is what an index does. **This byte is
incremented nowhere in its 76** — a search of both committed CSVs for
`inc a ; movx @dptr,a` returns two rows, `0x07D0`'s, and none of this file's.
That is a real difference between the two, recorded in §6.

### 4.3 The `0x07D1`/`0x07D2` pairing, and what the single-byte class misses

Five of the 76 reach past their own byte through `inc dptr`, and four of those
five treat `0x07D1` and `0x07D2` as **one 16-bit little-endian quantity**.
The `read`/`write` class scores them as single-byte accesses, which is true of
the *first* `movx` and understates the rest.

Two of them are accessors for the pair. `0xAD83` and `0xB38E` have the same
body — read `0x07D1` into `R7`, `inc dptr`, read `0x07D2` into `R5` — which
loads the little-endian word with `R7` holding the low byte:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2AD83 --runtime 0xAD83 -n 5
0xad83  9007d1   mov  dptr,#0x07d1
0xad86  e0       movx a,@dptr
0xad87  ff       mov  r7,a
0xad88  a3       inc  dptr
0xad89  e0       movx a,@dptr
```

`0x3E91` is the literal store of such a word, `0x07D1 ← 0x11` and
`0x07D2 ← 0x94`, so the value `0x9411`, and `0x8A4A` writes `R7` to
`0x07D1` and clears `0x07D2` and `0x07D3`.

**`0x3E7D` is the interesting one, and the CSV's own window misreads it.**
The committed row says `xch a,r5 ; movx @dptr,a ; inc dptr ; mov a,r5 ;
movx @dptr,a`, which read alone looks like "store `R5` to both bytes". It is
not, because the walk in that row starts *after* the `MOV DPTR` and so misses
where `A` and `R5` came from. The real reading needs the instructions above
it, and `0x3E6F` above those is a `0x07D0` site in
[`ec-0x07d0-sites.csv`](ec-0x07d0-sites.csv):

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x23E6F --runtime 0x3E6F -n 9
0x3e6f  9007d0   mov  dptr,#0x07d0
0x3e72  123539   lcall 0x3539
0x3e75  ef       mov  a,r7
0x3e76  12349b   lcall 0x349b
0x3e79  e0       movx a,@dptr
0x3e7a  fd       mov  r5,a
0x3e7b  a3       inc  dptr
0x3e7c  e0       movx a,@dptr
0x3e7d  9007d1   mov  dptr,#0x07d1
0x3e80  cd       xch  a,r5
```

`A` holds `[0x07D0]` across the `inc dptr` and `R5` now holds `[0x07D1]`, so
`xch a,r5` swaps them: `A` becomes `[0x07D0]`, `R5` stays `[0x07D1]`. The two
stores that follow put `A` at `0x07D1` and `R5` at `0x07D2`. **This is a
16-bit little-endian right shift of the two bytes at `0x07D0`/`0x07D1` into
`0x07D1`/`0x07D2`** — the sequence only makes sense if the firmware treats
`0x07D0`, `0x07D1` and `0x07D2` as one contiguous field it slides around.

That is the load-bearing decode in this file, and r2 agrees with it byte for
byte (§1). It does not identify what the field is, and it is not a claim that
`0x07D0` and `0x07D1` are halves of one number — a shift of adjacent bytes is
consistent with a 3-byte counter, a sliding field inside a packed structure,
or a 16-bit value being moved. What it does establish is that the PD firmware
treats these three addresses as neighbours, which the single-byte class
cannot show.

**It is not the only routine that touches both bytes**, and the difference
matters. Three sites here share a routine with a `0x07D0` site, and they fail
the same test differently:

| site | reads | writes | what it is |
|---|---|---|---|
| `0x3E7D` | `[0x07D0]`, `[0x07D1]` | `[0x07D1]`, `[0x07D2]` | a 16-bit right shift — the only one that reads both halves of a word and writes both back |
| `0x8662`/`0x866A` | `[0x07D0]` at `0x865A` | `[0x07D1]`, or zero | a **copy** of `0x07D0` into `0x07D1`, guarded by the `jz` at `0x8667` |
| `0xDA96` | — | `[0x07D1]` from `R5`, then `[0x07D0]` from `R7` at `0xDA9B` | two registers into two adjacent bytes, then the `0x77` stride multiply `ec-0x07d0-sites.md` §4 records at `0xDA9B` |

`0x3E7D` is the only one where the value read is the value written, which is
what makes it evidence about a shared field rather than about two
coincidentally adjacent variables. The other two are cross-address traffic —
the second is the DSDT's own `DBD1` → `PD:DBD2` direction, done by the PD
firmware itself.

## 5. Are all 76 real instructions?

`scan_refs.py` counts the byte pattern `90 07 D1` with no instruction
alignment, so in principle some hits are operand bytes inside other
instructions or bytes inside a data table. `disasm8051.py --converge`
therefore reports *evidence*, not a verdict: it decodes linearly from each of
the 24 bytes preceding a site and counts how many walks land exactly on it
versus step over it.

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d1-sites.csv')))
print(collections.Counter('syncs from every anchor' if r['frame_over'] == '0' else
      'syncs from none' if r['frame_onto'] == '0' else 'mixed' for r in rows))"
Counter({'syncs from every anchor': 57, 'mixed': 15, 'syncs from none': 4})
```

All 4 that no preceding anchor syncs onto are the same idiom
`ec-0x07d0-sites.md` §5 accounted for 42 of its own 45: `lcall 0x104D`
followed by four bytes of inline argument data, which a linear decoder cannot
know is not code and walks straight through. Each one has exactly that shape,
and the four argument bytes are:

| site | `lcall 0x104D` at | four inline bytes |
|---|---|---|
| `0x7630` | `0x7629` | `00 00 03 20` |
| `0x93CD` | `0x93C6` | `00 00 00 01` |
| `0xAF01` | `0xAEFA` | `00 00 00 01` |
| `0xD76C` | `0xD765` | `00 00 03 20` |

`0x104D` pops its own return address into DPTR, fetches four bytes from the
code stream through `0x1064`, and resumes past them with `jmp @a+dptr` — the
decode is in `ec-0x07d0-sites.md` §5 and is not repeated. So all 4 are
accounted for, and none of them is misframed: the site itself is where the
walk lands once the argument bytes are stepped over.

Nothing here found a false positive among the 76. Every site is followed by a
coherent `movx` access, a handoff to a routine that performs one, or the
multi-byte shape §4.3 decodes. That is not the same as proving any of them
executes, or is executable on this SKU — see §7.

**The CODE-pointer blind spot, checked explicitly for this address.** `MOV
DPTR,#imm16` builds CODE pointers as well as XDATA ones, and in this image
CODE `0x07D1` is inside the float-formatting string table: it is the `+` that
starts `"+INF"`, between `"NaN"` at `0x07CD` and `"-INF"` at `0x07D6`. The
collision here is *tighter* than for `0x07D0`, whose CODE `0x07D0` is only
the NUL terminator of `"NaN"` — for `0x07D1` the address is a live string
start that a table could plausibly target. The classifier names `movc` and
`jmp @a+dptr` separately precisely so this cannot hide, and both columns are
**0** for all 76. No site in this file is a table lookup in CODE.

## 6. `DBD2` against `DBD1`: the same kind of variable, and where it differs

The issue this file answers asked two things, and the answers are separate.

**Do the two site sets overlap? No — the intersection is empty.** This is a
set question over two committed CSVs, not an inference from counts:

```console
$ python3 -c "
import csv
a = {r['file_offset'] for r in csv.DictReader(open('ec/annotations/ec-0x07d1-sites.csv'))}
b = {r['file_offset'] for r in csv.DictReader(open('ec/annotations/ec-0x07d0-sites.csv'))}
print(len(a & b), 'shared of', len(a), 'and', len(b))"
0 shared of 76 and 254
```

**Same kind of PD variable, or a different one that merely shares a number
with the GPU pair?** The same kind, with the confidence stated: *high* on
"same kind", because three independent lines of evidence agree and none
contradicts it. *Not claimed* is any statement that they are the same
variable, that either is named, or what either indexes.

The evidence for "same kind":

- **Same shape.** Both are read-mostly, stride-multiplied indices into PD
  arrays reached through the same Keil `DPTR = base + A × B` idiom. 60 of 76
  read here; 229 of 254 read for `0x07D0`.
- **A shared array base.** `0x08FC` with stride `0x5E` is indexed by `0x07D0`
  (through helper `0x34D9`, per `ec-0x07d0-sites.md` §4) *and* by `0x07D1` at
  four of its sites here — `0x76F9` and `0x973C` inline, plus the two that
  hand DPTR to the `0xACF4` callee. One array, two index variables.
- **The same 16-bit little-endian idiom, on both sides.** §4.3 decodes
  `0x3E7D` shifting `[0x07D0]`→`0x07D1` and `[0x07D1]`→`0x07D2`. The
  `0x07D0` half has the mirror of it: site `0xDACF` reads `0x07D0` into `R7`,
  `inc dptr`, reads `0x07D1` into `R5` — the same 16-bit little-endian load
  as `0xAD83`/`0xB38E` here, on the other side of the pair.
  `ec-0x07d0-sites.csv` already scores that site as a two-byte walk, so
  nothing here contradicts `ec-0x07d0-sites.md`; what is new is naming where
  the second read lands. This was not expected when the walk started, and it
  is the single strongest piece of evidence that the PD firmware holds
  `0x07D0` and `0x07D1` as adjacent halves of a quantity.

Where they differ, and none of it is smoothed over:

| | `0x07D0` (`DBD1`) | `0x07D1` (`DBD2`) |
|---|---|---|
| sites | 254, over 11 pages | 76, over 9 pages |
| read / write | 229 / 15 (5.9% written) | 60 / 16 (**21% written**) |
| incremented in place | 2 sites | **none** |
| unresolved by this method | 8 | 0 |
| handoff callees | 25 distinct | 8 distinct |
| strides used | `0x5E`, `0x60`, `0x77` | `0x5E`, `0x17` |
| multi-byte walks | 4 sites | 5 sites, 4 of them a 16-bit pair |

So: this byte is written proportionally about three and a half times as often,
it is never incremented in place, its accessor set is far more concentrated,
and only the `0x5E` stride is shared. The one stride that is new to the pair,
`0x17`, is not new to the image.

**How `DBD2` differs from `DBD1` in the PD image, in one sentence:** on the PD
side they are two adjacent bytes of overlapping 16-bit little-endian windows,
with `0x07D0`/`0x07D1` read as a word at `0xDACF` and `0x07D1`/`0x07D2` as a
word at `0xAD83`, `0xB38E` and `0x3E91`; on the DSDT side they are two
independent 8-bit fields, and the field list says so explicitly —
`Offset (0x7D0), DBD1, 8, DBD2, 8, Offset (0x7D3), , 4`
(`evidence/acpi/dsdt.dsl:52248-52252`). The DSDT names `0x07D0` and `0x07D1`
as two fields and leaves `0x07D2` unnamed, while the PD firmware's 16-bit
quantities straddle that field boundary in both directions.

That is a real divergence, and it is the answer to what is worth recording:
**the DSDT's `DBD1`/`DBD2` pair is a pair of the DSDT's own making, not a
16-bit quantity the PD firmware agrees with.** The DSDT writes `Arg1 * 8` and
`Arg2 * 8` as two separate byte stores of a GPU power value; the PD firmware,
which never sees the DSDT, slides and loads those two bytes as halves of a
little-endian word that also reaches `0x07D2`. Whether the two readings of the
same physical bytes ever collide in practice is not determined here — the EC
side has no committed reference to this address at all.

## 7. What this does not establish

- **Nothing about the EC's `0x07D1`.** The byte the DSDT writes as `DBD2` lives
  in the main EC image's XDATA, which references `0x07D1` **zero** times by
  this method. The 76 sites are a different program's variable.
  `registers.yaml` keeps `unknown-not-absent-DO-NOT-WRITE-BLIND`, and this
  file does not lift it, propose lifting it, or add any tool that writes the
  byte. No `static_refs*` count and no `status:` value moved with this walk,
  and a PD-image walk cannot move an EC-side one.
- **76 is a lower bound, and a zero would have meant "not found".**
  `trace_xdata_refs.py` finds direct `MOV DPTR,#imm16` sites only. Anything
  reaching the byte through a computed DPTR — a register-held address, a
  table of pointers, an indirect `movx @a+dptr` or `movx @r0` — is invisible
  to it. That blind spot is the one §4c of `../../docs/findings.md` retracted
  a claim over, and it is why "76 sites" and "the PD firmware references this
  byte 76 times" are not the same sentence.
- **"76" is what this method found, not what the firmware does with the
  byte.** Nor is it a count of distinct decisions: 17 sites hand DPTR to 8
  shared accessors and 4 follow one call idiom (§3, §5).
- **Nothing observed on hardware.** No register was read back, no write was
  attempted, nothing was run on the machine. This is static analysis of a
  committed firmware image and that is all it is.
- **No control-flow recovery.** `disasm8051.py` decodes linearly and stops at
  the first branch; "76 distinct sites" counts *static* sites, and says
  nothing about how many execute, how often, or in what order. Some of these
  sites are certainly in the same functions — the `0xACBF`/`0xACB7`
  tail-share in §3 is proof of that much — and tracing functions upward is
  `#26`'s job, as is naming the 69 unnamed `DPTR` recipients
  `pd-index-geometry.md` §2.3 lists (`#67`).
- **The handoffs are resolved one level only.** `0x972E` returns a bare
  product with no base, and any callee that hands DPTR on again would stay
  unresolved — none of these 8 does at depth 1, but depth 2 is not attempted.
- **What the 16-bit windows mean is not identified.** §4.3 establishes that
  `0x07D0`-`0x07D2` are treated as contiguous and that `0x07D1` participates
  in two overlapping little-endian words. A shift of adjacent bytes is
  consistent with a 3-byte counter, a packed structure field, or a moved
  16-bit value, and this walk does not choose between them. What the indexed
  arrays contain is likewise unrecorded, as it is for `0x07D0`.
- **Nothing from the Windows side was re-derived here.** The absence of an
  `ECSpec` constant and of an `ec-callsites.csv` row is cited as it stands
  from the `registers.yaml` entry; no anti-tamper-protected method body was
  involved (`../../windows/antitamper/README.md`).

## 8. What would settle the rest

Unchanged, and still a human-at-the-machine step: a paired write to `0x07D0`
and `0x07D1` through the `T1WR` `Arg0 == 0x1173` path, alongside the
`0x07B9`/`0x07D0` experiment in §7 of
[`ec-0x07d0-sites.md`](ec-0x07d0-sites.md), with the GPU block's effect
observed — the DSDT's only committed writer of
either byte is a GPU power control, and nothing here predicts what a write
lands on. The values written by that branch are `Arg * 8` with `Arg` bounded
by 31, which is arithmetic on the ASL and not a claim about the argument's
meaning.

Three questions this walk opened, and deliberately did not answer:

- **What is the `0x07D0`/`0x07D1`/`0x07D2` field?** §4.3 locates it, shifts
  it, and loads it as a word. Naming it needs the call graph and the
  surrounding PD structures — `#26` and `#67`, not this file.
- **Does the PD's 16-bit reading of `0x07D0`/`0x07D1` ever collide with the
  DSDT's two independent byte fields?** §6 states the divergence and stops.
  A live observation would say more than another static pass, and no live
  observation is possible from here.
- **Does the EC firmware read `0x07D0` or `0x07D1` at all?** The EC image
  references neither by this method, which is the §4c signal, not a verdict.
  `#25` owns the `0x07D0` half of that question; this file does not re-open
  it, and the `0x07D1` half is not reachable from its scope.
