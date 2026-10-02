# The `pd 0x11C2` dispatch key is `0x0424 + 0x260 * R7`, and only three key pairs ever leave the default record (issue #647)

`docs/findings/pd-common-address-spaces.md` §"The CB2A comment tension"
deliberately left one thing open: the four records at `pd` 0xCB4D are scanned
against a 16-bit pair, and "A here is whatever `pd 0x38D3` returned, which the
bytes do not fix." Every instruction between the store and the dispatch is
committed and the arithmetic closes, so this is the answer, and
[`ec/tools/pd_dispatch_key.py`](../../ec/tools/pd_dispatch_key.py) is the
machine that re-derives it.

    key address = (0x0424 + 0x260 * R7)   mod 2**16
    key pair    = B = XDATA[addr], A = XDATA[addr + 1]

exact for all 256 values of the byte, and the table is a function of the pair
alone: three of the 65536 pairs reach `0xCB5D`, `0xCB66` and `0xCB6F`, one
pair each, and the other 65533 take the default to `0xCB76`. Which pair a real
execution presents is still open, because a pair is XDATA *contents* and the
image says nothing about what is stored there.

**Two corrections to the issue as filed, before any of this is used.** Its
`registers.yaml` census is wrong in a way that matters: `0x0803` and `0x0424`
already had rows in `ec/annotations/xdata-registers.csv`, so the gap was
`0x0425` alone. And its chain describes `pd 0x34EF` and `pd 0x34F2` as two
calls; `pd 0x34EF` has **no `ret`** — its own
`ec/annotations/ghidra-functions.csv` row says so, "A single `mov DPTR,#0x424`
with no ret" — so the `lcall` at 0xCB40 falls straight through into `pd 0x34F2`.
The total is the same and the mechanism is one call, not two.

---

## The chain, instruction by instruction

`pd 0xCB2A` is the entry. The two XDATA bytes it writes before the selector
work are R5 at 0x0804 and a zero at 0x0805; neither takes part in the key.

    0xCB2A  mov  dptr,#0x0803     ; the selector byte's address
    0xCB2D  mov  a,r7
    0xCB2E  movx @dptr,a          ; XDATA[0x0803] = the caller's R7
    ...
    0xCB33  mov  r7,a             ; R7 = 0 -- the register is spent here
    0xCB37  cjne a,#0x0d,0xcb3b   ; R3 != 0x0D, or 0xCB3A returns
    0xCB3B  mov  dptr,#0x0803
    0xCB3E  movx a,@dptr          ; A = the same byte again
    0xCB3F  mov  r1,a             ; and now it lives in R1

**The precondition is not in the issue, and it bounds the whole derivation.**
`cjne a,#0x0d,0xcb3b` returns at 0xCB3A when R3 == `0x0D`, before a byte of the
key arithmetic runs. The selector therefore executes only for a caller that
does not take that early return. `ec/tools/pd_dispatch_key.py` runs with R3 =
`0x00` and says so rather than picking a value silently; a case in its suite
drives R3 = `0x0D` and pins that the chain stops at 0xCB3A having entered none
of the helpers.

**`pd 0xCB2A` reads its own selector back rather than keeping it**, which is why
XDATA 0x0803 is the register this whole question is about: the byte is written
to RAM and read out of it, so anything that writes 0x0803 between 0xCB2E and
0xCB3E would change the key. Nothing in this chain does, and the *value* is the
caller's R7 either way — the store is not a transformation.

    0xCB40  lcall 0x34ef          ; -> mov dptr,#0x0424, and no ret
      0x34EF  mov  dptr,#0x0424
      0x34F2  mov  0xf0,#0x60     ; B = 0x60
      0x34F5  ljmp 0x10bc
        0x10BC  mul  ab           ; A*B: low half in A, high half in B
        0x10BD  add  a,0x82       ; A += DPL
        0x10BF  mov  0x82,a
        0x10C1  mov  a,0xf0       ; A = high half
        0x10C3  addc a,0x83       ; A += DPH + carry
        0x10C5  mov  0x83,a
        0x10C7  ret               ; -> 0xCB43

