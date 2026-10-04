# The 176 words at `0x0656`: a directory of five `ljmp` tables, read one at a time

`ec/annotations/data-regions.yaml`'s `common-0656-address-table` is the one
region in the map whose `note` said its stride was **not** uniform. Issue #1144
asked for that to be settled by reading the 176 words edge by edge instead of by
pattern. This is what they are.

Every number here is measured against the committed
`ec/firmware/GMxMGxx_11.800` by the `python3 -c` printed beside it, and every
one is a property of that binary — no change to this repository can move it.
Nothing here was observed on hardware: no EC was opened, no capture was read, no
register was read back, and no `status:` in `registers.yaml` moves. These are
code-image addresses, not XDATA.

## The headline

**The stride is uniform. What is mixed is the content, not the grid.**

All 176 words decode at stride 2 across the whole `0x0656`-`0x07B6` span. That
is why `--check` is green on it, and why the generic mutations in
`data_regions.py --self-test` — a one-byte-shifted start, a span cut one entry
short — still reject a mis-cut region here. The old `note` conflated the *grid*
with the *value pattern*, and that conflation is what made the entry look like
it needed a different shape. It does not; it needs an honest `note`.

**What the words are:** 140 of the 176 are the entry-or-end offsets of **five**
`ljmp` tables. The other 36 are ordinary common-area code addresses. The region
is a **directory**: it indexes those five tables rather than holding one kind of
value.

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read()
T=[(0x0035,0x003E),(0x0060,0x006F),(0x0126,0x012F),(0x01E3,0x01EF),(0x032F,0x0497)]
ent={o for lo,hi in T for o in range(lo,hi,3)}; ends={hi for _,hi in T}
W=[(d[o]<<8|d[o+1]) for o in range(0x656,0x7b6,2)]
print('entry',sum(1 for x in W if x in ent),'end',sum(1 for x in W if x in ends and x not in ent),
      'other',sum(1 for x in W if x not in ent and x not in ends))"
entry 135 end 5 other 36
```

## Block 1 — the 135 entry offsets and 5 end offsets

The five tables the directory names, four of which the map did not list. Extents
re-derived by the same `while d[o]==2: o+=3` walk `common-032f-ljmp-table` uses,
each seeded at its own `file_lo`:

| region | entries | targets | step |
|---|---|---|---|
| `common-0035-ljmp-table` | 3 | `0x116E`-`0x117A` | 6 |
| `common-0060-ljmp-table` | 5 | `0x1180`-`0x119E` | 6, 12, 6, 6 |
| `common-0126-ljmp-table` | 3 | `0x11A4`-`0x11B0` | 6 |
| `common-01e3-ljmp-table` | 4 | `0x11C8`-`0x11E6` | 6, then 18 |
| `common-032f-ljmp-table` | 120 | `0x11F2`-`0x14BC` | 6 |

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();o=0x1e3
while d[o]==2:o+=3
print(hex(o),(o-0x1e3)//3)"
0x1ef 4
```

Every target of the four new tables lies inside `bank-call-audit.md` §2's
`0x1150`-`0x1ABC` trampoline block, and all fifteen sit just *below* the
`0x032F` table's own `0x11F2`-`0x14BC` run — consistent with the five being one
family, and consistent is not demonstrated:

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read()
T=[0x0035,0x0060,0x0126,0x01E3]; tg=[]
for lo in T:
    o=lo
    while d[o]==2:o+=3
    tg+=[(d[x+1]<<8|d[x+2]) for x in range(lo,o,3)]
