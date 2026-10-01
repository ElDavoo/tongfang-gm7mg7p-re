# `0x07D6`/`0x07D7` are 213 PD-image sites and 0 EC sites, and the two bytes reach opposite conclusions

(2026-10-01, issue #323. Re-derivation from committed inputs only: the two
images in `ec/firmware/GMxMGxx_11.800`, the annotation files the grade came
from, and `evidence/acpi/dsdt.dsl`. **No hardware, no Windows, no capture, and
no EC was opened.** No `registers.yaml` row moved, no `static_refs*` count
changed, and no committed CSV was regenerated — the four grades this file
writes down were already in the table when it was planned, and what was missing
was the record of them.)

`docs/findings.md` mentions `0x07D6` or `0x07D7` on eight lines — five in §4o,
two in §7c and one in §47 — and **not one of the eight states the result**.
Six are block-level statements about `0x07C4`-`0x07D7` as a whole, one uses the
pair as a fixture pair in an unrelated suite, and the last is §4o's ASL table,
whose `| 0x1176 | 50730-50733 | CGCT = Arg1 (0x07D7) | Notify PEGP | — |` row
carries the `CGCT` writer and no scan result at all. The load-bearing number is
the one none of them states: **`0x07D6` has 142 and `0x07D7` has 71 direct `MOV
DPTR` sites, every one of them in the `ITE8850-PD` image, and not one in the main
EC firmware.** That is what `ec/annotations/ec-07d6-07d7-sites.md` walks, and it
is the whole reason `0x07D6`, `0x07D7`, `0x07C7` and `0x07C8` are graded
`unknown-not-absent` rather than `present-untested`.

## `0x07D7` — a decoded ASL writer, and no EC-side site at all

`0x07D7` is `CGCT` in the DSDT's `ECMG` field list, and `T1WR`'s
`Arg0 == 0x1176` branch is its writer:

```
dsdt.dsl:50730      ElseIf ((Arg0 == 0x1176))
dsdt.dsl:50731      {
dsdt.dsl:50732          ^^PCI0.LPCB.EC0.CGCT = Arg1
dsdt.dsl:50733          Notify (^^PCI0.PEG0.PEGP, 0xC0) // Hardware-Specific
```

An unconditional store of `Arg1` into the byte, with no guard on `DBEN` or any
other field — unlike the `Arg0 == 0x73` branch four branches above, which wraps
the same block's `CPUA`/`DBAP` publish in `If ((DBEN == One))`. The
notification goes to the PCI device behind the PEG0 root complex, not to
`\_SB.NPCF` as the `0x73` branch does, and **what that notification is for is
not recovered**.

Against that, the firmware scan finds **71** direct `MOV DPTR` sites for
`0x07D7`, all of them `pd-image`, and `0` in the main EC firmware. So a byte
with no EC-side reference anywhere is written by ASL, which is the shape of the
`0x07B0`-`0x07BE` blind spot `registers.yaml`'s own header records for `0x07B9`
— Windows writes it and it works, with no direct reference in the image to show
how. Two limits belong beside that, rather than assumed away: the branch is
*decoded* ASL and not an observed one, so whether `0x1176` is ever issued on
this board is not established; and `windows/tools/t1wr_callers.py` has never
searched for a caller of `0x1176`, so §4f's figures say nothing about this
branch at all.

## `0x07D6` — a name in the field list, and no ASL site at all

`0x07D6` is `DBSP`, the field declared immediately after `CPUA` and `DBAP`
(`dsdt.dsl:52257`), which allocates it 8 bits. **That declaration is the whole
of its ASL life:** grepping the DSDT for the field name and for the address
returns that one line and nothing else, so no ASL method reads or writes this
byte.

The firmware scan finds **142** direct `MOV DPTR` sites for `0x07D6`, again all
`pd-image`, and again `0` in the main EC firmware. So this byte has the mirror
image of `0x07D7`'s problem: a name with no access behind it on the ASL side,
and no EC-side reference behind it on the firmware side.

A name with nothing behind it is a real thing to find, but it is not an answer
to "what is `DBSP`", and the PD program filling its *own* `0x07D6` is not an
answer either — for the reason the next section gives.

## Why this is two paragraphs and not one sentence

The tempting compression is "the block is 213 PD-image sites and none are in
the EC firmware". It is wrong for each byte, in opposite directions, and the
way it is wrong is the whole content of this finding:

