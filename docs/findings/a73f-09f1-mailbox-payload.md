# `0xA73F` pushes a payload into an eight-slot ring, and there was never a command-code table to look it up in (issue #1444)

**Issue #1444, 2026-10-03.** Static reading and arithmetic over committed
bytes. Nothing here is a hardware claim.

`docs/findings/xdata-086c-cluster-ruling.md` §4 recorded that block two of
`0x9D9B` "calls `0xA73F` with a command code this record does not resolve", and
deliberately left the question for a follow-up pass to file once against the
command-code table. That framing is what this change answers, and the answer
is that the table does not exist and never did: **the byte `0xA73F` takes is a
payload.** It is pushed into an eight-slot producer/consumer ring at
`0x09F2`-`0x09F9`, indexed by a pair of cursors packed into `0x09F1`, and the
value is read back out and pushed into a second sixteen-byte ring. No
comparison on that path tests it, and the only routines that touch a ring
slot are the initialiser at `0x8955`, the two accessors at `0x89A9` and
`0x89E7`, and the two that call them.

The queue the question was deferred to was empty because the value is not a
selector. Recording that as the finding, rather than leaving the question open,
is the point of the exercise.

## The chain, one citation per step

Every step below is a committed listing; none of it rests on a decompiler's
symbol.

| Step | Address | What it does |
| --- | --- | --- |
| 1 | `ec/decompiled/bank0/A73F.asm` | Four instructions: `MOV 0x6A,R7`, `MOV A,0x6A`, `MOV R7,A`, `LJMP 0x1666`. `0x6A` is internal RAM, not XDATA — no XDATA byte is touched here. The `MOV 0x6A,R7` / `MOV A,0x6A` / `MOV R7,A` round trip has no effect on the value. |
| 2 | `ec/decompiled/bank0/1666.asm` | `MOV DPTR,#0x896A` then `LJMP 0x1114`. |
| 3 | `ec/decompiled/common/1114.asm` | `bl51_bank_select_1`: `PUSH 0x08`, `MOV A,#0x11`, `PUSH A`, `PUSH DPL`, `PUSH DPH`, `MOV 0x08,#0x1E`, `SETB 0x90`, `CLR 0x91`, `CLR 0x92`, `RET`. Bank number `0x1E`, `P1.0` set. This hands DPTR to BL51's far call into bank 1. |
| 4 | `ec/decompiled/bank1/896A.asm` | The gate: proceed only if `0x06E6 == 0x01` **and** `0x0440 != 0`; otherwise `RET` at `0x897A` and the byte is dropped. |
| 5 | `ec/decompiled/bank1/89B5.asm` | The producer, below. |

Step 3 is what the other annotation rows describing a `0x1114` trampoline got
wrong, and this change retracts; see "The retraction" below.

## `0x09F1` is two cursors and two flags, and the mask is why they are independent

This is the part that is not obvious from the listing, and the part the plan
that produced this file left open. It is settled by one mask.

`0x09F1` holds, in a single byte:

- **bits 0-2** — the producer's index, `ANL A,#0x07` at `89B5.asm:89C0`;
- **bits 4-6** — the consumer's index, `SWAP A` then `ANL A,#0x07` at
  `897B.asm:897F`-`8980`, which puts original bit 4 at A bit 0 through original
  bit 6 at A bit 2;
- **bit 3** — a flag, set only at `89B5.asm:89E3` (`SETB 0xE3`);
- **bit 7** — a flag, set only at `897B.asm:89A5` (`SETB 0xE7`).

Both sides mask with `0x77` on every index update — `ANL A,#0x77` at
`89B5.asm:89CC`/`89CF` and `897B.asm:898D`/`8991` — and `0x77` clears exactly
bits 3 and 7 and nothing else. That single fact resolves the arithmetic:

- the producer's `((v & 0x77) + 1) & 0x77` increments the low field and
  **stops there**. The carry out of bit 2 lands in bit 3, which the mask then
  clears, so it never reaches bits 4-6;
- the consumer's `((v & 0x77) + 0x10) & 0x77` increments the high field and
  stops there. The carry out of bit 6 lands in bit 7 and is cleared.

