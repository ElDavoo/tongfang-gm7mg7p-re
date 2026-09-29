# Issue #1027's 27 is a pre-#517 measurement of the same six tables, and a rendered `window` cell has three ways to be miscounted rather than two

(2026-09-29, issue #1027. Static reading of committed bytes through
`trace_xdata_refs.py`'s own `walk_why()` and a new `dptr_rebuild_forms.py`.
No capture opened, no EC, no hardware, no Windows, no `registers.yaml` row
touched.)

Issue #1027 asked what `walk_why()`'s reload guard cannot see, and counted
what it could not see: **27 rows** across the six tables, each one with a
direct DPL/DPH store inside its `window` and each one recording
`terminator = max_insns (8) exhausted`. It also warned about the counting
trap in a `grep` for `0x82` in the same column, which returns **31**.

**Both numbers are correct and both measure a tree this repository no longer
has.** They were taken under `walk_why()`'s pre-#517 guard, which tested
`d[i] == MOV_DPTR` and nothing else. #517 widened it to
`is_dptr_rebuild()`, re-cut the six tables from the tool, and recorded the
result in [`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md) §6 --
the 27 are the rows whose `window` *and* `terminator` moved, per table
**9 + 7 + 8 + 3**, which is the issue's own table digit for digit. The `31`
is a `grep` over cells that have since been re-rendered; the same search
returns **5** today, and one of those five is a class the issue does not
name.

So the blind spot #1027 names is real, was real, and has been closed. What
is left for it is a write-down and the one part of its item 1 that no one
had done -- the census of the **read** forms, counted and explicitly
excluded -- and that is what this file and
`ec/tools/dptr_rebuild_forms.py` are.

## 1. The 27, re-measured against both guards

Restored the pre-#517 guard in a scratch copy of `walk_why()` and ran every
committed row of the six tables under each. The reproduction is §5; it
prints, verbatim:

```
table                        before: budget  of those, +store  today: budget  +store
ec-07c4-07d5-sites.csv                   16                 9              7       0
ec-07d6-07d7-sites.csv                   13                 7              3       0
ec-0x07d1-sites.csv                      10                 8              2       0
ec-0x07d0-sites.csv                       4                 3              1       0
manual-fan-ctrl-0751-sites.csv            1                 0              1       0
xdata-0400-045f-sites.csv                 1                 0              1       0
total                                    45                27             15       0
```

The pre-#517 column reproduces the issue's 27 exactly, and the per-table
split reproduces its table (9 / 7 / 8 / 3 / 0 / 0). **The 27 is a real
measurement of a real tree**, not a miscount: it is `dptr-rebuild-walk-guard.md`
§6's re-cut, restated as a census.

The `today` column is the half the issue did not have. It is **15 rows on
the budget and none of them with a store**, and the `before` 45 against the
`today` 15 is `walk-window-terminators.md`'s own 45-then-15 correction
restated per table.

### No store can be in a window today, which is stronger than "none of the 15"

`walk_why()` runs its reload guard on the instruction *after* the one it has
just decoded, so it stops **at** a DPTR store without decoding it. A window
therefore cannot contain one at all, whatever the terminator. The issue's
item 2 asked whether any `access` cell moves: none does, and the reason is
structural rather than a per-row result -- there is no committed window for a
larger budget to reach past a rebuild.
`ec/tools/test_dptr_rebuild_forms.py::CommittedWindowTests` holds that as a
rule over the six tables rather than as a list of addresses, and the case
was checked against the pre-#517 guard, where it fails on the first row.

## 2. The counting trap: three ways, not two

The issue names the right trap and describes two of the three failures. A
sweep for `0x82`/`0x83` in the `window` column over the six tables returns
**5** rows today:

| table | `file_offset` | `window` cell | what the `0x82`/`0x83` is |
|---|---|---|---|
| `ec-07c4-07d5-sites.csv` | `0x0AD99` | `movx @dptr,a ; mov r7,#0xe1 ; ljmp 0x83d6` | **a jump target address** |
| `xdata-0400-045f-sites.csv` | `0x13F42` | `mov r3,0x82 ; mov r4,0x83 ; mov a,r6 ; ...` | a read |
| `xdata-0400-045f-sites.csv` | `0x13F52` | `mov r5,0x82 ; mov r6,0x83` | a read |
| `xdata-0400-045f-sites.csv` | `0x14CBB` | `mov r1,0x82 ; mov r2,0x83` | a read |
| `xdata-0400-045f-sites.csv` | `0x16779` | `mov r2,0x83 ; mov r1,0x82 ; ret` | a read |

The four reads are the ones the issue names, and its list is otherwise
right -- with one small transcription slip, corrected here because this
file quotes the cells: `0x13F52` reads `mov r5,0x82`, not the
`mov r3,0x82` the issue gives.

**The fifth is the class the issue does not name, and it is a byte, not an
operand.** `ec-07c4-07d5-sites.csv` `0x0AD99`'s window ends on
`02 83 d6` -- `ljmp 0x83d6` -- and the `0x83` is the high byte of a **jump
target address**. A sweep that looks for the byte finds it; a sweep that
looks for an *operand* in a `direct` position does not. So a search over
rendered text has three failure modes, not two:

1. **a read mistaken for a store** -- the issue's, from the operand order
   (`mov <dst>,0x82` loads, `mov 0x82,<src>` stores);
2. **a store missed because the cell was re-cut** -- the 27 moving to `DPTR
   reloaded`, which is what happened to the number this whole section is
   about;
3. **a target address mistaken for an operand** -- the new one.

A fourth would follow from a sweep that reads `disasm8051.mnemonic()`'s text
rather than bytes, and the defect is narrower than "the logical group is
miscaptioned": **the renderer is right about the accumulator rows and wrong
about the other side of them.** It renders `0x44`/`0x54`/`0x64` correctly as
`a,#imm` and `0x45`/`0x55`/`0x65` correctly as `a,direct`, both two bytes,
which is what the machine does -- `disasm8051.OPCODE_LEN[0x54] == 2` is
right, not a defect. What it does not render at all is the `direct,A` and
`direct,#data` rows of the same group, `0x42`/`0x43`/`0x52`/`0x53`/`0x62`/
`0x63`, which it emits as `db 0x42` and `db 0x63` where the machine writes
a byte address. A mnemonic-matching sweep built on it would find the writing
half of the logical group -- the six rows that are most of what
`IN_PLACE_FORMS` is claiming for that group -- under no name at all. That is
the defect; the accumulator rows are not part of it, and neither is
`OPCODE_LEN`, which is right about `0x26`/`0x27`/`0x36`/`0x96`/`0x97` at one
byte each for the reason §3 gives.
`dptr-rebuild-walk-guard.md` §1 records the rendering defect and
`test_dptr_rebuild_guard.py` holds it as a fact about the tree -- though
§1 states it wrongly, charging the accumulator rows for it, and carries a
correction beside the wrong version as of this writing. This paragraph is
the accurate account and §1 points here; the reason the defect is named
again is that it is the reason this issue's sweep has to
classify from bytes, and the reason the three tables are written out rather
than generated. The committed Ghidra listings are what settles the group
instead, and they are the reason the claim above is stated narrowly: `54 07
- anl A, #0x7` and `42 f0 - orl B, A` are one accumulator row and one direct
row of the same group, and they are what a byte census has to tell apart.
The listings decode `45 82` as `orl A, DPL`, `63 65 ff` as
`xrl 0x65, #0xff` and `54 0f` as `anl A, #0xf` as well, which is to say
the operand order and the operand's *kind* are both readable there and in
neither of the two tools this repository carries.

## 3. The read forms, counted and explicitly excluded

Nothing in the tree counted them. `ec/tools/dptr_rebuild_forms.py` is the
census, and over the committed image at every offset it reports **602**
read-form references to `0x82`/`0x83` against **1362** store-form ones:

| bucket | opcode group | count |
|---|---|---:|
| read | `0xE5` `mov a,direct` | 62 |
| read | `0xA8`-`0xAF` `mov rN,direct` | 204 |
| read | `0xC0` `push direct` | 268 |
| read | `0x25` `add a,direct` | 49 |
| read | `0x35` `addc a,direct` | 13 |
| read | `0x85` `mov direct,direct` (source) | 4 |
| read | `0x45` `orl a,direct` | 2 |
| store | `0xF5` `mov direct,a` | 766 |
| store | `0x88`-`0x8F` `mov direct,rN` | 282 |
| store | `0xD0` `pop direct` | 258 |
| store | `0x85` `mov direct,direct` (destination) | 35 |
| store | `0x87` `mov direct,@r1` | 11 |
| store | `0x75` `mov direct,#imm` | 10 |

`0x85` appears twice because one instruction is two references: `85 83 f0`
is `mov B,DPH`, which reads DPH and writes B. Counting the destination
alone -- which is what a classifier that returns one reference per
instruction does -- loses the four source reads, and the committed Ghidra
listings decode all four at real instruction starts as `mov 0x0e,DPL` (three,
at `0x2123E`/`0x21245`/`0x2124B`) and `mov B,DPH` (one, at `0x2104F`). The
routine at `0x2104D` is the shape that makes it obvious: it saves DPTR
through the stack, `mov r0,0x82 ; mov 0xf0,0x83 ; pop 0x83 ; pop 0x82`. The
guard is right to run past the `mov 0xf0,0x83` -- its destination is B, not a
DPTR byte, and `is_dptr_rebuild()` agrees -- but a census that only ever
looked at destinations would report that routine as naming DPL once and DPH
not at all, which is the opposite of what it does.

**The 11 `0x87` are this file's own §2 false positive, found inside itself.**
Every one of the eleven `87 82` byte pairs is the middle and last byte of an
`lcall 0x8782` (`12 87 82`) -- at `0x26987`, `0x26999`, `0x269B3`, `0x269CC`,
`0x269DF`, `0x26A14`, `0x26A41`, `0x26A56`, `0x26A71`, `0x26A91` and
`0x26AC0` -- so all eleven sit mid-instruction and a decoded sweep would
find none of them. They are in the byte census for the reason every other
figure in it is: it examines every offset, so a `direct` byte that is really
a jump target's middle byte is indistinguishable from one that is an
operand. Counting them is what §2's third class looks like from the inside.

There is a third bucket, because a census whose subject is *every way the
image names DPL or DPH* needs one: **71** references from the in-place
forms (`0x05`/`0x15` `inc`/`dec direct`, `0xC2` `clr direct`, `0xC5`
`xch a,direct` and `0xD5` `djnz direct,rel`, plus the six `direct,A`/
`direct,#data` rows of the logical group that the 8052 adds), which change
the pointer without replacing it and which
[`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md) §3 declines for
a stated reason. Listing them is what keeps that decision reading as a
choice rather than as a silence. The figure was **76** until the correction
below; the five references that difference is made of were not references to
a DPTR byte at all.

**The three tables are the whole map of byte-addressed `direct` operands,
and the two classes left out are named.** That map is **44** opcodes -- 38 in
the base 8051 and the six its 8052 extension adds, which are the
`direct,A`/`direct,#data` rows of the logical group (`0x42`/`0x43`/
`0x52`/`0x53`/`0x62`/`0x63`) and nothing else. The tool's three
tables hold all 44, which
`test_dptr_rebuild_forms.py` holds against a second transcription of that map
written out from the instruction set, with a negative control beside the
assertion so the check is shown able to reject a wrong union rather than
only to accept this one. That transcription is then held against the
committed Ghidra listings in the same file's `ListingCrossCheckTests`, which
**decodes every one of the 44**: the check reads each instruction's length
out of the listings' own byte columns, and a byte-addressed `direct` operand
is a second byte, so a one-byte decode refutes the row outright.

That check is the one this section used to describe in prose while no code
performed it, and its absence is what let the five rows below survive three
review rounds. Length is the property it checks because it is the one the
listings state unambiguously; operand *kind* is not decidable from their
text, since Ghidra renders the accumulator and direct address `0xE0` both as
`A`, so `add A, @R0` and `xrl A, B` are spelled alike and only their length
separates them. What a length decides is the one-byte class, and it decides
that class soundly -- a one-byte instruction cannot carry a byte-addressed
operand. What it does not decide is `0x24` against `0x25`, two `add` forms
of the same length differing only in whether the operand is an immediate;
that stays the operand-position claim the listings' own rendering supports
and a length cannot.

The check that used to stand in that place could
not be that oracle, and it is worth being exact about why: the 256-opcode
sweep held the **store** table to `is_dptr_rebuild()`, and those two omitted
`0x86`/`0x87` `mov direct,@Ri` *together*, so they agreed on exactly the rows
that were wrong; and because it compared a store list to a store list it
never looked at the read or in-place tables at all, so the `0xA6`/`0xA7`
`mov @Ri,direct` forms and the whole arithmetic and logical group -- which is
why `0x25` and `0x35` appear in the table above at all -- were outside what
it could see. The exclusions are the **bit-addressed forms**, where a bit
address `0x82` is the low byte of SFR `0x88` and not DPL, and
**`mov DPTR,#imm16` (`0x90`)**, which names no `direct` operand at all. Both
are facts about the keying, not about the 8051.

### The five rows the committed listings refute

This section first claimed the map was 49 opcodes -- 41 in the base 8051
plus eight 8052 additions -- on the reasoning that the base 8051's `SUBB`
group is `0x94`/`0x95` alone, so `0x96`/`0x97` must be 8052 additions like
the logical group's six. **That reasoning was wrong, and so were three rows
beside it.** The committed listings decode all five as one-byte,
register-indirect, base-8051 forms naming no address at all:

| opcode | committed listing decode | instances | what it actually is |
|---|---|---:|---|
| `0x26` | `26 - - add A, @R0` | 11 | base 8051 `add A,@R0` |
| `0x27` | `27 - - add A, @R1` | 11 | base 8051 `add A,@R1` |
| `0x36` | `36 - - addc A, @R0` | 15 | base 8051 `addc A,@R0` |
| `0x96` | `96 - - subb A, @R0` | 4 | base 8051 `subb A,@R0` |
| `0x97` | `97 - - subb A, @R1` | 1 | base 8051 `subb A,@R1` |

The error was reading the opcode *neighbourhood* rather than the operand:
`0x26` and `0x36` sit beside `0x25` and `0x35`, and `0x96`/`0x97` beside
`0x95`, so all five look like the same instructions with the accumulator
spelled `direct`. Nothing does. The `-` in the middle column is the second
byte column, and there is no second byte -- which is the whole finding, and
is the property `ListingCrossCheckTests` now asserts.

Three consequences, all mechanical. The map is 44 rather than 49, 38 plus
six. The in-place bucket is 71 rather than 76, the five references being one
`0x26` pair and four `0x36` pairs that named no DPTR byte. And the claim
that `0x96`/`0x97` "appear nowhere in the listings, so those two rows rest on
the instruction set alone" was not merely imprecise but exactly inverted:
they appear five times between them, and what they appear as is a refutation.

`disasm8051.OPCODE_LEN` was named in the same place as defective for giving
those five opcodes one byte. It gives one byte because one byte is right,
and that claim is withdrawn; the renderer's defect is the one still described
above it, the `direct,A`/`direct,#data` rows it emits as `db`.

**What these numbers are, precisely.** They are a **byte census over every
offset of the file**, not a disassembly. Every offset is examined rather
than every instruction boundary, because the sweep has no way to know where
the boundaries are without a decode -- so these are byte pairs at every
offset, and they include bytes that are data, bytes in a lookup table, and
bytes in the separate PD 8051 image. Read them as *found by this method*,
never as a count of executed instructions. **None of the nineteen byte
pairs this paragraph is about begins an instruction anywhere in the
committed listings**: not one of the fourteen `87 82` and `c2 83` pairs, and
not one of the five `26 82` and `36 83` pairs. That is a claim about the
pairs and not about their opcodes, and the difference is not decorative: an
earlier wording of this paragraph made it about the opcodes, and that
version is false, because `0x87` does start three instructions
(`0D1C 87 f0`, `A351 87 01`, `EB65 87 34` -- all three `mov direct,@R1`
naming a byte that is not a DPTR one), `0x26` starts eleven (`add A, @R0`)
and `0x36` starts fifteen (`addc A, @R0`). Only the pair-wise form is what
the listings support, so that is the form kept.
This paragraph first named four forms and 19 pairs; the other two were `0x26`
and `0x36`, whose five pairs the correction above removes rather than
explains, because they were never instruction starts to begin with, which is
why they are gone from the tables and not merely absent from the listings.
Of the two forms that remain, the `0x87` eleven are *established* as the
mid-instruction accident the `0x87` paragraph above describes: all eleven
`87 82` pairs sit inside `12 87 82`, each the middle and last byte of an
`lcall` target. The `0xC2` three are **not** established the same way, and
the difference is the point rather than a footnote: two of the three `c2 83`
pairs likewise sit in an `lcall` (`12 11 c2`), but the third, at `0x06AEF`,
decodes as `clr 0x83` if the `c0 c2` in front of it is `push 0xc2` -- so it
is a reference the census may well be right about and that no listing
happens to cover. The listings are 45,661 instruction lines of a 262,144-byte
file, so **absence from them is not absence from the image**. That is what
makes these two rows the place where the byte-census framing above does the
most work, and it is why they are named individually rather than summarised
as one accident.

The same caution applies to the 10,414 of
[`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md) §1. That census
sweeps for `0x90` at every offset of this same file, and a raw byte count of
`0x90` over this image is also 10,414 -- so its "mapped sites" are a byte
census over the same population as this one, not a smaller one. The two
figures are **labelled rather than added together**: 10,414 + 1,362 + 602 +
71 would count overlapping offsets of one file, and means nothing.

## 4. What the issue's items 2, 3 and 4 already had

Stated rather than re-done, because re-cutting six CSVs that the measurement
above shows do not move is churn and a sixth terminator token is a decision
#517 already made:

- **Item 2, "re-derive the 27 with a store-aware guard and report whether
  any `access` cell moves":** done, §1 above and
  `dptr-rebuild-walk-guard.md` §6. No `access` cell moved in the six; every
  `window` cell that moved got shorter.
- **Item 3, "either a sixth terminator token or a recorded blind spot":**
  decided, `dptr-rebuild-walk-guard.md` §5. No sixth token. The five-token
  vocabulary stands, and `test_dptr_rebuild_guard.py` holds the count.
- **Item 4, "the case that says which contract it holds":** done in
  `test_dptr_rebuild_guard.py`, and the `BothGuards` pattern is applied here
  too -- to the discriminator the issue names at its counting trap rather
  than to the guard, in `test_dptr_rebuild_forms.py::DiscriminatorTests`. One
  fixture with the store, one with the jump target where the store was, and
  the verdicts asserted to differ.

## 5. Reproducing it

From the repository root. `python3` and the committed firmware are the whole
toolchain -- no Ghidra, no `analyzeHeadless`, no `ilspycmd`, no radare2.

```sh
# 1. the census the issue's item 1 asked for and the tree had not taken
python3 ec/tools/dptr_rebuild_forms.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/dptr_rebuild_forms.py ec/firmware/GMxMGxx_11.800 --csv

# 2. the 27 against both guards, per table. The "before" walk is copied into
#    the snippet rather than fetched from a pinned commit, because one line
#    is the whole difference between the two guards and the pinned-SHA dance
#    `dptr-rebuild-walk-guard.md` §9 needs is a risk a copied function does
#    not carry: it is a transcription, and the transposition that would matter
#    is `d[i] == MOV_DPTR` for `is_dptr_rebuild(d, i)`, which is the line a
#    reader can see.
python3 - <<'EOF'
import csv, os, sys
sys.path.insert(0, "ec/tools")
import trace_xdata_refs as T
from disasm8051 import FLOW_OPCODES, OPCODE_LEN, inline_arg_len, mnemonic

TABLES = ("ec-07c4-07d5-sites.csv", "ec-07d6-07d7-sites.csv",
          "ec-0x07d1-sites.csv", "ec-0x07d0-sites.csv",
          "manual-fan-ctrl-0751-sites.csv", "xdata-0400-045f-sites.csv")


def walk_why_before(d, start, max_insns=8):
    """`walk_why()` with the pre-#517 guard, `d[i] == MOV_DPTR` and nothing
    else. Copied from the current function rather than fetched from a pinned
    commit, because one line is the whole difference between them."""
    out, i, why = [], start, T.budget_end(max_insns)
    for _ in range(max_insns):
        n = OPCODE_LEN[d[i]]
        if i + n > len(d):
            why = T.SHORT_END; break
        out.append((i, d[i:i + n], mnemonic(d, i)))
        if d[i] in FLOW_OPCODES:
            why = T.FLOW_END; break
        i += n + inline_arg_len(d, i)
        if i + 2 >= len(d):
            why = T.BUFFER_END; break
        if d[i] == T.MOV_DPTR:
            why = T.RELOAD_END; break
    return out, why


def per_table(d, walk_why):
    out = []
    for name in TABLES:
        ends = store = 0
        with open(os.path.join("ec/annotations", name), newline="") as f:
            for row in csv.DictReader(f):
                insns, why = walk_why(d, int(row["file_offset"], 16))
                if why != T.budget_end(T.walk.__defaults__[0]):
                    continue
                ends += 1
                # The site's own `mov DPTR,#imm16` is the window's first
                # triple, so the store that matters is a later one.
                if any(T.is_dptr_rebuild(raw, 0) for _, raw, _ in insns[1:]):
                    store += 1
        out.append((name, ends, store))
    return out


d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
before, today = per_table(d, walk_why_before), per_table(d, T.walk_why)
print(f"{'table':28s} {'before: budget':>14s} {'of those, +store':>17s} "
      f"{'today: budget':>14s} {'+store':>7s}")
for (name, be, bs), (_, te, ts) in zip(before, today):
    print(f"{name:28s} {be:14d} {bs:17d} {te:14d} {ts:7d}")
print(f"{'total':28s} {sum(r[1] for r in before):14d} "
      f"{sum(r[2] for r in before):17d} {sum(r[1] for r in today):14d} "
      f"{sum(r[2] for r in today):7d}")
EOF

# 3. the same five rows a `grep` finds, from the committed tables
python3 - <<'EOF'
import csv, os
TABLES = ("ec-07c4-07d5-sites.csv", "ec-07d6-07d7-sites.csv",
          "ec-0x07d1-sites.csv", "ec-0x07d0-sites.csv",
          "manual-fan-ctrl-0751-sites.csv", "xdata-0400-045f-sites.csv")
for name in TABLES:
    with open(os.path.join("ec/annotations", name), newline="") as f:
        for row in csv.DictReader(f):
            w = row.get("window", "")
            if "0x82" in w or "0x83" in w:
                print(f"{name:28s} {row['file_offset']:>8s}  {w}")
EOF

# 4. the checks this change does not touch, which are what say the six tables
#    are still what the tool produces
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --check

# 5. the suite, the shape gates, and the runner's total
python3 -m unittest discover -s ec/tools -p test_dptr_rebuild_forms.py
python3 ec/tools/gen_findings_index.py --check
python3 ec/tools/check_findings_frozen.py
python3 ec/tools/check_no_append_logs.py
bash tools/run-tests.sh
```

Step 2 is the load-bearing one and its "before" is a **transcription on
purpose**. `dptr-rebuild-walk-guard.md` §9 uses a pinned SHA and spends a
page on why a relative ref fails; that is right where the difference is
several lines of a module and a wrong ref prints a plausible zero. Here the
difference is one line, it is the line under discussion, and a reader can
see it in the snippet -- which is the property a pinned ref was reaching for
and a transcription gets for free. Step 4 is the stronger gate than any
figure above: it re-derives the census from the image and diffs it against
the committed CSV, so a re-cut that moved a cell is caught by the tool
rather than by a sentence in this file.

## 6. What this does not establish

- **Nothing about the hardware or the EC.** Every input is a committed file.
  No capture was opened, no register read back, no EC or HID node touched, and
  no sentence here should be read as a live observation. A count of byte
  pairs is a fact about a file and about the method that read it.
- **That the 27 were wrong.** They were right, for a tree this repository
  has since changed. The distinction matters: the pre-#517 guard genuinely
  could not see `mov 0x82,a`, and the rows it misfiled were genuinely the
  rows §1 lists. What changed is the guard, not the measurement's arithmetic.
- **That no other form of DPTR reach exists.** The census covers every
  8051/8052 opcode whose `direct` operand is a byte address -- all 44 of
  them, 38 in the base 8051 plus the six the 8052 extension adds -- at
  every offset, and
  `mov DPTR,#imm16` separately. The two classes it leaves out are named
  in §3 and are exclusions of this keying, not of the 8051: the
  bit-addressed forms, where `0x82` is the low byte of SFR `0x88`, and
  `0x90`. An indirect reach -- DPTR built through a
  pointer, as `test_de3c_store_target.py`'s `0xDE3C` does with the
  `0x0564:0x0563` pair staged out of CODE tables -- is in **none** of these
  tables and no byte sweep would find it.
- **That the length cross-check settles operand *kind*.** It settles that
  each of the 44 is decoded at the length a byte-addressed `direct` operand
  forces, which is what rules out the one-byte register-indirect rows the
  correction above removes. It does not separate `0x24 add a,#imm` from
  `0x25 add a,direct` -- both are two-byte `add` forms, and only the
  listings' rendering tells them apart. What separates those is quoted
  evidence in §3 and the renderer's behaviour in §2, not a check that can
  fail if one of the two moved into the other's row.
  `dptr-rebuild-walk-guard.md` §2 is where that one is worked.
- **The in-place forms as terminators.** They are counted here and excluded
  there, and §3 of that file states why. This change does not reopen it.
- **Anything about a register's status.** `ec/annotations/registers.yaml` is
  untouched and no `status:` moves: a `mov DPL,A` is a reference to the byte
  `0x82`, not to any XDATA address, and the `static_refs` counts are over
  addresses. The same sentence
  `dptr-rebuild-walk-guard.md` §6 gives, repeated here because this file too
  quotes a byte count and a reader could join them up.
- **#799** (a DPTR reassignment inside a *callee*, a different shape in a
  different place) and **#846**'s decision that the budget stays 8. Both are
  untouched here, and neither is cited as closing by this work.

## 7. The stale sentence this found, and where it was corrected

`docs/findings/walk-window-terminators.md` §A still read, in the present
tense, that "`walk()`'s guard tests `d[i] == MOV_DPTR` and cannot see the
`0xF5 0x82` / `0x8F 0x82` form", and annotated the `0x2C2FA` decode's
`0x2C2FE` line "budget-8 window ends here on `clr a`". Both describe the
pre-#517 guard. That row's committed `window` cell is now `mov a,r7 ;
movx @dptr,a ; mov 0xf0,#0x5e ; mul ab ; add a,#0xf8` with
`terminator = DPTR reloaded` -- the window ends **before** `0x2C305`, where
`f5 82` writes DPL, which is the very instruction the old annotation said
the guard could not see.

The correction is **in place in that file, with the wrong text left
visible**, per CLAUDE.md's §4a-4d pattern. It is the only place in the tree
still asserting the blind spot in the present tense, and it is the document a
reader is sent to for the terminator vocabulary.
