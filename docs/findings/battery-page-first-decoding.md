# The only committed record of the EC's whole XDATA page decoded for the first time, and the cycle count steps mid-charge because a routine in the tree already increments it (issue #1202)

[`evidence/battery-traces/2026-09-09-profiles.csv`](../evidence/battery-traces/2026-09-09-profiles.csv)
is the repository's only committed record of what the EC's entire `0x00`-`0xFF`
XDATA page does over a charge cycle: its `ec_hex` cell is 256 bytes on every
row, and until now nothing in the tree had ever decoded it.
[`battery-trace-column-drift.md`](battery-trace-column-drift.md) records that
the script shape which produced the file "appears nowhere outside the file
itself" and closes that question as **not found by this method** — the right
reading of *the writer*, and the wrong place to stop, because the file's
richest column was unread. This page decodes it with a new tool,
[`ec/tools/battery_page_census.py`](../../ec/tools/battery_page_census.py), and
follows the two offsets the page raises questions about into the firmware.

Nothing here is hardware evidence. No EC was opened, no register was read back,
and every figure below is re-derived from that committed CSV by a command in
this repository.

## 1. Reading the page

```console
$ python3 ec/tools/battery_page_census.py
evidence/battery-traces/2026-09-09-profiles.csv: 162 row(s), 256 page bytes
per row, 39 offset(s) took more than one value
```

The tool walks each `ec_hex` cell and reports, per offset: whether the byte
moved and over what range, whether it is half a little-endian pair tracking a
quantity the same row reports in its own columns, and whether `registers.yaml`
has a row for `0x0400 + offset`. It writes nothing and needs no hardware.

**Offset `o` is XDATA `0x0400 + o`, and that arithmetic is unmasked on
purpose.** Masking to `addr & 0xff` collapses every page onto one another, so
offset `0xA4` would resolve to whichever of `0x04A4` and `0x07A4` the map
happens to hold and report phantom matches against registers this page does not
contain. The base address is worth stating because nothing in the tree records
it: it is fixed by the fact that offset `0x34`/`0x35` equals the row's own
`current_now / 1000` and offset `0x38`/`0x39` its `voltage_now / 1000`, which
places the window on the page holding `BAT_CURRENT_MA` and `BAT_VOLTAGE_MV`. A
page-based-at-anything-else reading cannot make those two identities hold.

## 2. What moved, and what the map already calls it

Thirty-nine of the 256 offsets took more than one value. Most already have a
`registers.yaml` row, and that row is where the result belongs — the page is
not a source of new names for bytes the tree has already named:

```console
$ python3 ec/tools/battery_page_census.py
  0x0434 (offset 0x34)  moved 54 distinct 0x0A-0xFC  tracks current low half (155 row(s))  registers.yaml: BAT_CURRENT_MA (present-untested)
  0x0438 (offset 0x38)  moved 62 distinct 0x08-0xFC  tracks voltage low half (162 row(s))  registers.yaml: BAT_VOLTAGE_MV (present-untested)
  0x043E (offset 0x3E)  moved 16 distinct 0x24-0x3D  registers.yaml: CPU_TEMP (confirmed-working)
  0x044F (offset 0x4F)  moved 14 distinct 0x22-0x35  registers.yaml: GPU_TEMP (confirmed-working)
  0x04A6 (offset 0xA6)  moved 3 distinct 0xBD-0xBF  registers.yaml: BAT_CYCLE_COUNT (confirmed-working)
  0x04A4 (offset 0xA4)  moved 53 distinct 0x0A-0xFC  tracks current low half (157 row(s))  registers.yaml: XDATA_04A4 (present-untested)
  0x04A5 (offset 0xA5)  moved 11 distinct 0x03-0x0E  tracks current high half (157 row(s))  registers.yaml: XDATA_04A5 (unknown-not-absent)
```

The offsets that moved with **no** `registers.yaml` row are the ones this
capture newly says something about:
`0x0461`, `0x0469`, `0x046A`, `0x046F`, `0x0480`, `0x0490`, `0x0491`,
`0x04AB`-`0x04AE` and `0x04FC`. What any of them *means* is a firmware
question this page does not answer; §5 says which is worth following up.

## 3. The two pairs that track a quantity the row already reports

Three little-endian pairs on the page equal a value the same row carries in
`current_now` or `voltage_now`. None of them is an identity, and the rows they
miss are the evidence:

| pair | equals | rows matching |
|---|---|---|
| `0x0438`/`0x0439` | `voltage_now / 1000` | every row |
| `0x0434`/`0x0435` | `current_now / 1000` | all but seven |
| `0x04A4`/`0x04A5` | `current_now / 1000` | all but five |

