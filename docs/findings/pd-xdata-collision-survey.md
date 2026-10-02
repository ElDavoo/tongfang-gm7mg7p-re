# The 39 other collisions, decoded: the PD image hands them on, and the low 4 KiB's excess sits on one page

(2026-10-02, issue #64. Static reading of `ec/firmware/GMxMGxx_11.800`
through `trace_xdata_refs.py`, `xdata_span_survey.py`, `pd_index_geometry.py`
and `r2`. No capture opened, no EC, no hardware, no Windows, no `registers.yaml`
status touched.)

`pd-xdata-overlap.md` §5.1 rests its separate-maps reading on one address,
and says so itself: `0x04A6` was never special, it was the one collision over
`0x0400`-`0x07FF` that the audited addresses in `registers.yaml` happened to
include. What the rest of the set does is not known, and the chance argument
§5.1 offers the sample against has never been run against more than one of
them. This decodes the rest, applies the three tests §4 used to each, and
widens the survey from the span to the whole XDATA range.

The two halves answer differently, and the difference is the point.

**The decode.** At 29 of the 39, no `movx` at the address is found in any PD
site this scan sees: every PD site hands DPTR to a helper, and what the helper
dereferences afterwards is the part a `90 hi lo` byte scan cannot follow. That
is §5.2's "field offset into one strided structure" reading, measured over the
whole collision set rather than inferred from `0x04A6` and `0x04A3`. The
issue's falsifier — *a collision where both images increment the same byte* —
**does not appear in this scan**: no address has a read-modify-write in place
on both sides, and the `0x07D4` case that comes closest is a PD increment loop
against an EC mirror register that has already been named in this repository.

**The wider count.** Across `0x0000`-`0xFFFF` there are **138** addresses with
direct `MOV DPTR` sites in both images, and they are not spread evenly over the
low range: 65 of them are on the `0x0800`-`0x08FF` page. That looks at first
like §5.1's chance argument collapsing — a collision rate well over what
independent allocation predicts. It does not. Take that page out and the
collision rate in the rest of the low 4 KiB is what independent choice
predicts, and the argument survives, with the discount §5.1 already attached to
it unchanged.

## 1. The wider range, and the table that is its product

`xdata_span_survey.py` already took `lo`/`hi` as arguments; `--collisions` and
`--check` are what this needed. The full range is one pass, as the span was:

```console
$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x0000 0xFFFF --page 0x1000
0x0000-0xFFFF: 65536 addresses
  main EC :   7238 sites over 1899 addresses
  PD image:   3176 sites over 458 addresses
  both    : 138 address(es) with sites in each image

  block              main EC       PD
  0x0000-0x0FFF       5094     2844
  0x1000-0x1FFF       1222        6
  0x2000-0x2FFF         80       77
  0x3000-0x3FFF         95        4
  0x4000-0x4FFF         12        1
  0x5000-0x5FFF          1        4
  0x6000-0x6FFF         23       11
  0x7000-0x7FFF         65        9
  0x8000-0x8FFF         70        4
  0x9000-0x9FFF         33       11
  0xA000-0xAFFF         29        1
  0xB000-0xBFFF        155        3
  0xC000-0xCFFF        149       10
  0xD000-0xDFFF         31        8
  0xE000-0xEFFF        146        6
  0xF000-0xFFFF         33      177
```

A table of every address in the range is 65536 rows, almost all of them zero on
one side or the other. `--collisions` emits the rows both images reference, and
that table is committed beside the span one:

```console
$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x0000 0xFFFF \
    --csv --collisions > ec/annotations/pd-xdata-collisions-full.csv
$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x0000 0xFFFF \
    --csv --collisions --check ec/annotations/pd-xdata-collisions-full.csv
ec/annotations/pd-xdata-collisions-full.csv: this run reproduces it byte for byte (139 lines)
```

`--check` is `trace_xdata_refs.py`'s, imported rather than reimplemented, so
the committed `pd-xdata-span-sites.csv` is held the same way and §1's
cross-check against `trace_xdata_refs.py` still reproduces:

```console
$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x0400 0x07FF \
    --csv --check ec/annotations/pd-xdata-span-sites.csv
ec/annotations/pd-xdata-span-sites.csv: this run reproduces it byte for byte (1025 lines)
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x04A6 0x04A7 0x07D0 --counts-only
0x04A6: 7 direct MOV DPTR site(s)  bank0=1  bank1=2  pd-image=4

0x04A7: 2 direct MOV DPTR site(s)  bank0=1  bank1=1

0x07D0: 254 direct MOV DPTR site(s)  pd-image=254
```

Those are `7 = 3 + 4` and `254` pd-only — the figures `registers.yaml`,
`static-refs-audit.md` §1 and `ec-0x07d0-sites.md` §1 all quote — so the
wider run did not change what the narrower one measured.
`test_xdata_span_survey.py` holds all of it: both `--check`s, the three
agreement rows re-derived by *running* `trace_xdata_refs.py` rather than
compared against literals, and the property that every committed collision row
is referenced by both images.

## 2. Where the full-range collisions sit, and what the chance argument does now

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/pd-xdata-collisions-full.csv')))
pages = collections.Counter(int(r['addr'], 16) >> 8 for r in rows)
for pg, n in sorted(pages.items()):
    print(f'0x{pg:02X}00-0x{pg:02X}FF  {n:>3}')
print()
print('at or above 0x1000:', ' '.join(sorted(r['addr'] for r in rows
                                             if int(r['addr'], 16) >= 0x1000)))"
0x0000-0x00FF    9
0x0200-0x02FF    2
0x0300-0x03FF    1
0x0400-0x04FF   23
0x0600-0x06FF    6
0x0700-0x07FF   11
0x0800-0x08FF   65
0x0900-0x09FF    5
0x0A00-0x0AFF   11
0x9000-0x90FF    3
0xC200-0xC2FF    1
0xEF00-0xEFFF    1

at or above 0x1000: 0x9004 0x9007 0x900A 0xC291 0xEF70
```

§5.1's arithmetic — the PD image touches *p* addresses, the EC image *e*, out
of *n*, so independent choices collide on about *p × e / n* — applied to
ranges other than its own:

```console
$ python3 -c "
import csv, io, math, subprocess, sys

def survey(lo, hi):
    t = subprocess.run([sys.executable, 'ec/tools/xdata_span_survey.py',
                        'ec/firmware/GMxMGxx_11.800', lo, hi, '--csv'],
                       capture_output=True, text=True).stdout
    return list(csv.DictReader(io.StringIO(t, newline='')))

