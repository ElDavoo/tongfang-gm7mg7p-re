# The table reader has one spelling in the main EC and three in the PD image, and two of the PD three are not this family's layout

(2026-09-27, issue #61. Static reading of committed bytes through
`ec/tools/decode_index_table.py`'s widened `find_readers()` and the new
`ec/tools/pd_index_tables.py`. No capture opened, no EC, no hardware, no
Windows, no `registers.yaml` row touched, no
`ec/annotations/index-table-*.csv` or `bank0-8038-dispatch-table.csv`
regenerated.)

[`bank-call-audit.md`](../../ec/annotations/bank-call-audit.md) §9 finds the main
EC image's inline `switch` tables by one five-byte literal, `d0 83 d0 82 f8`,
and names its own blind spots in the same paragraph: a second reader spelled
differently — `pop dpl` first, a `ret`-based thunk, the selector kept
somewhere other than `r0` — would be invisible to it, and so would a caller
reaching `0x7151` through a BL51 trampoline. This is the search §9's sentence
asked for, run over both images, and the answer is different in each.

**Three results, in the order they matter.**

1. **The widened search still finds exactly one reader in the main EC**, out of
   36 prologue candidates and 10 body-corroborated ones. §9's uniqueness
   assertion survives a search that no longer depends on the literal it was
   written against — and the nine extra corroborated candidates are each a
   `push dph ; push dpl … pop dpl ; pop dph` pair around a single XDATA read, so
   the reason the literal found only one is now a reading rather than an
   accident.
2. **The PD image has three, not two.** `0x119C` and `0x11C2` are the
   dispatchers the committed census already names; **`0x11EF` is a third, with 3
   call sites, that nothing in the tree names.** It is found only because the
   search was widened past the five-byte literal — it has no `mov r0,a` at
   entry.
3. **Two of the PD three are not this family's layout.** Their readers walk
   **4- and 6-byte** entries, not the main EC's 3. The 0x11C2 rows in the new
   census are therefore *failures of the main EC's rule*, not verdicts about
   those tables — and so, in the two rows that pass it, are the two successes.
   This is the reason the new CSV carries a `reader_stride` column, and the
   reason its `well_formed` column is not what a reader of the main EC's file
   would take it to mean.

The trampoline half closes negative and is separate: **no BL51 trampoline in the
image names `0x7151`**, so no trampoline caller is a call site
`reader_call_sites()` structurally could not have found. The computed-caller
half of §9's sentence is untouched and still open.

## What the search is, and why it is tiered

`find_readers()` is now an enumerated set of twelve prologue shapes
(`PROLOGUE_SHAPES`), each a byte pattern matched at every offset of a region —
it is a byte scan and no more, and it does not claim a function boundary at
either end of a match. Each entry carries whether it `from_return_address` —
the family invariant, and the one thing that separates a reader of this family
from a routine that pops a DPTR it pushed itself. The set covers both pop
orders, the selector save landing in a register other than `r0` or in a direct
address, and an intervening `push acc`; the last two entries are the bare pop
pairs, which are the others' prefixes and are what a candidate matches when no
more specific spelling does. A direct-address reader — one that names its table
with an immediate — is **not** in the family and is not in the set:
`direct_address_readers()` counts those separately and decodes none of them.

Widening is only worth doing if the false positives are visible, so candidates
come in **two tiers and the tiers are nested**: every shape match is tier 1, and
a tier-2 candidate is one whose first 8 instructions contain a
`movc a,@a+dptr` — the routine actually walks a table. The window is short on
purpose; the family's own reader reaches its first `movc` at +4, and a longer
one lets a linear decode run past a call into the bytes after it, which is
exactly how a `pop dpl ; pop dph` around a `movx` comes to look like a reader.

The arithmetic that makes this necessary: **36 candidates in the main EC and 93
in the PD image, against 1 and 2 for the whole five-byte literal** — every one
of the 93 is a bare `d0 82 d0 83` or `d0 83 d0 82` at some offset. A search
that stopped at the pops would return 93 candidates in the PD image alone. A
tool that traded a known blind spot for 90
phantoms would not be progress, and the tiering is what keeps it progress.