The misses are all `Discharging` rows, and they are the same shape of error in
both pairs: the capture's sysfs read and its page dump are taken a moment apart,
so a pair that moved between the two reads lags the row's own column. That is
why `0x0434` is described in the tree as the current reading and not as *the*
current reading, and it is the reason this page does not call either pair an
identity.

`0x0434`/`0x0435` is `BAT_CURRENT_MA`, already a row.

## 4. `0x04A4`/`0x04A5`: a second current reading, and which one is written

`0x04A4`/`0x04A5` equals `0x0434`/`0x0435` on every row but two, and on those
two it matches its own row's `current_now` where `0x0434` does not — the two
disagree by 68 mA and 170 mA, both `Discharging` rows, both the timing skew
above. On its own that is a correlation and nothing more, and this page does
not assert which address is the copy.

**What the tree already holds is a writer, and it settles the direction.** The
census resolves `0x04A4`'s one EC-side site to bank1 `0xB4B6`, inside
`FUN_CODE_b43b` ([`ec/decompiled/bank1/B43B.c`](../../ec/decompiled/bank1/B43B.c)) —
the same routine that stores `0x0434` at `0xB487`. Both stores are
`write_r1r2_to_xdata_pair`:

```console
$ grep -n "0x434\|0x4a4\|lcall    0x888c" ec/decompiled/bank1/B43B.asm
45:B487     90 04 34 mov      DPTR, #0x434
46:B48A     12 88 8c lcall    0x888c
66:B4B6     90 04 a4 mov      DPTR, #0x4a4
67:B4B9     12 88 8c lcall    0x888c
```

So the two addresses are written by one routine through one accessor, twenty
lines apart. `0x04A4` is **write-only** in the census — `xdata-inc-dptr-only.csv`
gives it seven references and no reads, against `0x0434`'s sixteen including
reads — so the direction of the copy is settled by static evidence even though
which value the EC treats as authoritative is not.

**One detail this corrects, because the natural reading of "the same routine"
is wrong.** The two stores are not fed by the same source. Each is reached from
its own arm of the routine: a short-circuit taken when `0x0432` reads zero, and
otherwise a `read_xdata_pair_to_r1r2` of that arm's own address — `0x50A` for
the `0x0434` store, `0x50E` for the `0x04A4` one. So this is one routine
publishing two readings from two sources, not one value written twice, which is
consistent with the two addresses disagreeing on two rows and is why the
capture's disagreement is evidence about the sources rather than about a copy.

Both addresses gained rows in `registers.yaml`: `0x04A4` at `present-untested`
(it has an EC-side site), `0x04A5` at `unknown-not-absent` (all three of its
sites are in the PD image, which is another program's byte at the same address
number — see `ec/annotations/xdata-register-map.md` and
`ec/annotations/pd-xdata-overlap.md`).

**`0x04A5` is entered on a different warrant than the other, and that is worth
saying rather than leaving to the census's `entered` column.** It is one of the
107 `inc DPTR`-only bytes `ec/annotations/xdata-inc-dptr-only.md` governs, and
that page's rule admits a byte on a direct main-EC `MOV DPTR` site, which
`0x04A5` does not have — every site the scan finds is the PD image's. It was
entered on the capture instead: the byte takes more than one value here, tracks
the row's own `current_now / 1000` as the high half of the `0x04A4` pair, and
the main EC's writer for that pair is the named one in §4. So the rule still
describes what admits a byte on static evidence, and this is the first entry in
that population made on a committed observation instead.

## 5. `0x04A6`: the count steps mid-charge, and the tree already says why

`BAT_CYCLE_COUNT` reads 445, then 446, then 447 across this capture, and both
steps happen while charging — at 33% and 83% capacity. `registers.yaml` records
that this count selects a charge-voltage derating tier
([`ec/annotations/charge-target-derating.md`](../../ec/annotations/charge-target-derating.md))
and gates a DSDT capacity rescale, so a counter that steps inside one session is
worth explaining.

**The explanation is already in the tree, and this page's first pass got it
wrong.** The working assumption here was that `0x04A6` is only ever copied
from `0x0343` and is never incremented where it is written, which would make
the mid-session steps a value arriving over the `0x1C00` path rather than a
count the EC keeps itself. That is refuted by a routine the tree already names
and annotates: bank1 `0xD34B`, `bump_counter_mirror_to_04a6_04a7`
([`ec/decompiled/bank1/D34B.c`](../../ec/decompiled/bank1/D34B.c),
`ec/annotations/ghidra-functions.csv`).