- For `0x07D7`, the scan's zero would hide a **writer that exists** — the ASL
  one. The scan reads the two firmware images and not the DSDT, so its zero is
  a statement about the EC firmware and says nothing about who writes the byte.
- For `0x07D6`, there is no writer on either side to hide. Naming it in a table
  of the pair would import `0x07D7`'s conclusion onto it, and `0x07D6` does not
  have one.

The same reason governs the 213. Those are **the PD program's own variables at
its own `0x07D6`/`0x07D7`** — a second 8051 program with its own reset vectors
and therefore its own XDATA map, as `ec/annotations/ec-0x07d0-sites.md` §1 sets
out and `registers.yaml`'s header spells out again. A `MOV DPTR,#0x07D6` inside
that image is not a reference to the EC's `0x07D6`, because they are not the
same byte. So "213 sites" is a fact about the `ITE8850-PD` image and the
"0 in the EC firmware" is a fact about the EC image; they are the same census
run and they are not the same claim, and the `region` column of the site table
is what keeps them apart.

## The four grades, and why `absent` is not available

`0x07D6`, `0x07D7`, `0x07C7` and `0x07C8` are all `unknown-not-absent` in
`ec/annotations/registers.yaml`. `registers.yaml`'s own header defines the value
for exactly this situation — "the references that made it look present turned
out to belong to the PD image, so the EC image has none — and per the note
above that is not 'absent' either" — and each of the four rows says in its own
note that this is why.

**`absent` is not a softer `unknown-not-absent`; it is a claim the method cannot
support, and §4c is the retraction that says so.** `docs/findings.md` §4c
retracted "0x07B9 is definitively gone" — a "does not exist" claim built on a
zero-reference scan, in the case where Windows demonstrably writes the byte and
the scan cannot find how. That scan was the same kind of scan, and it was wrong
in the direction `absent` invites. Issue #110 owns the specific blind spot that
has to close first: the computed-`DPTR` form, where the EC reaches a page by
building `DPH` at run time instead of with `mov dptr,#imm`, and which no
`MOV DPTR` scan sees. `0x07B9` is writable and working with no direct reference
anywhere in the image; `0x07D6` and `0x07D7` have a DSDT writer and a DSDT name
respectively, so neither is the same case — but neither is a case the scan can
rule on either.

`0x07C7` and `0x07C8` carry a stronger version of the point, because their zero
has no PD-image half at all: **0 = 0 + 0 in both images**, no name in the
`ECMG` field list, and no row in `ec/annotations/xdata-registers.csv` either.
That is a real absence of every form this repository knows how to look for, and
it is still "not found by this method". `ec-07d6-07d7-sites.md` §5 runs the
control that keeps the zero honest rather than asserting it: the
`addc a,#0x07 ; mov DPH,a` construction that reaches a `0x07` page at run time
returns 0 hits in the EC image, while the same four-byte shape with `0x0F`
returns the eight known sites. So the idiom is common, this one page does not
use it, and the register form, `mov DPH,a` from a register, and an indirect
`movx @Ri` are all still invisible to it. **0 is a floor for that reason and
not a total.**

`present-untested` is unavailable for the other direction: it asserts EC-side
references, and for these four the EC image has none. That is the definition
rather than a judgement, and `check_status_vocabulary.py` enforces it — its
count rule is that `present-untested` needs `static_refs_main_ec >= 1` on every
address.

## Where the result lives, and how to re-derive it

The walk itself is `ec/annotations/ec-07d6-07d7-sites.md`, with one row per
site in `ec/annotations/ec-07d6-07d7-sites.csv` beside it. The four numbers this
file writes down, and the 213 that follows from them, are re-derivable from
committed inputs:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x07D6 0x07D7 0x07C7 0x07C8 --counts-only
0x07D6: 142 direct MOV DPTR site(s)  pd-image=142

0x07D7: 71 direct MOV DPTR site(s)  pd-image=71

0x07C7: 0 direct MOV DPTR site(s)  none

0x07C8: 0 direct MOV DPTR site(s)  none

$ python3 -c "import csv, collections; \
    rows=list(csv.DictReader(open('ec/annotations/ec-07d6-07d7-sites.csv'))); \
    print(len(rows), collections.Counter(r['region'] for r in rows), \
          collections.Counter(r['addr'] for r in rows))"