## Main EC: 36 candidates, 10 corroborated, 1 called

```console
$ python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800
reader search over common/bank0/bank1: 12 prologue shape(s)
     1  d0 83 d0 82 f8 pop-dph-dpl-selector-r0  -- `pop dph ; pop dpl ; mov r0,a` -- the spelling at 0x7151, and the one at the head of each PD dispatcher
    35  d0 82 d0 83    pop-dpl-dph  -- the bare pop pair, dpl first -- no selector save named
  36 shape match(es) (tier 1), of which 10 reach a `movc a,@a+dptr` within 8 instructions (tier 2) and 1 are named by an `lcall`
    tier 2  file 0x07151 runtime 0x7151 (common)  pop-dph-dpl-selector-r0  15 `lcall` byte site(s)
    tier 2  file 0x086EA runtime 0x86EA (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x08716 runtime 0x8716 (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x09410 runtime 0x9410 (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x09439 runtime 0x9439 (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x09484 runtime 0x9484 (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x0A22E runtime 0xA22E (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x0A25C runtime 0xA25C (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x0A282 runtime 0xA282 (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
    tier 2  file 0x0A2A7 runtime 0xA2A7 (bank0)  pop-dpl-dph  0 `lcall` byte site(s)
  1 direct-address candidate(s) -- `mov dptr,#imm16` then a table walk and `jmp @a+dptr`. Not this family, and decoded nowhere:
    file 0x0104D runtime 0x104D (common) names table 0x1055
  `mov dptr,#0x8038` byte sites file-wide: 0
  `mov dptr,#0x803A` byte sites file-wide: 0
  15 `lcall` byte site(s) name the 1 reader(s) above
```

The per-region split of the 36 is 18 `common`, 13 `bank0`, 5 `bank1`, and it
is pinned by `--self-test` so a different dump gets it re-derived.

### The nine that are not readers, read by hand

Nine of the ten corroborated candidates are the same eight-to-nine bytes, and
the reading is short because the shape is uniform. `0x086EA` is the worked
example and the other eight are byte-identical in form:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x86e2; pd 4' /tmp/bank0.bin
            0x000086e2      c083           push dph
            0x000086e4      c082           push dpl
            0x000086e6      900a50         mov dptr, #0x0a50
            0x000086e9      e0             movx a, @dptr
```

and then `d0 82 d0 83` — the candidate itself — restoring the pointer. That is
the compiler saving a DPTR it is about to clobber and putting it back
afterwards: the popped value is the routine's **own** `0x0a50`, not a return
address, so nothing inline follows a call to it. The other eight are the same
thing at `0x08716`, `0x09410`, `0x09439`, `0x09484`, `0x0A22E`, `0x0A25C`,
`0x0A282` and `0x0A2A7` — reading `0x0a49` rather than `0x0a50`, and four of
the nine also keeping the byte they read in `r5`, which with the immediate's
low byte is the whole of the variation between them. `decode_index_table.py
--self-test` holds all nine as that byte pattern, so the reading is a property
of the image and not of this paragraph.

**The `lcall` filter settles it independently, and it is the one that matters.**
A reader of *this* family is entered by a bare `lcall` and nothing else — that
is what makes the table addressable by the call's position at all. All nine
have **zero** `lcall` byte sites naming them, in any of the three main-EC
regions. So the widened search does not merely fail to find a second reader; it
finds nine lookalikes and rejects every one of them on a test that does not
depend on what the routine does.

### The direct-address bucket: one site, and it walks no table

`direct_address_readers()` is deliberately a tight shape — `mov dptr,#imm16`
followed inside the same 8 instructions by both a `movc a,@a+dptr` and a
`jmp @a+dptr` — because `mov dptr,#imm16` is everywhere in this image (1632
byte sites in `common` alone) and a looser shape would drown the search in
pointer loads. It returns exactly **one** site, `0x104D`, and read by hand it is
not a table reader: it reads the single byte at `0x1055` and dispatches through
the bank-switch stub at `0x1100` indexed by it. It names a table of this
family's shape nowhere. The PD image returns **zero**. Neither is decoded, and
the bucket is reported as its own result so the family is not quietly widened to
fit the search.