```console
$ sed -n '7,21p' ec/decompiled/bank1/D34B.asm
D34B     90 03 49 mov      DPTR, #0x349
D34E     e0 - -   movx     A, @DPTR
D34F     c3 - -   clr      CY
D350     94 c8 -  subb     A, #0xc8
D352     40 2a -  jc       0xd37e
D354     e4 - -   clr      A
D355     f0 - -   movx     @DPTR, A
D356     79 00 -  mov      R1, #0x0
D358     90 03 43 mov      DPTR, #0x343
D35B     e0 - -   movx     A, @DPTR
D35C     c3 - -   clr      CY
D35D     24 01 -  add      A, #0x1
D35F     50 02 -  jnc      0xd363
D361     79 01 -  mov      R1, #0x1
D363     f0 - -   movx     @DPTR, A
```

Read as a whole: when the byte at `0x0349` reaches `0xC8`, zero it, add one to
the 16-bit value at `0x0343`/`0x0344`, and mirror both halves to `0x0528`/`0x0529`
and to `0x04A6`/`0x04A7` — the `0x04A6`/`0x04A7` half is the same
`mov DPTR,#.. / movx @DPTR,A` pair repeated, which is why the excerpt stops
before it. The increment is the EC's own, gated on a counter byte this capture
does not contain: `0x0349` sits below the page's `0x0400` base, so **which path
produced either step is not settled by this file**, and this page does not pick
one.

Two things follow that are worth stating plainly, because both are corrections
of a natural reading rather than new findings:

  * **The carry makes `0x04A6` the low half.** `D34B` increments `0x0343` and
    carries *into* `0x0344`, so `0x0343` is the low byte and `0x04A7` the high
    one. Read little-endian the capture's `0xBD 0x01` is 445 — the value
    `registers.yaml` already recorded. Read big-endian it is 48385, which is
    not a cycle count, so the byte order here is settled by arithmetic rather
    than by assumption.
  * **`0x04A7` never moves in this capture.** The high byte holds `0x01`
    throughout, so the two steps are visible in the low half alone. That is
    what a count in the hundreds looks like, and it is consistent with the
    decode; it is not independent evidence for it.

`0x04A6`'s `status` stays `confirmed-working`. Its warrant is the live read
already in the file, and nothing in a capture of a committed CSV strengthens or
weakens it; what is added is the note recording both transitions and the
`0x0343`/`0xD34B` path that maintains the pair.

## 6. `0x04AB`-`0x04AE`: the most promising unknown

Four adjacent unnamed offsets, and `0x04AB` equals `0x04AC` on every row but
two — the same near-duplicate shape `0x04A4`/`0x0434` has, at a much higher
distinct-value count. That is a lead, not an identification: what the quartet
holds needs the firmware, and this capture cannot supply it. It is the obvious
next piece of work, and it is deliberately not started here.

## What this does not establish

- **That any of this is a behaviour.** Every figure is read out of a committed
  CSV by a tool in this repository. No register was read, written or read back;
  no site was seen run. A byte that moved is a byte the EC touched during that
  window, which is a weaker claim than one it acts on.
- **Byte-position correlation is not identification.** That a cell equals
  `current_now` is a fact about a file of rows. `0x04A4` is the standing
  counter-example inside this very capture — it tracks the same quantity from a
  different address, and §4 names the writer instead of inferring from the
  coincidence.
- **Which path stepped `0x04A6`.** `0xD34B` increments the pair, and
  `0xDEE8`/`0xDEF1` copy it from `0x0343`; the gate byte that decides between
  them, `0x0349`, is outside the captured page. Two writers, one observed
  effect, no tie-break.
- **Which of `0x0434` and `0x04A4` the EC treats as authoritative.** The
  census settles that `0x04A4` is never read, not that its value is unused.
- **That the moving offsets with no row have any particular meaning.** They are
  named as having moved; §6 is a lead, not a result.
- **That this capture's shape had a writer.** `battery-trace-column-drift.md`'s
  "not found by this method" stands and is not retracted here — this page reads
  what the file contains, not what wrote it.
- **Anything about the remaining captures.** The tool takes a path argument so
  another capture can be pointed at it; only this one is measured here.

## Reproducing every figure

```console
$ python3 ec/tools/battery_page_census.py
$ python3 -m unittest discover -s ec/tools -p "test_battery_page_census.py"
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x04A4 --counts-only
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x04A5 --counts-only
```

The suite computes its own expectations from the committed bytes rather than
reading them back out of the tool, so a byte-order or off-by-one error inside
the census fails on the value instead of agreeing with itself.