So the two three-bit fields are **independent counters over one shared
eight-byte buffer**, not the two halves of one eight-bit index. The mask is
what makes them independent, and reading it as a single index is the mistake
that made the producer's bump look like it advanced both cursors at once.

Both index updates also clear *both* flag bits as a side effect. That is not an
incidental consequence of reusing one mask: it is how a flag is released.

## The producer's flag is full, the consumer's is empty

Each side tests its own new index against the other side's, and sets its flag
when they are equal. The comparison is `CJNE A,0x00` — opcode `B5`, the
`CJNE A,direct,rel` form, so the operand at `0x00` is `R0` in register bank 0,
not a literal zero. `R0` was loaded with the new value at `89B5.asm:89D2` and
masked to bits 0-2 at `89B5.asm:89D3`; `A` is the swapped new value masked to
bits 4-6. The test is therefore *write field == read field*.

- **Producer** (`89B5`): if the incremented write field equals the read field,
  the producer has carried all the way round onto the consumer — set bit 3.
- **Consumer** (`897B`): if the incremented read field equals the write field,
  the consumer has caught the producer — set bit 7.

Write-equals-read is ambiguous between drained and wrapped in an eight-slot
ring, and two flag bits is exactly how that ambiguity is resolved: bit 3 is
*full*, bit 7 is *empty*, each set by the side that lapped the other, each
released by the other's next index update.

The reset state falls out of it and is checkable.
`ec/decompiled/bank1/8955.asm` writes `0x80` to `0x09F1`: bit 7 set, both
cursors zero — a fresh mailbox reads empty, which is correct when nothing has
been written. A producer call then stores at slot 0, moves the write field to
1, finds `1 != 0`, and clears both flags on the way; the mailbox holds one
unread byte with neither flag set, which is the correct state for that.

`ec/decompiled/bank1/8915.asm` is the consumer's caller and tests bit 7 with
`JB 0xE7` at `8944` before draining, so a read of a ring nothing has written
is refused rather than served.

## The consumer half, and where the payload goes

`ec/decompiled/bank1/8915.asm` is more than a gate. In order:

1. `0x06E6 == 0x01` and `0x0440 != 0`, else `RET` at `0x8954`;
2. if `0x047C` is non-zero, increment `0x09F0` and return while the result is
   below `0x10` (`CLR CY` / `ADD A,#0xF0` / `JNC`), and clear `0x047C` on
   reaching `0x10` — a saturating counter over the mailbox's content;
3. zero `0x09F0`;
4. if bit 7 of `0x09F1` is clear, `LCALL 0x897B` to take a payload, store the
   returned R7 into `0x047C`;
5. `LCALL 0x88F0` with `R5 = 0x53`.

So `0x047C` is a latch holding the last payload the mailbox handed over, and
`0x09F0` counts passes since it was last cleared. Both are now rows in
`ec/annotations/registers.yaml`.

`0x897B` reads the slot and increments the consumer's cursor; the byte comes
back in R7 and lands in `0x047C`, and the `R5 = 0x53` that follows is a fixed
constant, not the payload.

### `0x88F0`'s listing stopped at `0x8900`, and the bytes past it are in the image

The listing for `ec/decompiled/bank1/88F0.asm` stops at `0x8900` because the
exporter's call-target scan also found entries at `0x8901` and `0x8902`, and
the routine's own decompile says so. That truncated body was the one thing in
this walk that rested on a `.c` reading, and the committed image settles it:

```
0x8901  04        inc  a
0x8902  54 0f     anl  a,#0x0f
0x8904  90 07 0f  mov  dptr,#0x070f
0x8907  f0        movx @dptr,a
0x8908  90 07 10  mov  dptr,#0x0710
0x890b  25 82     add  a,0x82
0x890d  f5 82     mov  0x82,a
0x890f  ed        mov  a,r5
0x8910  f0        movx @dptr,a
0x8911  12 19 ea  lcall 0x19ea
0x8914  22        ret
```