## The trampoline cross-check closes negative, and did not need #48

§9 left open whether a caller reaching `0x7151` through a BL51 trampoline is
what its `lcall` byte scan cannot see, and whether answering that waits on #48.
It does not: the question is about the trampolines' own `mov dptr,#imm16`
immediates, and those are a byte scan over a committed range today. Using
`audit_call_targets.py`'s own `trampolines()` — imported, not re-derived, so
this cross-check cannot disagree with the audit it is checking:

```console
$ python3 -c '
import sys; sys.path.insert(0, "ec/tools")
from decode_index_table import trampoline_targets, READER_SITE
t = trampoline_targets(open("ec/firmware/GMxMGxx_11.800", "rb").read())
imms = [v[1] for v in t.values()]
print("%d trampolines, entries 0x%04X-0x%04X" % (len(t), min(t), max(t)))
print("immediates 0x%04X-0x%04X, %d below 0x8000, %d equal to 0x%04X"
      % (min(imms), max(imms), len([i for i in imms if i < 0x8000]), READER_SITE[1],
         len([i for i in imms if i == READER_SITE[1]])))
'
403 trampolines, entries 0x1150-0x1ABC
immediates 0x8031-0xFE00, 0 below 0x8000, 0 equal to 0x7151
```

All 403 immediates are at or above `0x8000` and **none** is `0x7151`, so no
trampoline names the reader and no trampoline caller is a call site the scan
missed. That is also what the structure predicts independently: the block is
common-area, and a trampoline naming a target below `0x8000` would be naming
common-area code, which is mapped in every bank and needs no switch. This is a
bounded negative for this image, not a claim about the other 402 immediates —
**#48's actual work, decoding and labelling what they point at, is untouched
and stays open.**

## The PD image: three dispatchers, and a third that nothing names

`pd_index_tables.py` runs the same search over `pd-image` and imports the
shapes, `decode_table()`, `malformed()` and `reader_call_sites()` from
`decode_index_table.py`, so the two readings of the same prologue cannot drift
apart. 93 tier-1 candidates, 5 corroborated, 3 named by an `lcall`.

```console
$ python3 ec/tools/pd_index_tables.py
```

| reader | shape | entry stride | `lcall` sites | well-formed under a 3-byte reading |
|---|---|---|---|---|
| `0x119C` `dispatch_code_table` | `pop-dph-dpl-selector-r0` | 3 | 9 | 8 of 9 |
| `0x11C2` `dispatch_code_table_2byte_key` | `pop-dph-dpl-selector-r0` | **4** | 16 | 2 of 16 |
| `0x11EF` *(unnamed)* | `pop-dph-dpl` | **6** | 3 | 0 of 3 |

The 9 and 16 are the committed figures: `pd_image_census.py`'s
`CODE_TABLE_DISPATCHERS` already counts them, and this tool reconciles its own
per-dispatcher site counts against that function so the two cannot disagree
silently. **322 bytes of the PD image are read as table data by this method**,
and the full 28-row census — every candidate site, failures included — is
[`pd-index-table-spans.csv`](../../ec/annotations/pd-index-table-spans.csv).

### `0x11EF` is new, and is only findable by the widened search

It has no `mov r0,a` at entry: the selector save happens *after* the two
zero-tests, so the five-byte literal misses it and only the bare
`pop dph ; pop dpl` plus a `movc` in the window finds it. Its three call sites
are at file `0x224FE`, `0x22867` and `0x2BCEE`. Nothing in the tree names this
routine; the first two of its sites are also at 24/24 and 22/24 frame anchors.

### Two of the three are not this family's layout, and the CSV says so per row

