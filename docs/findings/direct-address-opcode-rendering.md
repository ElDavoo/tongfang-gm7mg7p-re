# Six `direct`-destination opcodes the decoder printed as data, and the four committed tables that inherited it

(2026-09-29, issue #1294. Static reading of committed files: the firmware image, the
committed Ghidra listings, and the committed annotation tables. No capture opened,
no EC, no hardware, no Windows.)

`disasm8051.mnemonic()` had no case for `0x42`/`0x43` (`ORL direct,A` /
`ORL direct,#data`), `0x52`/`0x53` (`ANL …`) or `0x62`/`0x63` (`XRL …`), so all six
fell through to `return f"db   0x{op:02x}"` at the end of the function. `db` is
the token this tree reads as *data, not code* — it is the `not-code` criterion
`ec/tools/citation_gap_scan.py` grades windows against — so a real instruction
rendered as one is a code byte reading as evidence of a data island. This records
what the six are, the oracle that settles them, the census of what the defect put
in the committed tables, and a grade of the re-cut rather than a blanket
substitution.

## The six, and the oracle that is not the tool under test

| opcode | 8051 | length | renders as |
|---|---|---:|---|
| `0x42` | `ORL direct,A` | 2 | `orl  0x%02x,a` |
| `0x43` | `ORL direct,#data` | 3 | `orl  0x%02x,#0x%02x` |
| `0x52` | `ANL direct,A` | 2 | `anl  0x%02x,a` |
| `0x53` | `ANL direct,#data` | 3 | `anl  0x%02x,#0x%02x` |
| `0x62` | `XRL direct,A` | 2 | `xrl  0x%02x,a` |
| `0x63` | `XRL direct,#data` | 3 | `xrl  0x%02x,#0x%02x` |

The oracle is the committed Ghidra listings, read from disk rather than
reconstructed from the decoder — the same discipline `disasm8051.py`'s `BIT_SITES`
and `TEXTBOOK_BIT_SITES` record, and for the same reason: an encoding derived
from the tool under test asserts nothing. Measured over `ec/decompiled/*/*.asm`,
**76 lines across 32 files** decode one of the six and all 76 name a **byte
address** as the destination — 20 `0x42`, 29 `0x43`, 5 `0x52`, 9 `0x53`, 5 `0x62`,
8 `0x63`. Five transcribed here, with the file and line each came from:

```
ec/decompiled/common/70FA.asm:12   7100     42 f0    orl      B, A
ec/decompiled/common/2632.asm:43   2667     52 66    anl      0x66, A
ec/decompiled/common/5802.asm:56   5857     43 45 47 orl      0x45, #0x47
ec/decompiled/common/2632.asm:54   2680     63 65 ff xrl      0x65, #0xff
ec/decompiled/bank1/897B.asm:21    8995     53 00 07 anl      0x00, #0x7
```

`42 f0 orl B, A` is also why the expected text in the suite carries the byte
address as well as the listings' own spelling: `0xf0` *is* `B`, and Ghidra's
SFR naming is a rendering choice the base 8051 map does not require.

Reproduce the census with:

```console
$ C='^([0-9A-Fa-f]{4,6}) +(42|43|52|53|62|63) [0-9a-f]{2}( [0-9a-f]{2})? *(-+ *)?(orl|anl|xrl) '
$ grep -rnE "$C" ec/decompiled/*/*.asm | wc -l
76
```

The optional `-+ *` is not decoration: the listings pad the byte column to a
fixed width with `-` on the two-byte rows and leave it unpadded on the
three-byte ones, so a census that does not allow for both finds 30 of the 76
rather than all of them.

## The dual encoding, recorded and not settled

The Intel manual's opcode table admits a three-byte `direct,#data` /
`direct,@DPTR` reading of `0x25`/`0x35`/`0x45`/`0x55`/`0x65`/`0x95` — the bytes
this tree renders as the two-byte `a,direct` accumulator forms. Every assembler
and compiler emits those six as `a,direct`, and that is the reading the committed
listings' framing rests on, so **`OPCODE_LEN` is unchanged** at 2 for all twelve
opcodes involved (six accumulator, six direct-destination). Nothing here resolves
the disagreement and the decoder does not take a side on it: the new cases key on
the opcode rather than the operand, so the two readings cannot collide.