print(f\"{'range':<24}{'addrs':>6}{'EC':>6}{'PD':>6}{'both':>6}{'expected':>10}{'z':>7}\")
def counts(rows):
    ec = sum(1 for r in rows if int(r['main_ec']))
    pd = sum(1 for r in rows if int(r['pd_image']))
    both = sum(1 for r in rows if int(r['main_ec']) and int(r['pd_image']))
    e = ec * pd / len(rows)
    return ec, pd, both, e, (both - e) / math.sqrt(e * (1 - ec / len(rows))
                                               * (1 - pd / len(rows)))

def line(label, rows):
    ec, pd, both, e, z = counts(rows)
    print(f'{label:<24}{len(rows):>6}{ec:>6}{pd:>6}{both:>6}{e:>10.1f}{z:>+7.1f}')

low = survey('0x0000', '0x0FFF')
line('0x0400-0x07FF', survey('0x0400', '0x07FF'))
line('0x0000-0x0FFF', low)
line('  minus 0x0800 page', [r for r in low
                             if not 0x800 <= int(r['addr'], 16) <= 0x8FF])
line('  0x0800 page alone', [r for r in low
                             if 0x800 <= int(r['addr'], 16) <= 0x8FF])
line('0x0000-0xFFFF', survey('0x0000', '0xFFFF'))

print()
print('leave-one-out over the sixteen 0x100 pages of the low 4 KiB:')
print(f\"  {'page dropped':<14}{'addrs':>6}{'both':>6}{'expected':>10}{'z':>7}\")
for pg in range(16):
    rest = [r for r in low
            if not pg * 0x100 <= int(r['addr'], 16) <= pg * 0x100 + 0xFF]
    _, _, both, e, z = counts(rest)
    print(f\"  0x{pg:02X}00-0x{pg:02X}FF{len(rest):>7}{both:>6}{e:>10.1f}{z:>+7.1f}\")
"
range                    addrs    EC    PD  both  expected      z
0x0400-0x07FF             1024   430   114    40      47.9   -1.6
0x0000-0x0FFF             4096  1029   346   133      86.9   +6.0
  minus 0x0800 page       3840   862   263    68      59.0   +1.4
  0x0800 page alone        256   167    83    65      54.1   +3.0
0x0000-0xFFFF            65536  1899   458   138      13.3  +34.9

leave-one-out over the sixteen 0x100 pages of the low 4 KiB:
  page dropped   addrs  both  expected      z
  0x0000-0x00FF   3840   124      73.9   +7.0
  0x0100-0x01FF   3840   133      90.7   +5.4
  0x0200-0x02FF   3840   131      90.5   +5.2
  0x0300-0x03FF   3840   132      78.5   +7.2
  0x0400-0x04FF   3840   110      73.2   +5.1
  0x0500-0x05FF   3840   133      84.5   +6.4
  0x0600-0x06FF   3840   127      78.2   +6.6
  0x0700-0x07FF   3840   122      69.0   +7.6
  0x0800-0x08FF   3840    68      59.0   +1.4
  0x0900-0x09FF   3840   128      84.3   +5.8
  0x0A00-0x0AFF   3840   122      68.7   +7.7
  0x0B00-0x0BFF   3840   133      91.8   +5.3
  0x0C00-0x0CFF   3840   133      92.5   +5.2
  0x0D00-0x0DFF   3840   133      91.9   +5.2
  0x0E00-0x0EFF   3840   133      91.0   +5.4
  0x0F00-0x0FFF   3840   133      89.7   +5.6
```

Two of these lines are not findings, and the third is.

`0x0000-0xFFFF` at +34.9σ is **not** a collision rate. Both images are Keil
allocations biased toward low XDATA, so a uniform null over 64 KiB is the wrong
model and that z measures the bias, not agreement. That is the discount §5.1
states for its own span, and widening the span does not remove it.

`0x0000-0x0FFF` at +6.0σ looks like it might be one, and is not: it is the
`+1.4σ` row and the `+3.0σ` row added together, because one contains the
other. **Take the `0x0800` page out and the collision rate in the rest of the
low 4 KiB is what independent choice predicts** — 68 observed against 59.0,
which is +1.4σ and nothing a reader would act on. §5.1's "40 is about what
chance predicts" is therefore not an artefact of the span it was measured on;
it holds one page wider.

**The page is where the excess in the low 4 KiB sits, and the choice of it was
not made after the fact.** Removing `0x0800`-`0x08FF` takes the rest of that
4 KiB to +1.4σ, and the leave-one-out above drops each of the sixteen `0x100`
pages in turn to show no other single page does anything like it: every other
removal leaves the remainder between +5.1σ and +7.7σ. So the concentration is
a property of that page and not of the choice to single it out — had the
excess been spread, every leave-one-out would have stayed high. On the page
itself the two images' address choices exceed a null computed over that page
alone, which is the same uniform model the full-range row has already
discounted one scale up: the excess is measured here, not explained, and it is
the leave-one-out above rather than the page's own z that carries the
conclusion.

That is a statement about the low 4 KiB, which is what this section measures.
The wider range is not scanned page by page here, so nothing is claimed about
`0x1000`-`0xFFFF` beyond the full-range row above.

**What that page is, and what it is not.** It is not new territory in this
repository: `pd-base-strides.csv` already records the PD image's second stride
family (`0x5E`) on nine bases at `0x08E7`-`0x08FC`, and `xdata-086x-dispatch.md`
is about the EC's `0x086x` handlers. Both images allocate there heavily and
they collide there more than that page's own null predicts, and **this work
does not say why** — naming what either image keeps at `0x0800`-`0x08FF` needs
the control-flow recovery §6 lists as missing, and `pd-index-geometry.md` §8 is
where that question is already carried. It is a follow-up, not a result.

## 3. The 39, with §4's three tests applied to each

The three tests, from `pd-xdata-overlap.md` §4: is the access a byte access or
a base for index arithmetic; is anything incremented or compared against a
constant; does the same address get the same *shape* of use in both images.
Run over all 39 in one `trace_xdata_refs.py` call and read off its `--csv`
`access` and `window` columns — `index` is `DPTR handed to lcall/ljmp`,
`walk` is an `inc dptr` onto the next byte, `byte` is a `movx` at the address
itself, and `none` is a window with no `movx` in it:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
    0x0400 0x0404 0x0408 0x040C 0x0410 0x0420 0x0432 0x0434 0x0437 0x043A \
    0x0457 0x0458 0x0491 0x0495 0x0499 0x049D 0x049F 0x04A1 0x04A2 0x04A3 \
    0x04A4 0x04A8 0x0670 0x0672 0x0678 0x0679 0x0694 0x0699 0x07C4 0x07D3 \
    0x07D4 0x07D5 0x07D8 0x07D9 0x07DA 0x07F3 0x07F6 0x07FE 0x07FF --csv \
  | python3 -c "
import csv, collections, sys

rows = list(csv.DictReader(sys.stdin))
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    by[r['addr']]['pd' if r['region'] == 'pd-image' else 'ec'].append(r)

def shape(rs):
    n = collections.Counter()
    for r in rs:
        a = r['access']
        if 'inc dptr' in a:
            n['walk'] += 1
        elif 'DPTR handed' in a:
            n['index'] += 1
        elif a.startswith('no movx found'):
            n['none'] += 1
        else:
            n['byte'] += 1
    return ', '.join(f'{v} {k}' for k, v in sorted(n.items(), key=lambda kv: -kv[1]))

def rmw(rs):
    # a read and a write of the named byte itself, no walk, with +1 between
    return [r for r in rs if 'inc dptr' not in r['access']
            and not r['access'].startswith('no movx')
            and 'read' in r['access'] and 'write' in r['access']
            and ('inc a' in r['window'] or 'add a,#0x01' in r['window']
                 or 'addc a,#0x01' in r['window'])]

print(f\"{'addr':<8}{'main EC':<36}{'PD image':<38}in-place +1 in both?\")
hits = []
for addr in sorted(by):
    both = rmw(by[addr]['ec']) and rmw(by[addr]['pd'])
    hits += [addr] if both else []
    print(f\"{addr:<8}{shape(by[addr]['ec']):<36}{shape(by[addr]['pd']):<38}\"
          f\"{'YES' if both else 'no'}\")
print()
print('addresses with an in-place increment in BOTH images:',
      ' '.join(hits) if hits else 'none')
"
addr    main EC                             PD image                              in-place +1 in both?
0x0400  2 none, 1 byte, 1 index             2 index, 2 none                       no
0x0404  10 index, 1 walk                    3 index                               no
0x0408  2 index                             5 index, 2 none                       no
0x040C  2 index                             2 index                               no
0x0410  1 index                             4 index, 1 none                       no
0x0420  1 none                              11 index                              no
0x0432  12 byte                             2 index                               no
0x0434  9 index, 1 byte                     4 index, 2 none                       no
0x0437  1 byte                              5 index                               no
0x043A  3 index                             3 index                               no
0x0457  4 byte                              1 index                               no
0x0458  4 byte                              1 index                               no
0x0491  37 byte                             7 index                               no
0x0495  12 byte                             8 index                               no
0x0499  6 byte                              2 index                               no
0x049D  7 byte                              4 index                               no
0x049F  12 byte                             3 index                               no
0x04A1  5 byte                              3 index                               no
0x04A2  5 index, 1 byte                     5 index                               no
0x04A3  1 byte                              5 index                               no
0x04A4  1 index                             1 none, 1 index                       no
0x04A8  1 index                             1 index                               no
0x0670  9 byte                              6 index                               no
0x0672  4 byte                              2 index                               no
0x0678  2 byte                              1 index                               no
0x0679  2 byte                              1 index                               no
0x0694  6 byte                              2 index                               no
0x0699  2 byte                              6 index                               no
0x07C4  4 byte, 1 none                      3 index                               no
0x07D3  2 byte, 2 none                      4 byte, 3 index                       no
0x07D4  2 byte                              48 byte, 14 index, 4 walk, 2 none     no
0x07D5  4 byte                              19 byte, 4 index, 1 none              no
0x07D8  1 byte                              28 byte, 4 index, 1 none              no
0x07D9  1 byte                              9 byte, 4 index, 1 none, 1 walk       no
0x07DA  1 byte                              30 byte, 19 index, 3 walk             no
0x07F3  4 byte                              3 walk, 1 index, 1 byte               no
0x07F6  5 byte                              2 byte, 1 walk, 1 index               no
0x07FE  7 byte                              1 byte, 1 walk                        no
0x07FF  7 byte                              1 byte                                no

addresses with an in-place increment in BOTH images: none
```

The three tests, answered:

**Byte access, or index base?** At 24 of the 39 the PD column is entirely
`index` — DPTR handed on, with no `movx` at the address in the window — and at
five more (`0x0400`, `0x0408`, `0x0410`, `0x0434`, `0x04A4`) it is `index`
plus `none`, still no `movx` at the address. **At the other 29, no `movx` at
the address is found in any PD site this scan sees**, and §5's caveat is what
governs that wording: `0x04A3`, one of the 29, is an address whose PD sites do
dereference, at a rebased address this scan cannot see. The ten that are
dereferenced all sit on the `0x07xx` page, and that is not the
collision-concentration effect §2 measures:
`xdata-registers.csv` already marks all ten of them `program=both`, so a page
this heavily used on both sides is where a plain `movx` is expected to turn up
rather than an index base.

Those 29 are not a fresh finding, and it is worth saying where they are
already recorded: every one of the 22 `0x04xx` collisions is a base in
`pd-base-strides.csv`'s `0x60` row, which is the stride family
`pd_index_geometry.py --strides 0x0400-0x07FF` re-derives, and
`pd-index-geometry.md` §3.2's page term makes the effective stride `0x260`. So
§5.2's reading is not re-derived here; it is now measured over the whole
collision set rather than over `0x04A6` and `0x04A3`, and it comes out the
same. The six `0x06xx` collisions are in none of that mode's resolved rows —
`--strides 0x0400-0x07FF` leaves each of them `unresolved`, which is this
tool's word for "the chain was not modelled to a stride constant", not a
verdict that no stride is there.

**Incremented, or compared against a constant?** The PD side does both, and
`pd_index_geometry.py --strides 0x0400-0x07FF` is where the arithmetic lands:
`mov 0xf0,#0x5e ; mul ab ; add a,#0xe9` at most `0x07D4` sites is the stride
`0x5E` computation, not an increment of the byte. The one genuine in-place
increment in the whole set is §4's next section. The EC side compares
constants at five of the 39, and not in one shape: `0x0458` and `0x0491` are
masked bit-field tests (`anl a,#0x70 ; cjne a,#0x10` and `anl a,#0xc0`),
`0x0670` a threshold compare against `0xA0` whose byte is elsewhere written
with that same `0xA0`, and `0x07FE`/`0x07FF` unmasked compares against the
`0x55`/`0xAA` pair followed by clearing both. At the first three of those the
PD image hands DPTR on rather than reading; at the last two it reads the byte.

**Same shape in both images?** No, and consistently so in one direction. Of
the 28 collisions below `0x0700`, **20 have a `movx` at the address in the EC
and are never dereferenced by the PD image** — the same asymmetry §5.2 found
for `0x04A1`-`0x04A6`, now measured over the set instead of the two addresses
the audit happened to include. Three of those 20 (`0x0400`, `0x0434`,
`0x04A2`) have an `index` site on the EC side as well, so "EC touches the byte,
PD does not" is the claim rather than "`movx` throughout".

`xdata-registers.csv` is a different projection — census rows over annotated
functions, not an unaligned byte scan — and this file does not reconcile its
magnitudes. Its *set* nearly agrees with the scan's, and the near-agreement is
worth the sentence: the census marks eleven addresses `program=both`, and this
survey finds the PD image dereferencing the byte at ten of those eleven, all
on `0x07xx`. The eleventh, `0x04A3`, has a PD column of `5 index` and no
`byte`, and that is the caveat above rather than a disagreement between the two:
`pack-temp-producer-chain.md` §4 adjudicated that address as a base whose
PD-side dereferences land at a rebased address (`0x04A3 + R7×0x60 + 0x200×R7`
and the like), which a `90 hi lo` byte scan cannot see — §5's blind spot,
operating in the direction that makes the two projections agree rather than
disagree. The census marks the other 25 `program=main-ec`, with three of the 39
carrying no census row at all.
Ten of eleven, plus one the file can account for, is corroboration from two
projections with different units; §5's `unresolved` caveat is what governs it.

## 4. `0x07D4`, the closest the two images come

The falsifier does not turn up in this scan, so the address worth writing up
is the one where a PD-side in-place increment sits opposite an EC-side write.
That is `0x07D4`, and both halves are already understood, from opposite
directions.

The load-bearing windows below are `r2 -a 8051` listings, not this repository's
linear decoder, and the images are the ones `pd-xdata-overlap.md` §1 builds:

```console
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
```

The PD image increments `0x07D4` in place, under a bound:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xee03; pd 16' /tmp/pd.bin
        ┌─> 0x0000ee03      9007d4         mov dptr, #0x07d4
        ╎   0x0000ee06      e0             movx a, @dptr
        ╎   0x0000ee07      ff             mov r7, a
        ╎   0x0000ee08      c3             clr c
        ╎   0x0000ee09      9401           subb a, #0x01
       ┌──< 0x0000ee0b      5014           jnc 0xee21
       │╎   0x0000ee0d      12f28d         lcall 0xf28d
       │╎   0x0000ee10      9007d4         mov dptr, #0x07d4
       │╎   0x0000ee13      12b293         lcall 0xb293
       │╎   0x0000ee16      121041         lcall 0x1041
       │╎   0x0000ee19      9007d4         mov dptr, #0x07d4
       │╎   0x0000ee1c      e0             movx a, @dptr
       │╎   0x0000ee1d      04             inc a
       │╎   0x0000ee1e      f0             movx @dptr, a
       │└─< 0x0000ee1f      80e2           sjmp 0xee03
       └──> 0x0000ee21      22             ret
```

`clr c ; subb a,#1 ; jnc` leaves the loop on the first non-zero read, so the
shape is `while 0x07D4 == 0 { call 0xf28d; call 0xb293; call 0x1041; 0x07D4++ }`
— a bounded poll over a byte it expects something else to fill in. The
`movx a,@dptr ; inc a ; movx @dptr,a` is the only in-place `+1` this scan
finds in either image across all 39.

The EC image's two sites at `0x07D4` are a compare-and-copy, not an
increment:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x845b; pd 18' /tmp/bank0.bin
            0x0000845b      9009ea         mov dptr, #0x09ea
            0x0000845e      e0             movx a, @dptr
            0x0000845f      ff             mov r7, a
            0x00008460      9007d4         mov dptr, #0x07d4
            0x00008463      e0             movx a, @dptr
            0x00008464      6f             xrl a, r7
        ┌─< 0x00008465      700c           jnz 0x8473
        │   0x00008467      9009eb         mov dptr, #0x09eb
        │   0x0000846a      e0             movx a, @dptr
        │   0x0000846b      ff             mov r7, a
        │   0x0000846c      9007d5         mov dptr, #0x07d5
        │   0x0000846f      e0             movx a, @dptr
        │   0x00008470      6f             xrl a, r7
       ┌──< 0x00008471      6029           jz 0x849c
       │└─> 0x00008473      9009ea         mov dptr, #0x09ea
       │    0x00008476      e0             movx a, @dptr
       │    0x00008477      9007d4         mov dptr, #0x07d4
       │    0x0000847a      f0             movx @dptr, a
```

`0x07D4` is compared against `0x09EA` and, on a mismatch, **overwritten from
it**; `0x07D5` is then compared against `0x09EB` the same way. That is a
mirror pair, and the repository already says so: `xdata-registers.csv`'s
`0x07D4` row carries `bank0:0x83FF=sync_0788_and_07d4_from_09e9`, and the
DSDT spells the byte `CPUA`. So the two images' uses are not two readings of
one counter — one program is polling for a byte to become non-zero and the
other is keeping a copy of `0x09EA` in step with it.

**This is not a conflict, and it is not proof of one.** Whether the PD image's
`0x07D4` and the EC's `0x07D4` are the same byte is a question of §7's kind for
this address — one only a human at the machine can answer, because two
programs whose separate XDATA spaces are byte-identical in address would
produce this listing pair exactly as it stands — and it is still open.

## 5. What this does not establish

- **Nothing observed on hardware.** No register was read, written or read
  back; nothing ran on the machine. Static analysis of
  `ec/firmware/GMxMGxx_11.800` and that is all it is.
- **Every zero here means "not found by this `90 hi lo` scan".** The same
  blind spot §6 of `pd-xdata-overlap.md` carries for `0x04A7` cuts against the
  PD-side `index` reading here exactly as much as for it: a pointer built in
  registers, or a base+offset access reaching one of these addresses from some
  other base, is invisible to this scan. `0x04A7`'s absent PD column and the
  `none` cells above are the same claim.
- **The `index` cells are `unresolved` in the tool's own vocabulary.**
  `trace_xdata_refs.py` reports `DPTR handed to lcall … -- direction unresolved
  here` because it cannot follow a call. `pd-index-geometry.py` resolves the
  arithmetic for the addresses whose chain it can model, and issue #1425
  adjudicated `0x04A3` as a base rather than as the datum
  (`pack-temp-producer-chain.md` §4: the three sites that dereference do so at
  a rebased address, `0x04A3 + R7×0x60 + 0x200×R7` and the like, and no
  general value of those terms lands on the byte) — but that is a per-address
  adjudication, not something this survey did for all 29. "Hands DPTR on" is
  the claim; what it computes is not re-derived here.
- **The `0x0800` page's excess is measured, not explained.** §2 shows where it
  is and that the rest of the low range is at chance. Naming what either image
  keeps there is §6's missing control-flow recovery, and it is not attempted.
- **`xdata-registers.csv` is a different projection and is not reconciled
  here.** Its counts are census rows over annotated functions; this file's are
  an unaligned byte scan, and where their magnitudes differ this file does not
  adjudicate. §3 compares the two on the one thing they can be compared on —
  *which* addresses the PD image is recorded as dereferencing — where ten of
  the census's eleven `program=both` addresses agree and `0x04A3` is the
  exception. Agreement on a set is corroboration of the asymmetry, not a
  measurement of it.
- **`BAT_CYCLE_COUNT` is untouched.** Its `confirmed-working` status comes
  from a live read; a static decode can neither strengthen nor weaken that, and
  no status in `registers.yaml` changed in this work.
- **The `unknown-not-absent` entries are not re-graded here.** §7 of
  `pd-xdata-overlap.md` says which would need re-reading and under what
  condition, and that condition is still the live step.

## 6. What follows

- **The `0x0800`-`0x08FF` page**, where both images allocate heavily and
  collide more than a null computed over that page alone would give, and where
  this work says nothing about what either image keeps. §2 names it; naming it
  needs the same recovery §6 of `pd-xdata-overlap.md` lists as missing, and
  `pd_index_geometry.py --bases 0x0800-0x08FF` is the mode already built
  for it.
- **The live step is a human's.** Read EC RAM over a period in which the PD
  image is active and see whether the byte the EC calls `CPUA` moves on its
  own.