`pd 0x10BC` is `DPTR += A*B`, and it is a *correct* 16-bit modular add:
`mul AB` splits the product, and the `addc` folds the low byte's carry into
DPH. With B = `0x60` this is `DPTR += 0x60 * R7`, so far `0x0424 + 0x60 * R7`.

    0xCB43  mov  a,r1             ; A = the selector byte again
    0xCB44  lcall 0x349b
      0x349B  add  a,0xe0         ; A += A
      0x349D  add  a,0x83         ; A += DPH
      0x349F  mov  0x83,a         ; DPH = A; DPL is untouched
      0x34A1  ret                 ; -> 0xCB47
    0xCB47  lcall 0x38d3
      0x38D3  movx a,@dptr        ; low key byte
      0x38D4  mov  r4,a
      0x38D5  inc  dptr
      0x38D6  movx a,@dptr        ; high key byte
      0x38D7  mov  0xf0,r4        ; B = the low one
      0x38D9  ret                 ; -> 0xCB4A
    0xCB4A  lcall 0x11c2

`pd 0x349B` adds `2*R7` to DPH and leaves DPL alone, which is `0x200 * R7` in
the high byte. **`add A,0xE0` and `add A,0x83` are both plain `ADD`s, so the
carry out of the first is discarded** — and it has to be, because a carry is
worth 1 and the doubled value it stands for is worth 256. The result is
`DPH += 2*R7` modulo 256 exactly, for every value of the byte, which is a
different route to the same arithmetic from `pd 0x10BC`'s and not the same
routine. Modelling both as "add with the carry" is wrong by one in DPH for every
selector byte from `0x80` up — which is a defect this derivation actually had
before the whole-byte run caught it, and which no amount of checking `R7` = 0..7
by hand would have found.

So, summing the two steps:

    key address = 0x0424 + 0x60 * R7 + 0x200 * R7
                = 0x0424 + 0x260 * R7   (mod 2**16)

**It wraps, and the issue's "0x04xx–0x14xx pages" does not survive the whole
byte.** The sum leaves the `0x04xx`–`0x14xx` band long before the byte is
exhausted: `R7` = `0x6A` is the last value that stays under `0x10000`, at
`0xFFE4`, and `R7` = `0x6B` wraps to `0x0244` — a *lower* address than `R7` = 0
gives. The largest byte lands at `0x61C4`. So the range is not a set of pages
but a stride with a wrap in the middle of it, and the two steps that produce it
are both exact 16-bit modular adds, not approximations of one.

### What the simulator is, and what it refused

`ec/tools/pd_dispatch_key.py` executes the chain on a machine modelled
instruction by instruction, fetching every byte at runtime address `pc` out of
the PD region of the committed image. It refuses on any opcode outside the set
the chain uses, and on any direct byte outside `0x82`, `0x83`, `0xE0` and
`0xF0` — a silent skip would let the closed form and the machine agree while
both ignored the byte in question, which is the failure a comparison between
two things cannot detect about itself.

Its `--self-test` re-derives against the committed listings: every mnemonic in
`ec/decompiled/pd/{CB2A,34EF,34F2,10BC,349B,38D3,11C2}.asm` against what the
image decodes to at the same address, the no-`ret` claim that makes 0x34F2 a
fall-through, all 256 selector bytes, and the residue below.

---

## The record table

Only `0xCB4D..0xCB4F` appear in any committed listing — `ec/decompiled/pd/CB2A.asm`
stops there, because those three bytes are data and the decompiler read them as
`xch a,r3 / anl a,r5 / ajmp 0xc808`. The remaining thirteen bytes are in no
listing at all, so the table is read from the image at file 0x2CB4D rather than
transcribed:

    0xCB4D: cb 5d 01 08      key (B, R0) = (0x01, 0x08)   -> 0xCB5D
    0xCB51: cb 66 02 06      key (B, R0) = (0x02, 0x06)   -> 0xCB66
    0xCB55: cb 6f 02 07      key (B, R0) = (0x02, 0x07)   -> 0xCB6F
    0xCB59: 00 00 cb 76      default                      -> 0xCB76
    0xCB5D: eb 64 02         code resumes: mov a,r3 / mov a,@r4 / inc r0