213 Counter({'pd-image': 213}) Counter({'0x07D6': 142, '0x07D7': 71})
```

The blank lines are the tool's own — `trace_xdata_refs.py --counts-only` emits
one block per address. The 142 and 71 are a count of raw `90 07 D6` / `90 07 D7`
byte patterns; they are a different unit from the 37 and 35 that
`ec/annotations/xdata-registers.csv` reports for `cluster pd-028` and
`pd-029`, which count classified statements in the decompiled PD sources, and
`ec-07d6-07d7-sites.md` §1 reconciles the two and says which claim rests on
which. **The scan's number is neither an upper nor a lower bound on its own
terms, and the write-up should not lean on it as either**: it is inflated
above the instruction count by `inc dptr` walks, DPTR re-loads and byte
patterns that are not instructions at all, and it is short of what a computed
`DPTR` would reach, which no `MOV DPTR` scan sees. The scan's numbers are the
ones the four `registers.yaml` rows carry, because `check_register_counts.py`
recomputes those from the image on every gate run — its own
`N entries / M addresses` figure counts the whole register table and moves with
every row added, so it is not quoted here.

The `0x07D1` half of §4o's census bullet is a separate walk with its own site
table, `ec/annotations/ec-0x07d1-sites.md` and `ec-0x07d1-sites.csv` beside it:
76 rows, all `pd-image`, which reconciles the same way and is not folded into
the 213 here.

## The eight lines in `docs/findings.md`, and what each is

Cited by section rather than by line: a bare `file:NNN` is true only until the
next merge grows the file above it, and the issue that asked for this table
cited its sites that way, and has already drifted.

| where | what it is | verdict |
|---|---|---|
| §4o, the ASL table's `0x1176` row | `CGCT` = `Arg1` (`0x07D7`), `Notify PEGP` | the ASL half only, and correct as far as it goes — it says nothing about the scan |
| §4o, "`0x07C4`-`0x07D7` is a GPU dynamic-boost control block and not battery state" | a block-level structural conclusion from the field list | correct, and consistent with this file; not a per-byte statement |
| §4o, "one at `0x07C4`-`0x07D7` that ACPI reads out to the NVIDIA device" | the two-block reading, and `0x07D0`/`0x07D1`'s place in it | correct; the sentence names the block, not the two bytes |
| §4o, the `gpu_block_watch.py` door-procedure sentence | what the prepared watcher covers | correct; a procedure's scope, not a result |
| §4o, the register-census to-do bullet | asks for exactly this census | **stale — corrected in place, and this file is the answer for its `DBSP`/`CGCT` half** |
| §7c, "§4o — which reads `0x07C4`-`0x07D7` as a GPU dynamic-boost control block from the ASL alone — never mentions" | why `0x07C4` moving was a gap in §4o | correct and unchanged by this file |
| §7c, the `WATCH` set's `0x07C4`-`0x07D7` | what the door procedure can separate | correct; a scope statement about the procedure |
| §47, "`0x07C4`/`0x07D7`" among three testdata shapes | two EC addresses used as a fixture pair in an unrelated suite | incidental — nothing about this block, and nothing here reaches it |

## What this does not establish

- **Nothing here is a live test.** Every classification in this file and in the
  walk it points at is a statement about an 8-instruction linear window around
  each site, plus the routine each one sits in. **A `write` class is an
  instruction storing to the address, never evidence that the PD firmware or the
  EC acts on it**, and none of the five PD `[writer]` functions is known to be
  reached on this machine.
- **#278's capture has not been taken.** The prepared half is committed —
  `windows/tools/gpu_block_watch.py` sweeps `0x07D6` and `0x07D7` in one capture
  with the rest of the block, and `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`
  is the written procedure — but it needs the physical machine, which no cloud
  agent has. Nothing in this file or the walk it summarises should be read as an
  observed write.
- **Whether `0x1176` is ever issued, and what the EC then does with `CGCT`.** A
  decoded ASL branch is not an observed one. Widening `t1wr_callers.py` to
  `0x1176` re-bakes that tool's `EXPECTED_*` tables and §4f's figures, so it is
  a calibration change of its own rather than a line here.
- **What `DBSP` is for**, given that nothing in the ASL touches it. The field
  list allocates it 8 bits and that is the whole of it.
- **The rest of the census §4o asks for.** `0x07C9`-`0x07CB`, `0x07CD`-`0x07CF`
  and `0x07D2` still have no `registers.yaml` row, and `0x07D2` is issue #226's.
  `0x07CC` already has one and is not part of this. The door procedure's §7
  table is where that list is kept, and this file closes four cells of it and
  not the census.