The entry stride is read off each reader's own loop — the `inc dptr` run that
feeds the branch returning into its zero-test — not assumed, and the same
derivation returns 3 for the main EC's `0x7151` so it means the same thing in
both images. It gives **3, 4, 6**. The two non-3 readers take the pointer off
the return address exactly as the main EC's does; what differs is how many key
bytes an entry carries, and so how many bytes it occupies. `0x7151` compares
**one** key byte against `r0`; `0x11C2` compares **two**, at entry offsets 2 and
3, against `B` and `r0`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x11dd; pd 8' /tmp/pd.bin
        ╎   0x000011dd      7402           mov a, #0x02
        ╎   0x000011df      93             movc a, @a+dptr
       ┌──< 0x000011e0      b5f006         cjne a, b, 0x11e9
       │╎   0x000011e3      7403           mov a, #0x03
       │╎   0x000011e5      93             movc a, @a+dptr
       │╎   0x000011e6      68             xrl a, r0
       │└─< 0x000011e7      60e9           jz 0x11d2
       └──> 0x000011e9      a3             inc dptr
```

and `0x11EF` compares **four**, at offsets 2 to 5, against `r4`-`r7`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1209; pd 9' /tmp/pd.bin
            0x00001209      7402           mov a, #0x02
            0x0000120b      93             movc a, @a+dptr
            0x0000120c      6c             xrl a, r4
        ┌─< 0x0000120d      7012           jnz 0x1221
        │   0x0000120f      7403           mov a, #0x03
        │   0x00001211      93             movc a, @a+dptr
        │   0x00001212      6d             xrl a, r5
       ┌──< 0x00001213      700c           jnz 0x1221
       ││   0x00001215      7404           mov a, #0x04
```

All three dispatch through `jmp @a+dptr` — at `0x11B6`, `0x11DC` and `0x1208`
respectively — which carries no address for any of the three committed byte
scans to resolve an edge out of, exactly as §9 records for the main EC's
`0x716B`. So `decode_table()`'s 3-byte `[address, address, case]` reading is
the wrong rule for the two non-3 readers, and what its failures mean is
specific to each:

- **`0x11C2`, 16 sites, 14 failing.** "Case values not strictly ascending" is
  what reading a 4-byte entry's second key byte as a case value looks like. The
  two that *pass* — `0x283CF` and `0x292EF`, 4 entries each — pass by
  coincidence, and `reader_stride=4` in the row is what stops that being read
  as a clean table.
- **`0x11EF`, 3 sites, 0 passing.** All three decode to a single entry: the
  key bytes at entry offsets 2 and 3 of a 6-byte entry are `00 00`, which the
  3-byte reader takes as a terminator. **The zero is pinned as a zero** and is
  a statement about a rule, not about those tables. Its 6-byte stride, its
  four-key compare chain and its `00 00` key bytes are all in the bytes; the
  full entry layout of this reader is not decoded here and is not claimed.
- **`0x119C`, 9 sites, 8 passing.** The one that fails, `0x242C5`, has this
  family's stride and is the interesting one: 20 entries, cases `0x20`-`0x58`,
  failing both "strictly ascending" and "the byte after the table is one of its
  own targets". All that says is that it does not read as a **well-formed**
  table of this family — a real table with out-of-order case values would fail
  the same way, and nothing here decides between those and the reading. It
  keeps its row, and it is the one site in this census where reading the bytes
  by hand is the next step rather than a settled verdict.

**A PD well-formedness check is a weaker check than the same check in the main
EC, and that is a property of the region, not of the code.** `malformed()`
requires every target and the default to resolve inside the caller's own region.
In the main EC that means *banked*: below `0x8000` is common area, at or above it
is the caller's own bank. `REGIONS` gives the PD image base `0x0000`, so the
identical test there asks only for a `0x0000`-`0xFFFF` CODE address — which in a
flat 64 KiB program is most of the address space, and is a correspondingly
weaker discriminator. The other two checks are unchanged. Nothing in this
section upgrades a PD verdict; the 8-of-9 above is 8 tables in a flat image
under one weakened check plus two unchanged ones.

## What this does not say, and what it leaves open