**The two target conventions are different and both are right.** `pd 0x11C2`
tests `CODE[+0]` and `CODE[+1]` for zero *first*; when either is nonzero it
compares `CODE[+2]` against B and `CODE[+3]` against R0, and on a match DPTR is
still at the record base, so `mov 0x82,a` / `mov 0x83,r0` build the target from
`+0`/`+1`. When both of `+0`/`+1` are zero the scan takes the other route: two
`inc DPTR` first, so `+2`/`+3` are the *target* there and the key is never
compared. `pd-common-address-spaces.md`'s existing reading of the `00 00`
record — that it is the default and selects 0xCB76 — **is correct and is not
retracted**; what this adds is the three keyed records beside it and the fact
that the selection is a function of the pair.

**Which record a pair selects, exhaustively.** `--select` evaluates the scan's
own logic over all 65536 pairs. Three pairs reach a keyed record, one each;
the other 65533 reach the default. So this table cannot be scanned past its
end, whatever the pair is — the `00 00` record is inside the table, and that
is what stops it. `pd 0x11C2` itself has no length check and never had one; the
bound is a property of *this* table, not of the routine, and the general
question stays open where the earlier section put it. `--select --verify-all`
runs the machine against the census over the whole 65536-pair space rather than
the named set the default run prints, which is about a minute and currently
reports agreement on all of them.

**A residue, which bounds what this call site can ever select.** The stride is
`0x260 = 32 * 19`, so every address the chain can reach is congruent to
`0x0424 ≡ 0x04 (mod 32)`. A key pair only ever stored at an address outside
that residue cannot be selected through `pd 0xCB2A` — and this says nothing
about the other fifteen `lcall 0x11C2` sites in the image, each of which builds
its own DPTR.

---

## `XDATA_0803`: a selector, a second writer, and two more readers

`ec/annotations/registers.yaml` gains one row, `XDATA_0803`, at
`present-untested`: 142 sites, 3 EC-side, 139 in the PD image. All three
numbers are tool-derived and reproduced by `ec/tools/check_register_counts.py`;
none is typed from the issue.

Per CLAUDE.md, a register with a second writer is worth surfacing explicitly,
and this byte has one. `ec/annotations/xdata-registers.csv` names, for the
PD image:

| site | what the census says |
|---|---|
| `pd 0xCB2A` `store_0803_0805_then_jump_c808` | writes it from R7, and builds the dispatch key from it |
| `pd 0xB80E` `write_r7_and_r3r2r1_to_0803` | **a second writer**, and its name says it also takes R3:R2:R1 |
| `pd 0x1E4B` `read_0803_and_invert` | a further reader |
| `pd 0x1EFE` `gate_0803_then_dispatch_through_code_table` | a further reader, and it dispatches on the byte |
| `pd 0x1E9D` `flag_from_f4ee` | touches the 0x0803-0x0806 block |
| `bank1 0x8300` `clear_and_set_xdata_flag_bits` | the one EC-side site the census names a function for |

So the selector is per-call and the byte has several sites feeding it. The
derivation above is about one call site and one round trip; it is not a model
of what the byte holds at any other time. On the EC side the three sites are
one read at bank1 0x81EA and two stores of `0x01` at 0x830D and 0x83C7, all
three in bank1; `ec/annotations/site-resolution.csv` names bank1 0x8300
`clear_and_set_xdata_flag_bits` for the middle one and `not exported` for the
other two. A static direction is a static direction: none of this is evidence
the EC acts on the byte.

### What the new row moved, and what it did not

Four generated files follow `registers.yaml` and were regenerated with their
own tools rather than edited — `ec/ghidra/xdata-symbols.csv` and the two
census CSVs from `ec/tools/gen_xdata_symbols.py` and
`ec/tools/xdata_register_map.py`, plus `ec/annotations/site-resolution.csv`
from `ec/tools/check_site_resolution.py`. In `xdata-registers.csv` the change
is one cell: the `0x0803` row's `name` was empty and is now `XDATA_0803`.
`xdata-clusters.csv` gains the same address in the seeded-name column of
`main-ec-369` and `pd-012`, and `xdata-symbols.csv` gains its row. The
counts, the clusters and every other cell are unchanged — which is the point of
running the generators rather than the diffs.