print(len(tg),hex(min(tg)),hex(max(tg)),all(0x1150<=t<=0x1ABC for t in tg),all(t<0x11F2 for t in tg))"
15 0x116e 0x11e6 True True
```

The five **end offsets** are `0x003E`, `0x006F`, `0x012F`, `0x01EF`, `0x0497` —
one past each table's last entry. `0x012F` is worth naming: it is both the end
of `common-0126-ljmp-table` and `chan_init_170a_then_jmp_11b6` in
`annotations/ghidra-functions.csv`, so a region boundary and a named routine's
entry address are the same number.

## Block 2 — 36 ordinary code addresses

These are genuine common-area addresses inside a contiguous run of them. They
stay, and the `note` now says so per class rather than leaving them unexplained.
The three sub-classes below are 19 + 11 + 9 = 39, which is three more than 36
because three words are named in two of them — `0x003E` and `0x006F` are both
low-area instruction starts and end offsets, and `0x012F` is both a routine
address and an end offset. The suite assigns each word to exactly one class.

**Nineteen are instruction starts in the low common area at `0x0000`** — not,
as issue #1144 had it, "the address byte of `ljmp 0x11xx` instructions". A
linear sweep settles what each one is: five hold an `ljmp` into the same
trampoline block, fourteen hold a `ret`, and every one is the *start* of an
instruction.

Two of the nineteen — `0x003E` and `0x006F` — are *also* one of the five table
end offsets from block 1, and are counted there; the third word named in two of
these sub-classes is `0x012F`, which is one of the eleven routine addresses
below and an end offset. The classes partition the span, so they are named here
as what they are and counted once.

**These are not all vector entries, and this page does not call them that.** The
sweep reaches instruction starts; it does not decide which of them the vector
table owns. The repository already answers that question, and its answer
contradicts four of the nineteen. `build_ec_decompile.py`'s `discover_vector_table()`
walks the EC's vector table and stops where code begins — its own self-test pins
that end at `0x002E`, not the `0x0040` a textbook layout would suggest — and on
this image it returns sixteen entries, the last at `0x002B`, so the block spans
`0x0000`-`0x002D`. Four of the nineteen — `0x003E`, `0x003F`, `0x006F`,
`0x01FF` — lie past that end and are therefore ordinary code addresses, not
vector entries. That is also why the write-up used to be internally
inconsistent: `0x003E` and `0x006F` were described in one breath as offsets into
the vector block and, a few lines up, as the *end* offsets of two `ljmp` tables.

```console
$ python3 -c "import sys;sys.path.insert(0,'ec/tools')
from build_ec_decompile import discover_vector_table
d=open('ec/firmware/GMxMGxx_11.800','rb').read()
v=discover_vector_table(d)
print(len(v),'entries, last at',hex(v[-1][0]),'-> code begins at 0x002e')"
16 entries, last at 0x2b -> code begins at 0x002e
```

The class is therefore named for what the sweep establishes and no more.

The suite below assigns each word to exactly one class, which is why its
low-area membership comes out at **sixteen** rather than nineteen. The
mechanism is its sweep window, not a third overlap: the suite derives this class
from a 40-instruction linear sweep from `0x0000`, and that sweep only reaches
`0x47`. `0x006F` and `0x01FF` therefore fall outside it and are excluded as *not
reached*, while `0x003E` is excluded as an end offset — 19 − 2 − 1 = 16. The
window is not widened to cover them, because a 200-instruction sweep reaches
`0x15A` and so also swallows `0x0114`, a `mov dptr` routine address, which fails
the same suite's own `0x02`/`0x22` assertion. The gap is closed separately:
`test_the_words_the_sweep_window_does_not_reach` verifies `0x006F` and `0x01FF`
against a wider sweep, so all nineteen are checked even though the class is not.

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0000 -n 15
0x00000  020070   ljmp 0x0070
0x00003  02052f   ljmp 0x052f
0x00006  22       ret
0x00007  021150   ljmp 0x1150
0x0000a  22       ret
0x0000b  020530   ljmp 0x0530
0x0000e  021156   ljmp 0x1156
0x00011  22       ret
0x00012  22       ret
0x00013  020556   ljmp 0x0556
0x00016  02115c   ljmp 0x115c
0x00019  22       ret
0x0001a  22       ret
0x0001b  0205b6   ljmp 0x05b6
0x0001e  021162   ljmp 0x1162
```

| the 19 | what the address holds |
|---|---|
| `0x0007` `0x000E` `0x0016` `0x001E` `0x0026` | an `ljmp` into `0x1150`-`0x1168` |
| `0x0006` `0x000A` `0x0011` `0x0012` `0x0019` `0x001A` `0x0021` `0x0022` `0x0029` `0x002A` `0x003E` `0x003F` `0x006F` `0x01FF` | a `ret` |

The last four — `0x003E`, `0x003F`, `0x006F`, `0x01FF` — are the ones past the
vector block's `0x002E` end; the rest sit inside it. Two of those four,
`0x003E` and `0x006F`, are *also* table end offsets from block 1, so the region
indexes the low common area as well as the tables.

**Eleven are routine entry addresses**, of which three are named in
`annotations/ghidra-functions.csv`:

| word | first bytes | named |
|---|---|---|
| `0x0114` | `90 11 05` `mov dptr,#0x1105` | no |
| `0x012F` | `90 17 0a` `mov dptr,#0x170A` | `chan_init_170a_then_jmp_11b6` |
| `0x018C` | `90 17 09` `mov dptr,#0x1709` | `chan_init_1709_then_jmp_11bc` |
| `0x029B` | `90 17 08` `mov dptr,#0x1708` | `chan_init_1708_then_jmp_11c2` |
| `0x02FD` | `12 00 2e` `lcall 0x002E` | no |
| `0x0312` | `90 15 10` `mov dptr,#0x1510` | no |
| `0x04A5` | `90 11 4c` `mov dptr,#0x114C` | no |
| `0x04B4` | `02 14 c2` **`ljmp 0x14C2`** | no |
| `0x04B7` | `90 11 50` `mov dptr,#0x1150` | no |
| `0x04CB` | `90 11 50` `mov dptr,#0x1150` | no |
| `0x051E` | `90 11 50` `mov dptr,#0x1150` | no |

**Nine are `0x0526`-`0x052E`**, which name a nine-byte `ret` run *elsewhere* in
the image. They are offsets pointing at padding; they are not padding, and no
word in this region is `0x2222`:

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read()
print('any 0x2222 word:',any((d[o]<<8|d[o+1])==0x2222 for o in range(0x656,0x7b6,2)))
print('bytes at 0x0526:',d[0x526:0x52f].hex(' '))"
any 0x2222 word: False
bytes at 0x0526: 22 22 22 22 22 22 22 22 22
```

## The right edge is a function's first byte

`file_hi: 0x07B6`. The word there is `0xE490` = `clr A`, the first byte of
`zero_seven_xdata_bytes_from_200b` in `annotations/ghidra-functions.csv`:

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();print(' '.join(f'{x:02x}' for x in d[0x7b6:0x7bf]))"
e4 90 20 0b f0 f0 f0 f0 f0
```

That is a better boundary than issue #1144 claimed, and it is the reason
**nothing is excluded and no terminator is added**. `0x0526`-`0x052E` is not in
the span; it is what the last nine words point at. The `addresses` shape claims
only "a word below `0x8000`" and has no terminator *by design* — a terminator
would be a claim about content this shape does not test, and this entry is its
only user. A green run on mixed content is the shape working as documented.

## Corrections to issue #1144, each re-derived before anything was edited

Left visible beside the right value, per the `docs/findings.md` §4a-4d pattern.

- **Four new tables, not five.** `0x01EC` is the **fourth entry** of the `0x01E3`
  table, not a fifth table's start. `while d[o]==2: o+=3` from `0x01E3` returns
  four entries and ends at `0x01EF`, so a region declared at `0x01EC` would
  **overlap** `common-01e3-ljmp-table`. This is the YAML header's own warning —
  a scan-site address is not a table boundary — repeated by the issue.
  `test_data_regions_0656_directory.py` holds it as a regression case.
- **The `ret` tail is nine bytes and holds no `0x2222`.** No word in the region
  is `0x2222`. The last nine words *hold* `0x0526`-`0x052E`, which name a
  nine-byte `ret` run. The issue read the target's bytes as the word's value.
- **`file_hi` is not that padding.** `0x07B6` is `0xE490`, a named function's
  first byte — see above.
- **Nine routine words in the issue's list, and eleven in all.** It named three
  already in `annotations/ghidra-functions.csv` and listed six more — nine words
  — under a heading that said eight; it omitted `0x0114` and `0x02FD`, and read
  `0x04B4` as a `mov dptr` when it is an `ljmp 0x14C2`. The table above is the
  full set. Note that `0x04B4` is why no test here asserts these addresses do
  not begin with `0x02`: a routine whose first instruction is a jump is still a
  routine, and what makes a word a table offset is its position on a table's
  stride grid, not the byte that happens to sit there.
- **The nineteen are not "address bytes".** They are instruction starts in the
  low common area at `0x0000` — and, as issue #1144's own reading did not say,
  four of them lie past the `0x002E` end `discover_vector_table()` defines, so
  they are code addresses rather than vector entries. See block 2.
- **`common-0060-ljmp-table`'s own step sequence.** Its YAML `note` described the
  steps as 6 between the first four entries and 12 into the last. The steps are
  **6, 12, 6, 6**: the 12 is between the *second and third* entries, and the step
  into the last is 6. The conclusion the note drew — that this table's targets do
  not step uniformly, unlike `common-0035-ljmp-table`'s — is right and stands;
  only the sequence was wrong, and it is corrected in place. Nothing else in the
  tree would have caught this: `--check` re-derives the extent, stride, count and
  first/last value, but never the steps *between* targets.
- **The stride claim itself.** The `note` said *not* uniform; it is uniform
  across the whole span. What is mixed is content. This is the correction that
  reaches furthest, because it is the one the corrections above were read
  through.

## The `inferred` tier stays, and why