Two things follow that are worth naming rather than leaving implicit. First,
`opcode_coverage.py`'s `MCS51_LEN` takes the same two-byte reading on all
twelve — verified equal to `OPCODE_LEN` for each — so `--divergence` **cannot
see** this disagreement; it compares two oracles that agree with each other for
the same reason. That is the boundary with #1155 and the reason this is a
comment rather than a `--divergence` row. Second, the new cases sit one byte
above the branch opcodes (`0x42`/`0x52`/`0x62` over `0x40`/`0x50`/`0x60`), so
the growth is a real risk rather than a formality: a decoder that widened `0x42`
into the `0x40` row would read `jc`/`jnc`/`jz` as data. The suite pins those
branches beside the six for exactly that reason.

## The census, and the grade of the re-cut

**Cells, not tokens.** The issue's "220 cells in four tables" is a token count;
the cell count is smaller because `indirect-xdata-sites.csv`'s `window` cell
holds up to 24 instructions, so 17 of its tokens sit in 10 cells.

| file | cells | tokens |
|---|---:|---:|
| `ec/annotations/bank-relative-branch-targets.csv` | 117 | 117 |
| `ec/annotations/bank-call-targets.csv` | 73 | 73 |
| `ec/annotations/indirect-xdata-sites.csv` | 10 | 17 |
| `ec/annotations/bank-paged-call-targets.csv` | 13 | 13 |
| | **213** | **220** |

Reproduce with, against the commit before the one that re-cut them — the count is
of the text this change *removed*, so on this tree it is zero, and the zero is
what `ec/tools/test_direct_address_renderings.py` asserts:

```console
$ for f in bank-relative-branch-targets bank-call-targets \
           indirect-xdata-sites bank-paged-call-targets; do
>   printf '%-34s %3s cells %3s tokens\n' "$f" \
>     "$(git show HEAD~1:ec/annotations/$f.csv | grep -cE 'db 0x(42|43|52|53|62|63)')" \
>     "$(git show HEAD~1:ec/annotations/$f.csv | grep -oE 'db 0x(42|43|52|53|62|63)' | wc -l)"
> done
bank-relative-branch-targets 117 cells 117 tokens
bank-call-targets             73 cells  73 tokens
indirect-xdata-sites          10 cells  17 tokens
bank-paged-call-targets       13 cells  13 tokens
```

All four were re-cut **from the tool** (`audit_call_targets.py --csv` /
`--relative-csv` / `--paged-csv`, `find_indirect_xdata.py --csv`) and diffed
against the committed file, never hand-edited. The diff is confined to the
`earlier_record` and `window` fields: row counts and headers are identical, the
`<address> <bytes>` prefix of every changed field is byte-identical, and every
differing token in `indirect-xdata-sites.csv` is one of the six becoming its own
mnemonic. No site's `access`, `target`, `bucket`, `frame_onto` or terminator cell
moved, because none of them is derived from the mnemonic text.

**The grade — what this change does and does not claim.** It is a *rendering*
change, applied uniformly, and it makes exactly one class of claim: *the byte the
walk presents as an instruction start has a spelling, and the spelling names a
byte-addressed destination.* It does not upgrade any window to correct. A `db`
inside a real data region would be a **framing** fault rather than a rendering
one, and framing is a separate question that `converges_from()` produces evidence
about without settling — its own docstring says so, and this change does not
displace that. So the 213 cells are graded here by what is actually measurable:

- **The 203 site-table cells**, scored with `converges_from(fw, off, 24)` at
  the renamed instruction's **own** file offset — the address the
  `earlier_record` cell prints, which for a bank is already a file offset and
  needs no `offset_for_runtime()` round trip: **99** have at least one of the
  24 preceding byte anchors decoding onto them, **16** of those at the full
  24/24, and **104** have none.