- **The nine `bank0` candidates are not "not readers" in the sense of
  something being there.** They are ordinary code, and the reading above is what
  they are: a DPTR saved and restored around a read. What is settled is that
  they are not inline-table readers, which is the question the search asked.
- **Zero is zero, here and in the PD.** A count this method did not find is
  "not found by this method". §9's "no `bank1` call site" stays that sentence;
  the widened search does not change it, because 0x7151 is common-area and a
  `bank1` caller would look identical to the 15 that are found. The 5 `bank1`
  prologue candidates are among the 36 and none is called.
- **The computed-caller blind spot is untouched.** A `jmp @a+dptr` dispatch, an
  `ljmp` thunk, or any caller reaching `0x7151` by arithmetic rather than by an
  `lcall` byte is still invisible to `reader_call_sites()`, and no amount of
  widening this search changes that. §9's sentence stands with the trampoline
  half answered and this half still open.
- **The `?C?CCASE` name is still a name for the idiom, not a symbol.** Nothing
  here reads it out of either image; what both images show is the same shape
  spelled by the same compiler runtime, and of the PD's three readers two carry
  the `mov r0,a` at entry and one saves the selector after the zero-tests
  instead.
- **Nothing behavioural.** No register was read, no `status:` in
  [`registers.yaml`](../../ec/annotations/registers.yaml) moves, no live
  observation is claimed, and no handler of any of the 15 main-EC tables or the
  10 PD spans this method calls well-formed was walked. Of those 10, two are
  under the 4-byte reader and are not a statement about a table at all — the
  8 under `0x119C` are the only PD spans this method both decoded and checked
  as tables of this family.

## Feeds

- **#48** (decode and label the 403 trampoline DPTR immediates) is **not**
  blocked on this and this is **not** a substitute for it. The narrow question
  — does any trampoline land on `0x7151` — is answered here; the 402 other
  immediates are untouched and stay open.
- **#36** (the general inline-argument-after-`lcall` convention in the PD image)
  is fed its input: the 28 rows of
  [`pd-index-table-spans.csv`](../../ec/annotations/pd-index-table-spans.csv) are
  the data this PR adds, and *changing* `pd-xdata-span-sites.csv` to subtract
  them is #36's change, not this one's.
- **#26** (characterising the PD image as an RE target) is fed a result: its
  dispatch surface has three entry points, not the two the committed census
  names, and two of the three walk tables of a different layout than the main
  EC's. Not attempted here beyond that.
- **`jmp @a+dptr` at `0x11B6`, `0x11DC` and `0x1208`** — the computed dispatch
  at the end of each PD reader, and `0x716B` in the main EC — is what no byte
  scan in this tree resolves an edge out of, so none of these tables' handlers
  has a caller edge recorded anywhere. Still #41's input, still undecoded.
- **Reading `0x242C5` by hand** — the one PD site whose stride is this family's
  and whose bytes fail the checks, above — is the one place this census hands
  on an open question rather than a verdict.

## Reproducing

No hardware, no Ghidra, no network; every input is a committed file. Both
self-tests print one line per assertion before the verdict — 37 from
`decode_index_table.py`, 16 from `pd_index_tables.py` — and the committed
spans CSV comes back byte-identical.

```console
$ python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --self-test
  ok   12 enumerated shape(s), longest pattern first, ...
  ...
self-test passed
$ python3 ec/tools/pd_index_tables.py --self-test
  ok   the 'ITE8850-PD' marker is at file 0x20040, ...
  ...
self-test passed
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
$ python3 ec/tools/pd_index_tables.py --spans-csv > ec/annotations/pd-index-table-spans.csv
```

The main-EC self-test keeps every assertion §9 and §10 were built on — the
reader at `0x07151`, its 38 hand-decoded bytes, the 15 `lcall` sites, the 15
spans, 663 table bytes, the 133 phantom rows split 9/52/72, and the two
23-of-24 weak sites — and adds the widening, the nine lookalikes, the
direct-address bucket and the three trampoline figures. `decode_index_table.py
--self-test` running the census under a *found* reader rather than a hard-coded
address is what would go red if a second one ever appeared.