(`python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x108F0 -n 16`,
anchored at the listing's own start.)

The ring base is **`0x0710`**, so the sixteen entries are `0x0710`-`0x071F` and
the store is `0x0710 + cursor`. The decompile's
`*(undefined1 *)CONCAT11(7,DAT_EXTMEM_070f + 0x10)` puts them at
`0x0700`-`0x070F` and is wrong: `CONCAT11(7,x)` is `0x0700 + x`. The `.asm` is
the machine code and wins. The `0x8902` annotation row already read it this
way, so this is the listing's truncation being closed rather than a claim
changed.

`0x19EA` is `load_dptr_8588_tail_jump_1100`, a forwarder. **What drains
`0x0710`-`0x071F` is not established by this walk**, which stops there.

## The call sites: eleven `lcall` and four `ljmp`

`ec/tools/a73f_call_sites.py` enumerates them from the committed transfer
census. Reading `ec/annotations/bank-call-targets.csv` rather than re-scanning
is deliberate and is the tool's own docstring: `a5e6_quotient.py` states the
reason (re-running `audit_call_targets.py` here would assert the tool against
itself), and a `12 a7 3f` byte scan would also answer a **smaller** question,
because four of the transfers are `02 a7 3f` — `ljmp` tail calls, which push no
return address of their own. An opcode-specific scan is blind to every one of
them, and losing them is silent, since every remaining row is still a real
site.

| Runtime | Opcode | R7 | | Runtime | Opcode | R7 |
| --- | --- | --- | --- | --- | --- | --- |
| `0x8867` | lcall | `0xBB` | | `0xC5A5` | lcall | `0xB1` |
| `0x8993` | lcall | `0xAC` | | `0xC603` | lcall | `0xB2` |
| `0x8F17` | lcall | `0xA7` | | `0xC729` | ljmp | `0xB0` |
| `0x8F1C` | lcall | `0x43` | | `0xC77F` | lcall | `0xB8` |
| `0x9FA0` | lcall | `0xBC` | | `0xC848` | lcall | — |
| `0xA33D` | lcall | `0xAE` | | `0xC936` | ljmp | `0xB9` |
| `0xA3D3` | ljmp | `0xA8` | | | | |
| `0xABD0` | ljmp | `0xB0` | | | | |
| `0xB10E` | lcall | `0xB6` | | | | |

Twelve of the fifteen load R7 in the instruction immediately before the
transfer, and the `r7_gap` column is 2 for every one of those — the value is
not merely the nearest one, it is the adjacent instruction.

**The two gap-44 readings are settled by a branch, not by the scan reaching
further.** `ec/decompiled/bank0/C55F.asm` loads `MOV R7,#0xb1` at `0xC579`
and takes `SJMP 0xC5A5` at `0xC57B`, which is the transfer site itself;
`ec/decompiled/bank0/C5BD.asm` does the same with `0xB2` at `0xC5D7` and
`SJMP 0xC603` at `0xC5D9`. Each site's only inbound branch in the image is
that one, so R7 is `0xB1` and `0xB2` there by control flow rather than by a
byte pattern that happens to sit nearby.

That distinction is what `a73f_call_sites.py`'s `r7_branch` column records and
why the tool drops an uncorroborated far pair instead of publishing it. The
image holds a `mov r7,#0x12` at `0xC827`, in a run of `7f nn` / `lcall 0x2990`
pairs that tail-jumps away at `0xC829` and has nothing to do with this path. A
window wide enough to reach gap 44 also reaches it, and without the branch
check `0xC848` would read as `0x12` — a value the firmware does not support.
It stays empty: **"not found by this scan",** never "R7 was left alone".

`0xC77F` is the one site no committed `.asm` listing covers, and it carries
`0xB8` — a value the listing-derived list does not have.

**Every one of the fourteen readings is a literal.** There is no site that
passes a computed or register-derived value. The values run `0xA7` to `0xBC`
with gaps, and `0x43` outside that range.

## What the values are not

A scan for a comparison against any of those immediates — `CJNE A`, `CJNE Rn`,
`SUBB`, `MOV Rn,#data` — returns hits, and the honest report is what it
returned, not the tidier claim that all of them are misframings.

Twelve of the hits are the immediate of the `mov DPTR,#0xBFxx` / `ljmp 0x1100`
forwarder table in the common area, which a byte scan reads as
`CJNE R7,#0xA7` and up: `90 BF xx` re-frames as `BF xx 02`, and `BF` is
`CJNE R7,#data,rel`. That is the shape `ec/annotations/bank-call-targets.csv:557`
records, and this file's own predecessor got that much right. The count is not
independent of the payload set: it is exactly one hit for each of the twelve
distinct values in the `0xA7`-`0xBC` range, all of which the table covers, and
none for `0x43`, which falls inside a gap the table leaves between its entries
`0x2C` and `0x55`. So the correspondence is with what the table covers, not
with the payload block. The rest are ordinary unframed byte coincidences; a byte scan
is not a decode, and `ec/tools/disasm8051.py`'s docstring is the longer
argument.

**No hit falls inside any routine on the mailbox path** — bank1 `0x88F0`-`0x897A`,
bank0 `0xA73F`-`0xA745`, bank0 `0x1666`-`0x166A`, common `0x1100`-`0x1128` — and
the fourteen instructions from `0xA73F` through the gate to the `LCALL 0x89B5`
that starts the ring store contain no comparison at all. That is a bounded
negative: *no comparison on the path*, not *no comparison in the image*.

So the enum's meaning is not in this firmware, by the method above. Whether the
eight bytes are, say, event codes or a state machine's inputs is a question for
a capture, not for another scan, and this file does not guess.

## The register rows, and the ones that cannot have one

`ec/annotations/registers.yaml` gained rows for `0x047C`, `0x070F`, `0x09EF`,
`0x09F0`, `0x09F1`, `0x09F2` and `0x0A47`. Every `static_refs*` is reproduced by
`check_register_counts.py`, and `site-resolution.csv` is regenerated from them.
All seven carry `present-untested`: each has a direct EC-side site, and each
site resolves to a read, a write or both.

**The rest of both rings cannot have a row at all, and that is a property of
the table rather than a gap in the walk.** A `registers.yaml` address is turned
into a Ghidra symbol by `gen_xdata_symbols.py`, the symbol file is named
`xdata-symbols.csv`, and `xdata_register_map.py --self-test` requires every
address that file names and its C-level census does not reach to be recorded in
`NOT_IN_TREE` with a reason. So a byte the decompiled C never spells can be
written down only by growing that dict — and `NOT_IN_TREE` lives in a tool
whose line numbers are cited from `docs/findings.md`, which is frozen. Adding
the entries shifts those pins by the length of the addition, and fixing them
means editing a file this repository forbids editing.

That is worth stating as a limitation rather than working around:

- **`0x09F3`-`0x09F9`** are written and read only through the indexed helpers
  at `0x89E7` and `0x89A9`, which the export spells over register arithmetic,
  so the C names only the `0x09F2` base. `scan_refs.py` reports zero direct
  sites for six of them — "not found by this method", the blind spot this
  file's header records at `0x07B9`. `0x09F9` is the seventh and is different
  again: its two sites are both in the ITE8850-PD image at file `0x20000`,
  which has its own XDATA map, so the EC image has none.
- **`0x09F6`** would have been the one site to check before believing a count.
  Its single EC-side site, bank0 `0x10C59`, is `MOV DPTR,#0x09F6` followed by
  `MOV R4,0x83` and `MOV R3,0x82` and then `MOV DPTR,#0x0497` — no `MOVX` in
  between, so the site names the address and never dereferences it.
- **`0x0710`-`0x071F`** are the same shape in the other ring, and the cause is
  a misreading worth recording on its own: the export's
  `CONCAT11(7,DAT_EXTMEM_070f + 0x10)` places the ring at `0x0700`-`0x070F`
  where `bank1/8902.asm` has `MOV DPTR,#0x0710`.

The knowledge those rows would have carried is in this file and in the
annotation rows for `0x88F0`, `0x89B5`, `0x897B` and `0x8955`, which carry the
bank and address citations the register table cannot hold. **A register table
that is derived from what the decompiler could spell cannot describe a byte
the decompiler could not spell** — which is the sharpest form of the §4c blind
spot this repository keeps meeting, and it is a structural limit rather than a
gap anyone can scan their way out of.

### `0x0710` is a second thing the instrument decides, and it is recorded here

Worth stating because it cost a row. `0x0710` *does* have an EC-side site and
its listing shows it stored to, but the access walk ends at the `ADD A,DPL` two
instructions later: `trace_xdata_refs.is_dptr_rebuild()` treats a DPTR reload
as a different access and not a longer window, by design
(`docs/findings/walk-window-terminators.md`). The census records
`no movx in window`, and rule 3 of `check_status_vocabulary.py` would refuse
`present-untested` on that basis — correctly, on what it can see. The row was
dropped rather than filed at a status weaker than its evidence.

The open question both of these raise is the same one: **should a DPTR rebuild
count as a resolved direction at `--callee-depth 1`, and can a
`registers.yaml` row be filed for a byte the census cannot reach without
growing a line-pinned tool?** The committed listing answers the first
("write"). Neither is this change's to answer — the census feeds every row in
the register table — but both are cheap to fix deliberately and expensive to
rediscover.

## The retraction

Every annotation row that described `0x1114` as absent from the decompiled tree,
and every row that said the same of `0x1100`, is corrected. Both addresses are in
`ec/decompiled/index.csv`, with `ec/decompiled/common/1114.asm`,
`common/1114.c`, `common/1100.asm` and `common/1100.c` committed beside them.
That matters because `0x1114` is the bank switch on this very path: the rows
that called it missing were describing a trampoline as a dead end while it is
the reason the mailbox is reachable at all.

`0x1114` loads bank number `0x1E` into `0x08` with `P1.0` set; `0x1100` is the
same stub carrying `0x0A` with `P1.0` clear.

The rows now carry a dated correction beside the retracted claim rather than
in place of it, and the claim survives in the correction as prose rather than
as a quoted assertion — so a search for the assertion finds none, and a reader
still sees exactly what was retracted. `ec/tools/test_trampoline_absence_claims.py`
holds the shape: no row may claim an address is absent from the tree when
`ec/decompiled/index.csv` lists it.

Two more rows were corrected in the same pass. The `0xA73F` row said nothing in
its listing showed what `0x1666` does with the register value; the `0x8F0F` row
called its two values "command codes" and recorded the question as open. Both
now point here.

## What this does not establish

- **Nothing about a machine.** Every statement above is a reading of committed
  bytes. No register was read back and no behaviour observed.
- **Not a unit or a name for the payload.** That the value is not a selector
  says nothing about what it means. `0xA7`-`0xBC` is an enum whose labels are
  not in this firmware.
- **Not what drains `0x0710`-`0x071F`.** The walk stops at the `LCALL 0x19EA`
  after the store.
- **Not that the ring is used.** A decoded store is not evidence the EC acts on
  the bytes, which is the calibration rule in `CLAUDE.md` and the reason every
  row above is `present-untested` or weaker.

The read that would settle the first three is named, and it is a human's:
`0x09F0`, `0x09F1`, `0x09F2`-`0x09F9` and `0x047C` read while `0x06E6 == 1` and
`0x0440 != 0`, with a payload published, so the flags are caught mid-transition
rather than at rest. The machine runs for this block are already #1318 and
#1393; this change opens no third issue and adds no second preparation document
for runs those two carry.

## The commands

```console
$ python3 ec/tools/a73f_call_sites.py ec/firmware/GMxMGxx_11.800 --csv
$ python3 ec/tools/a73f_call_sites.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/check_site_resolution.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/check_status_vocabulary.py --check
$ python3 ec/tools/gen_xdata_symbols.py --check
$ python3 ec/tools/xdata_register_map.py --check
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x108F0 -n 16
$ grep -c "not present in this decompiled tree" ec/annotations/ghidra-functions.csv
```

All nine exit 0. `grep -c` returning 0 is the retraction check: no row is left
asserting that `0x1114` or `0x1100` is missing from the tree.