- **The 10 `indirect-xdata-sites.csv` cells** sit inside the `window` of a `movx`
  site, and it is the *site's* framing the table records: `frame_onto` is 21, 23
  or 24 for all ten, so every one of those windows is strongly framed.

**Correction (2026-09-30, issue #1294 review).** The bullet above carries
99 / 16 / 104. The first pass of this write-up carried **166** anchored, **110**
at 24/24 and **37** unanchored, and claimed the 37 were "all in `common` and
`bank0` — never `bank1`". Both halves are wrong, and the headline is the part
that matters. The score has to be taken at each cell's own file offset, and
`offset_for_runtime()` returns `None` for all 97 `bank1` cells — the first pass
counted those as anchored. They are scorable, and scoring them the way their own
column already scores itself settles it: `frame_onto`/`frame_over` reproduce
`converges_from()` at each row's own `file_offset` in **18,555 of 18,555** rows
across the three tables, banks included. Re-run, **104 cells have no anchor, not
37 — and 67 of them are in `bank1`.**

**What the 104 are, and the shape that inverts the first reading.** They split
24 `common` + 13 `bank0` + 67 `bank1`, and the two halves behave differently:

- The **37 in `common` and `bank0`** are scattered — a median gap of 473.5 bytes
  — so they are not one contiguous data table being renamed wholesale. That is
  still true, as a statement about *that subset*.
- The **67 in `bank1`** are the clustered ones: a median gap of 94 bytes, 46 of
  the 67 (69%) within 64 bytes of another, and four clusters of three or more
  cells inside 32 bytes — `0x13387`–`0x13398`, `0x1357a`–`0x1359e`,
  `0x13f4f`–`0x13f8e`, and the largest, four cells at `0x143df`–`0x14418`. The
  first pass's "never `bank1`" is what let the scatter argument stand
  unqualified, and these four clusters are exactly the shape a genuine data
  island would have.

**Checked against both committed readings, and the positive one says code.**
`ec/annotations/data-regions.yaml` has **no** recorded region inside `bank1` at
all, so none of the 67 is one — which is a weaker statement than it looks, since
that file's own header says it is "the set one reading turned up, not a
code/data separation of the image": *not found by this method*, never *absent*.
The other committed reading is a positive one, and it does not say table. All 13
cells of the four clusters sit inside committed `bank1` listings, and the
listing decodes those bytes as a whole 3-byte instruction the walk arrives two
bytes into: `ec/decompiled/bank1/C3CD.asm:14` reads
`C3DD  12 88 63  lcall 0x8863`, and the renamed record at file `0x143df` —
`0x143df 63 40 41 xrl 0x40,#0x41` — is that `lcall`'s **last byte**. The other
twelve are the same shape: ten more `lcall 0x8863`, and two on
`90 05 42  mov      DPTR, #0x542` (`ec/decompiled/bank1/B33B.asm:40`). There is
no tie-break to blame, either. At each of the 13 sites `off-2` is a two-byte
opcode — `0x88` eleven times, `0x05` twice — that ends exactly *at* the site, so
`earlier_record()`'s strict "spans the site" test excludes it and the misframed
`off-1` is the only surviving candidate. So the clustering is a **framing**
observation about a walk anchored *inside* the instruction rather than before it
— a finding for the walk's framing to record, and not one this rendering change
can settle either way.

**Two of the 104 are a framing fault in fact, not in prospect.** The same check
puts `0x05621` and `0x05629` — both `common` — inside the recorded region
`common-055a8-be-words`: `0x05621` is the low byte of the descending word
`0x0162` and `0x05629` the low byte of `0x0142`, and the re-cut spells them
`xrl 0x01,a` and `orl 0x01,a`. That is the case this grade exists to catch, and
it is two cells rather than none of them. Nothing here makes the spelling wrong
— the byte still has the encoding the manual gives it — but the count is not
zero, and a grade that reported zero would have been reporting the part of the
set nobody had looked at.

Reproduce the whole grade with:

```console
$ PYTHONPATH=ec/tools python3 - <<'EOF'
import csv, re, statistics as st
import disasm8051 as D, data_regions as DR
NEW = re.compile(r'^0x([0-9A-F]{5}) (?:[0-9a-f]{2} )+(?:orl|anl|xrl) 0x[0-9a-f]{2},'
                 r'(?:a|#0x[0-9a-f]{2})$')
fw = open('ec/firmware/GMxMGxx_11.800', 'rb').read()
cells = []
for f in ('bank-relative-branch-targets', 'bank-call-targets', 'bank-paged-call-targets'):
    for r in csv.DictReader(open('ec/annotations/%s.csv' % f, newline='')):
        m = NEW.match(r['earlier_record'].strip())
        if m:
            off = int(m.group(1), 16)
            cells.append((r['region'], off, D.converges_from(fw, off, 24)[0]))
print(len(cells), 'cells;', sum(1 for c in cells if c[2]), 'anchored;',
      sum(1 for c in cells if c[2] == 24), 'at 24/24;',
      sum(1 for c in cells if not c[2]), 'unanchored')
regions = DR.load()
un = {reg: sorted(c[1] for c in cells if c[0] == reg and not c[2])
      for reg in ('common', 'bank0', 'bank1')}
for reg, offs in un.items():
    gaps = [b - a for a, b in zip(offs, offs[1:])]
    print('%-7s %2d unanchored, median gap %6.1f, %d inside a data region'
          % (reg, len(offs), st.median(gaps),
             sum(1 for o in offs if DR.region_at(regions, o))))
offs = sorted(un['common'] + un['bank0'])
print('common+bank0 %d unanchored, median gap %.1f'
      % (len(offs), st.median([b - a for a, b in zip(offs, offs[1:])])))
offs = un['bank1']
cl, cur = [], [offs[0]]
for a, b in zip(offs, offs[1:]):
    if b - a <= 32:
        cur.append(b)
    else:
        cl.append(cur)
        cur = [b]
cl.append(cur)
print('bank1 clusters of >=3 cells inside 32 bytes:',
      [(len(c), '0x%05x-0x%05x' % (c[0], c[-1])) for c in cl if len(c) >= 3])
print('bank1 within 64 bytes of another: %d of %d'
      % (sum(1 for o in offs if any(0 < abs(o - p) <= 64 for p in offs if p != o)),
         len(offs)))
EOF
203 cells; 99 anchored; 16 at 24/24; 104 unanchored
common  24 unanchored, median gap  463.0, 2 inside a data region
bank0   13 unanchored, median gap  754.0, 0 inside a data region
bank1   67 unanchored, median gap   94.0, 0 inside a data region
common+bank0 37 unanchored, median gap 473.5
bank1 clusters of >=3 cells inside 32 bytes: [(3, '0x13387-0x13398'), (3, '0x1357a-0x1359e'), (3, '0x13f4f-0x13f8e'), (4, '0x143df-0x14418')]
bank1 within 64 bytes of another: 46 of 67
```

The 104 are therefore **not found by this method** to be instructions, which is not
the same as not being instructions: `converges_from()`'s own docstring says a
site nobody syncs onto may be preceded by data that no linear walk can decode
into alignment. The 13 above are the same mechanism read from the other side — a
walk anchored *inside* the instruction rather than before it. Where a record is
later shown to sit in a genuine data region, the correct fix is the walk's
framing, not the renderer's spelling, and `0x05621`/`0x05629` are that case
already in hand.

## What §3 of `dptr-rebuild-walk-guard.md` deferred, measured

[dptr-rebuild-walk-guard.md](dptr-rebuild-walk-guard.md) §3 declines to treat an
in-place DPTR modify as a terminator, and deferred the question of the class's
population. It is answered now, and the answer is a null recorded as one:

- The twelve byte pairs `42 82`, `43 82`, `52 82`, `53 82`, `62 82`, `63 82` and
  their `… 83` equivalents occur **0 times each** in
  `ec/firmware/GMxMGxx_11.800`.
- Driving `trace_xdata_refs.walk_why()` from all **10,414** mapped
  `MOV DPTR,#imm16` sites finds **no** window containing an in-place modify of
  DPTR in any form — none of the six with an `0x82`/`0x83` operand, none of
  `inc 0x82`/`0x83`, `dec 0x82`/`0x83`, `xch a,0x82`/`0x83`. So no counted
  `movx` sits behind one.

**What bounds that null**, because it is a statement about a method and not about
the image. It is a linear walk, so it stops where `walk_why()` stops: at a flow
opcode (7,224 of the 10,414 windows), at a DPTR reload (2,977) or at the budget
of 8 instructions (213). Raising the budget to 16, 32 and 64 while honouring the
same two terminators still finds **zero** — so the null is bounded by the
terminator set, not by the budget, and that budget sweep is what carries it. A
second figure — a walk ignoring the terminators and running 64 bytes regardless,
which found 26 — is **withdrawn rather than re-derived**: it counted instruction
hits while its sentence was worded about windows, and no committed table pins
that walk's framing, so re-running it would be a choice of method rather than a
re-measurement. A null that holds across four budgets does not need a supporting
number whose own definition is unpinned.

§3 keeps its **decision** — the guard still does not stop on these, and
`is_dptr_rebuild()`'s scope is unchanged by this work — and now states the
class's population instead of deferring it. Widening the guard remains the
separate change with its own census behind it, which is what §3 already said.

## Named stale: the `db` count is now 29, and two files still say 35

`docs/findings/opcode-table-coverage.md` and `ec/tools/opcode_coverage.py` both
say **35** opcode values reach `mnemonic()`'s `db` return. With the six named
here, that is **29**, measured the same way:

```console
$ python3 -c "import sys; sys.path.insert(0,'ec/tools'); import disasm8051 as D; \
    print(sum(1 for op in range(256) if D.mnemonic(bytes([op,0,0]),0).startswith('db')))"
29
```

**Left uncorrected on purpose.** Both are long shared files a concurrent branch is
likely inside, and per `CLAUDE.md` a new write-up takes a pointer rather than
growing one. The figure is flagged here with the command that re-derives it; the
edit belongs to a branch that owns those files. The four map-unassigned bytes
`0x06`/`0x07`/`0x16`/`0x17` that `citation_gap_scan.UNASSIGNED` depends on are
unaffected and still render `db`, and the suite pins that they do.

## What this does not establish

- **Nothing about what the EC does.** Every input is a committed file. "213 cells
  changed" is a claim about what this decoder renders over these four tables, and
  `disasm8051.py`'s own docstring is the standing reason a linear walk anchored
  mid-instruction decodes the garbage that follows.
- **That the 213 renamed bytes are 213 instructions.** See the grade above. The
  104 without an anchor are *not found by this method* to be framed — 13 of them
  are positively read as the tail of a 3-byte instruction the committed
  listings decode whole, and 2 sit inside a recorded data region, and neither
  fact is settled by giving the byte a spelling.
- **Anything about the dual encoding above.** Both readings are recorded with
  their oracle; neither is settled here, and `--divergence` is blind to it by
  construction.
- **That widening `is_dptr_rebuild()` is safe.** The measurement above says the
  class is empty in the windows this tool walks. It says nothing about windows a
  different walk would produce, and §3's decision is unchanged.
- **Any hardware or Windows step.** None is needed and none is claimed.

## Reproducing it

```console
$ python3 ec/tools/disasm8051.py --self-test
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/citation_gap_scan.py --check
$ python3 ec/tools/test_direct_address_renderings.py
```

`citation_gap_scan.py` is on the list because `ec/ghidra/gap-citation-scan.csv`
is a fifth committed file the re-cut reaches, and the gate catches it when one is
missed: its `db` column counts `db` bytes in a window, and the one row it moves
is the `not-code` pair. The suite is
[`../../ec/tools/test_direct_address_renderings.py`](../../ec/tools/test_direct_address_renderings.py);
the rendering contract it pins is in `ec/tools/disasm8051.py`, at the cases
themselves.