One `xdata_register_map.py` oracle moves: `named_in_tree`, 189 → 190. That is
arithmetic over the tool's own `NOT_IN_TREE` dict rather than a figure anyone
decided — 0x0803 is an address the census already reached, so the new name is
absent from `NOT_IN_TREE` and adds one to the count, where a row for an address
the scan cannot reach would have added one to `NOT_IN_TREE` and none here.

**Two addresses the issue asked for are not entered, and the reason is a
committed rule rather than a judgement.** `0x0424` and `0x0425` do not get
`registers.yaml` rows. Rule 2 of that file's own header — the one
`ec/tools/check_status_vocabulary.py` enforces — is that `present-untested`'s
entire warrant is a reference count, so it needs `static_refs_main_ec >= 1` for
every address in the entry, and a PD-only count cannot carry it. `0x0424`'s
twelve sites are all PD-image and `0x0425` has none at all, so both are
refused the grade, with `0x07CC`'s re-grade to `unknown-not-absent` as the
stated precedent. Separately, `ec/annotations/xdata-0400-045f.md` §6 declines
both by a stated *if and only if* rule — "entered if and only if the EC image
has at least one direct `MOV DPTR,#addr` site" — and `0x0425` is reached only
through `pd 0x38D3`'s `inc DPTR`, which is the case
`ec/annotations/xdata-inc-dptr-only.md` declines.

`0x0425`'s zero is **not found by this method**, never absent: it is the second
byte of a pair this chain reads, and an `inc DPTR` between two reads is
invisible to a direct-`MOV DPTR` scan by construction.

---

## What this does not establish

**Nothing behavioural, and no live test ran.** Every figure is a static
measurement over committed `.asm` listings and the committed firmware,
reproducible with the commands above. No hardware is reachable from a
GitHub-hosted runner and nothing here needs any.

**The value stays open, and it is more open than "R7 is a runtime byte"
suggests.** The key pair is a pair of XDATA contents. The image fixes the
*address* those contents live at, for each of the 256 selector bytes, and says
nothing whatever about what is stored there. So *which record a real execution
selects* is unanswered, and it would need either a live run or a reachability
and dataflow analysis over the PD image. The three keyed pairs in the table are
what the PD program would have to have written for the keyed branches to be
reachable at all; this write-up does not claim they ever are.

**Whether `pd 0xCB2A` is reached, and with what R3.** The R3 == `0x0D` early
return is decoded; what any caller passes in R3, R5 and R7 is not.

**The function name against the bytes.** `store_0803_0805_then_jump_c808`
describes neither what happens at 0xCB4D (which is the table) nor where control
goes. All four targets are code and none of them is 0xC808: `0xCB5D`,
`0xCB66` and `0xCB6F` each open `mov a,r3 / mov a,@r4 / mov r0,a / xrl a,r0`
with a different immediate after it, and `0xCB76` opens `mov a,r7 /
add a,#0xfe / mov r7,a / ajmp`. None of the four has a
`ec/annotations/ghidra-functions.csv` row. The existing row for `pd 0xCB2A`
already records the discrepancy. Renaming it ripples through the generated
call-graph, group and listing-index CSVs, several of which other agent PRs are
open against, so it is left as a follow-up rather than done here.

**Nothing about the EC.** Every address in this write-up is the PD image's own
XDATA, which `ec/annotations/registers.yaml`'s header is explicit is a different
map from the EC's. The `XDATA_0803` row is the one place where the two meet,
and it meets them only in the file-offset bookkeeping.

---

## Follow-ups this opens

- **`0x0803` has a second writer and two more readers**, named above. What
  `pd 0xB80E` writes there, and whether it can land between `pd 0xCB2A`'s store
  and its read-back, is a question this write-up does not touch.
- **Whether `ec/annotations/xdata-0400-045f.md` §6 should now admit PD-image
  addresses whose PD use has been identified.** `0x0424` is the case in point:
  its use is now understood and its admission rule still declines it. Amending
  that rule means editing its arithmetic in a shared annotation document, which
  is a change of its own.
- **Whether the record scan at `pd 0x11C2` can run past the end of a table it is
  given.** Settled for this table (it cannot) and still open for the routine.
- **The function-name-versus-bytes mismatch at `pd 0xCB2A`**, and the four
  unexported targets behind the table.