Issue #1144 asked for the tier to be "gone or justified word by word". It is
justified, and the honest reading keeps it. `confidence` is about **how the
extent was chosen**: the right edge was picked by "walk while the word is below
`0x8000`", which is a pattern. That the edge happens to coincide with a
function boundary is corroboration, not the choice, and the tier is not a claim
about whether the bytes agree.

Promoting it to `read-by-hand` would also flip every currently-empty
`entry_aligned` cell in `annotations/bank-call-regions.csv` — a large downstream
change resting on a judgement this issue does not require. Those cells are the
rows sitting in a region of this tier, and the count moves whenever a tier or a
region changes, so the argument is better made without it; the split between
bucket-C and paged, and the command that prints it, are in
[`bank-call-regions-csv.md`](bank-call-regions-csv.md). Recorded as considered
and not taken, with the reason, so the next reader need not re-derive it.

## What this changed downstream

The four new regions label **15 `paged` sites** in
`annotations/bank-call-regions.csv` that were previously `not listed`. Each is
the same misframed-read phantom the map exists to label: a byte pair one byte
into an `ljmp 0x11xx` entry, where `0x11` is the `acall` opcode.

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read()
print(' '.join(f'{x:02x}' for x in d[0x35:0x39]), '<- 0x0036 is the 0x11')"
02 11 6e 02 <- 0x0036 is the 0x11
```

They are `entry_aligned=no`, since they sit one byte past an entry boundary. The
**bucket-C population is untouched**: no site in `0x0035`-`0x01EF` appears in
`annotations/bucket-c-codemap.csv`, so `bank-call-audit.md`'s labelled-site
figure does not move.

```console
$ python3 -c "import csv
rows=[r for r in csv.DictReader(open('ec/annotations/bucket-c-codemap.csv')) if not r['file_offset'].startswith('#')]
print(sum(1 for r in rows if any(lo<=int(r['file_offset'],16)<hi
      for lo,hi in ((0x35,0x3e),(0x60,0x6f),(0x126,0x12f),(0x1e3,0x1ef)))))"
0
```

The `inferred` tier also holds its downstream claim: every row that sits in a
region with an undefined `entry_aligned` cell is still a
`common-0656-address-table` row, and those rows still split between bucket-C and
paged. [`bank-call-regions-csv.md`](bank-call-regions-csv.md) carries the
command that prints it.

One further generated table moves, and it is worth naming because it is a census
of the sites *outside* every listed region. `annotations/bucket-c-unplaced.csv`
records each such site's nearest region and its distance, so adding four regions
re-answers that for one row: the site at `0x00181` is now 82 bytes from
`common-0126-ljmp-table` rather than 430 from `common-032f-ljmp-table`. Nothing
else about that row changes — it was `off-grid` before and is `off-grid` now, so
its verdict, its walk and its containing function are untouched, and
`bucket-c-unplaced.md`'s own aggregates (the on-grid share and the shape-decode
share) are unaffected. The table is regenerated by
`bucket_c_unplaced.py --csv` and is never hand-edited.

## Not settled by counting any of this

- **Whether the directory is a dispatch table.** These offsets *name* `ljmp`
  tables. What the tables dispatch to, and what a caller of the directory would
  do with the answer, is a separate question this page does not answer.
- **Why the low common area is in a directory of table offsets at all.** The
  nineteen offsets name `ret`s and trampoline entry points at `0x0000`, four of
  them past the vector block's own end; that they are *indexed* is measured, and
  what indexing them buys is not.
- **The `0x032F` table's own 120 targets**, and whether the four new tables'
  fifteen targets are the same kind of thing. Both belong to the companion issue
  on the six-byte trampolines in the `0x1150`-`0x1ABC` block.
- **Whether the 36 code addresses should ever be split out.** They are genuine
  addresses in a contiguous run; excluding them would need a shape for mixed
  content that no evidence here supports, and splitting the span would break the
  oracle rows binding `0x00686` and `0x0067E` to this region's name while buying
  nothing `--check` could then test.
- **The regions are not exhaustive, and their absence is not a claim.** A span
  not listed is a span this reading did not find — never "not a table". This
  file's entire subject is one method's blind spots, so `docs/findings.md` §4c
  applies to it more than to anything else in the tree.

## Re-deriving

```console
$ python3 ec/tools/data_regions.py --check ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/data_regions.py --self-test
$ python3 ec/tools/test_data_regions_0656_directory.py
```

The per-word classification above is re-derived rather than hard-coded in
`ec/tools/test_data_regions_0656_directory.py`: the suite walks the same
`while d[o]==2: o+=3` extents from the image and checks that every one of the
words falls into exactly one documented class, that `0x01EC` is an entry of
`0x01E3` rather than a fifth table, and that no two listed regions overlap.
