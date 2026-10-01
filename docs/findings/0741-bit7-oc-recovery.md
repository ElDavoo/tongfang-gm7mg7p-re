# One instruction sets AP_OEM bit 7, and the region it scans is 253 bytes rather than the three a committed annotation claimed

(Issue #114. Static reading of the committed firmware
`ec/firmware/GMxMGxx_11.800` plus the committed decompilations and tables.
No laptop, no EC and no Windows machine is involved: every address below is
re-derivable from that image with the commands in §8, and nothing here is a
live test of the byte.)

## The claim

**Of the 35 direct `MOV DPTR,#0x0741` sites, exactly one sets bit 7, and it
sets it when a two-bit accumulator reads exactly 3 — which happens when the
bytes `0x14` and `0x32` have both been seen in the 253-byte XDATA region
`0x0B00-0x0BFC`.**

That is the answer to the issue's third bullet. It is a reading of the code:
it says what the instructions do when they run, and it does **not** say the EC
ever ran them or that an overclock failure ever occurred. §7 is the limit, and
the load-bearing half of it is that *nothing in this tree is found to write
`0x0B00-0x0BFC`*, so the two marker bytes have no known source.

The same investigation corrects a committed annotation that was wrong about
this routine in a way that made the finding unreadable — §3.

## 1. The one setter

```
CFEE     90 07 41 mov      DPTR, #0x741
CFF1     e0 - -   movx     A, @DPTR
CFF2     44 80 -  orl      A, #0x80
CFF4     f0 - -   movx     @DPTR, A
```

Eight bytes, and the whole of the setter. It sits at the tail of the
already-annotated bank0 routine `0xCFC6`,
`collect_two_flags_into_0816_then_raise_ap_oem_bit7`
(`ec/annotations/ghidra-functions.csv`). The per-site table in
`ec/annotations/ap-oem-0741-bit7-sites.csv` carries all 35 sites with their
windows, and `0xCFEE` is the only row whose window contains an `orl a,#0x80`.

The other 34 split cleanly by bit, and the committed table's `window` column
is what the split is read from: the majority test or clear **only bit 0** —
`anl a,#0x01` and `jb`/`jnb acc.0`, `AP_OEM`'s documented meaning — while the
rest work on bits 2, 4 and 5. Of the 34, **only the two clears in §5 touch
bit 7.**

## 2. The condition, and what `0xD078` reads

`0xCFC6` is a scan loop with a two-bit accumulator:

```
CFC6     e4          clr      A
CFC7     fd          mov      R5, A
CFC8     12 d0 78    lcall    0xd078        ; byte at XDATA[0x0B00 + R5]
CFCB     b4 14 07    cjne     A, #0x14, 0xcfd5
CFCE     90 08 16    mov      DPTR, #0x816  ; bit 0 if it was 0x14
CFD5     12 d0 78    lcall    0xd078        ; the *same* byte again
CFD8     b4 32 07    cjne     A, #0x32, 0xcfe2
CFDB     90 08 16    mov      DPTR, #0x816  ; bit 1 if it was 0x32
CFE2     0d          inc      R5
CFE3     ed          mov      A, R5
CFE4     b4 fd e1    cjne     A, #0xfd, 0xcfc8   ; <- the back-edge
CFE7     90 08 16    mov      DPTR, #0x816
CFEA     e0          movx     A, @DPTR
CFEB     b4 03 07    cjne     A, #0x3, 0xcff5    ; <- the guard on the setter
CFEE     90 07 41    mov      DPTR, #0x741        ; the equal case:
CFF1     e0          movx     A, @DPTR             ; set bit 7 and return
CFF2     44 80       orl      A, #0x80
CFF4     f0          movx     @DPTR, A
```

The address arithmetic is `0xD078` in full, twelve bytes, no branch in it:

```
D078  74 00     mov  A,#0x00
D07A  2d        add  A,R5
D07B  f5 82     mov  DPL,A
D07D  e4        clr  A
D07E  34 0b     addc A,#0x0b
D080  f5 83     mov  DPH,A
D082  e0        movx A,@DPTR
D083  22        ret
```

`DPL` takes the low byte of `0x0B00 + R5` and `DPH` the high byte, so the
routine reads `XDATA[0x0B00 + R5]` and returns the byte. The Ghidra C spells the
same thing as `CONCAT11(0xb, param_1)`, which is the giveaway that made it worth
naming; the disassembly is what the claim above rests on.

**The two calls per iteration read the same address.** `R5` is not advanced
between them, so both `cjne`s test the byte at `0x0B00 + R5`, and a byte can
never be both `0x14` and `0x32`. `0x0816 == 3` therefore requires the two
markers at **different offsets** in the region — one byte seen twice does not
constitute a scan result.

So the condition is: `0x14` appears somewhere in `0x0B00-0x0BFC`, **and**
`0x32` appears somewhere in it, at an offset that is not the `0x14` one. That
is what raises the BIOS's overclock-recovery request.

## 3. The correction: the loop runs 253 times, not three

The committed `0xCFC6` annotation read:

> Runs three iterations of a counter held in R5; each iteration calls 0xD078
> twice […]

**That is wrong, and the wrongness is what made the finding unreadable.** The
back-edge is `CFE4 b4 fd e1` — `cjne A,#0xfd,0xcfc8` — so the loop continues
until `R5` reaches `0xFD`. `R5` starts at `0x00` and is incremented once per
pass, so the body runs for `R5 = 0x00` through `0xFC` inclusive: **253
iterations**, scanning `0x0B00` through `0x0BFC`.

Where "three" came from is worth recording, because it is a decompiler-reading
error rather than a careless one. `CFC6.c` renders the test as
`while (cVar1 != -3)`, and `0xFD` as a signed `char` is `-3`. The value is
right and the reading is wrong: `0xCFC6.asm` is where the bytes are, and the
`.c` is a reading of them.

Three iterations would scan three bytes, and the committed comment went on to
say that "what address `0xD078` reads is not determined from this listing" —
which left the routine looking like a three-byte coincidence check over an
unknown address. At 253 iterations over a known region it is a marker scan,
and it joins the two other routines that scan the same region (§4).

The correction is in place in `ec/annotations/ghidra-functions.csv`, with the
superseded sentence kept beside the corrected one, and §7 of this file is the
standing limit on what the corrected reading licenses.

**One generated table moves with it, and the reason is worth naming.**
`ec/annotations/call-graph-callees.csv` gains a citation for `bank0:0xD078`
(`cited_by` 0 → 1, citing `bank0:CFC6`). That is not a side effect of the loop
count; it is the *removed sentence*. The old comment's closing claim — "what
address `0xD078` reads is not determined from this listing" — parses as a data
frame on `0xD078`, and `call_graph.py`'s citation rule vetoes a pair when any
mention of the address carries one, so the old comment's "calls `0xD078`" never
counted as a call citation. Correcting the sentence that was *false* un-vetoes
it: the comment now credits `0xD078` for the call it always described. The
table is regenerated, and the row is the only one that changes.

## 4. `0x0B00-0x0BFC` is a marker-scan buffer, and three routines scan it

The region is zeroed at init by the common-area routine `0x2896`
(`clear_iram_6d_7f_then_xdata_b00_bfe`), whose second loop is
`7f fd` / `mov DPTR,#0x0B00` / `movx @DPTR,A` / `inc DPTR` / `djnz R7` — 253
iterations over exactly this span, followed by explicit clears of `0x0BFD` and
`0x0BFE`.

Three routines then scan it, for three different marker bytes:

| routine | byte sought | on match |
| --- | --- | --- |
| bank0 `0xCFC6` (via `0xD078`) | `0x14` then `0x32` | latches into `0x0816`; sets `0x0741` bit 7 when both seen |
| bank1 `0xA43B` `scan_0b00_for_byte_1c` | `0x1C` | tail-jumps to `0xA44C`, clearing `0x0750` |
| bank1 `0xAAA2` `clear_0756_when_1c_found_in_b00_fc` | `0x1C` | clears `0x0756` and returns |

The two bank1 scanners are already annotated and already say they stop when
`DPL` reaches `0xFD`, "0x0B00 to 0x0BFC inclusive, 253 bytes" — the same span,
reached independently. That agreement is the check on §3: three routines
written separately agree on 253, and the one whose annotation said three was
the one whose annotation was wrong.

**No writer of the region is found by any method in this tree** — §7.

## 5. Three sites clear bit 7, and two of them clear the latch with it

The set-flag half of the sequence is well bracketed:

- **`0xCFEE`** — the setter (§1).
- **`0xCF78`** — `mov DPTR,#0x741` / `movx A,@DPTR` / `anl A,#0x7f` /
  `movx @DPTR,A` / `clr A` / `mov DPTR,#0x816` / `movx @DPTR,A` /
  `ljmp 0xCDE4`. This is the **`0x81` arm** of the dispatcher at `0xCF48`
  (`dispatch_06e6_after_counting_down_06e8_pair`): the dispatcher counts the
  16-bit pair `0x06E8/0x06E9` down with `0x70E4` and only dispatches once it
  reaches zero, then selects on `0x06E6` — `0x82`/`0x83`/`0x84` tail-jump to
  `0xCE9E`/`0xCEE9`/`0xCE37`, `0x81` clears the flag *and* the latch, and any
  other value clears `0x06E6`.
- **`0xAD46`** — the same `anl a,#0x7f` followed by `clr A` and
  `mov DPTR,#0x816`, then `lcall 0xBC3F`, which is a store of the caller's `A`
  through whatever DPTR it was handed. It sits inside the whole-machine reset
  pass at `0xACB4` (`reset_xdata_flags_and_07d5_to_ff`).
- A fourth clearer is the BIOS's own `0xA5` write-back, which is host-side and
  not EC code at all.

**`0x0816` behaves as a latch, not a scratch byte.** All five of its bank0
sites are inside this one chain — `0xCF80` and `0xAD4E` (the two clears),
`0xCFCE`/`0xCFDB` (the two setters) and `0xCFE7` (the read that guards the
flag). The other four of its nine total sites are in the PD image, which is a
separate program with its own XDATA map and is not evidence about this one.

So the sequence the EC implements is **set flag → latch → clear flag and
latch**: `0xCFC6` raises the request, `0x0816` remembers what it found, and
each of the two bank0 clears takes both back down. The reset pass at `0xAD46`
and the `0x06E6` dispatcher arm at `0xCF78` are the two places that arm is
taken back.

## 6. How `0xCFC6` is reached, and what is not annotated

`0xCFC6` has **no `lcall` caller** in either bank or the PD image. Scanned as
raw bytes over all three programs, the pattern `12 cf c6` finds nothing and
`02 cf c6` finds exactly one hit — the `ljmp` below. It is
reached by `ljmp 0xCFC6` at `0x8521`, the tail of a three-instruction run at
`0x851B` (`lcall 0xA7C8` / `lcall 0xA844` / `ljmp 0xCFC6`). That run is itself a
far-call-stub target: `ec/annotations/task-call-table.csv` carries the row
`far-call-stub,0x1150,174,0x1564,ljmp,0x851B`, so the common-area dispatch
table at `0x1150` reaches it through the `0x1564` stub.

The two sibling arming routines reach the same dispatcher from bank1 the same
way, through the bank-select trampolines at `0x19A2` → `0xCF96` and `0x19AE` →
`0xCFA9`; `arm_index_06e7_for_dispatch_06e6` at `0xCF96` writes the `0x06E7`
index and zeroes the `0x06E8/0x06E9` countdown the dispatcher waits on. Those
trampolines are called from eight and three bank1 sites respectively.

**What this does not add.** The task run at `0x851B` is not in
`ec/annotations/ghidra-functions.csv`, and is not a separate function boundary
in the committed `ec/decompiled/index.csv` either — it is reached by the
far-call table rather than by any `lcall`, which is the case CLAUDE.md's "an
annotation row also seeds a function entry" rule exists for. Seeding it is a
project change (`--mode rebuild-project`), so it is left as the follow-up this
file names rather than done here: the `0xCFC6` correction is an export-only
change and ships on its own. Nothing in this section is needed for the claim in
§1–§2.

(The neighbouring `0x84EB` is the same *shape* — a far-call-stub target with no
referrer anywhere in the image and no annotation row — but it is a different
task entry and no link between it and this chain was found. It is named here
only so the next reader does not mistake it for one.)

## 7. Limits

**The writer of `0x0B00-0x0BFC` is not found.** `find_indirect_xdata.py
--page 0x0B` resolves **0 of 91** anchored `movx @Ri` sites on that page — all
91 are reported unresolved by "no P2 write in the window" — so the indirect
addressing mode finds no writer either. The only writer this tree names is the
init clear at `0x2896`. **That is "not found by this method", not "there is
none"**, and the distinction is the whole reason this section exists: the
region is provably read as a marker buffer by three routines, so something
writes it through a path these tools cannot see. Until that path is found, it
is unknown whether the `0x14`/`0x32` bytes this routine tests for correspond to
real POST or overclock outcomes, and that is the question that decides whether
the recovery net is real.

**Nothing here is a live test.** No register was read back and no hardware was
observed. The claim in §1 is what the bytes say the EC does; it is not a
statement that the EC did it, and `0x0741`'s `status:` stays
`confirmed-working` **for bit 0 only**, exactly as its note already said.

**This is a static reading of a scan loop.** The `0x0816 == 3` test is
`cjne A,#0x3` against the byte as stored, so any other writer of `0x0816` in
this bank would change what the equality means. The five bank0 sites are all in
the chain §5 describes, which is what makes that a closed set *for this bank*
— not for the PD image, whose `0x0816` is a different program's byte.

**`0xA2`-`0xA5` host-command handler: not found.** The issue's second bullet is
out of reach with the methods in this tree, and saying so is the deliverable
rather than a gap in it. `ec/annotations/subsystems.md` §9 records that the
`0x62`/`0x66` index/data pair "does not exist in the 8051 at all" — it is the
ACPI EC interface, already mapped on the BIOS side — and
`ec/annotations/xdata-086x-dispatch.md` notes that a host path would have to
arrive through a computed DPTR, the blind spot its §2 names for every address
on that page. All 15 tables read by the `0x7151` switch reader are accounted for in
`ec/annotations/index-table-spans.csv` and none is a command table;
`decode_index_table.py` has swept them. Closing this needs a method that does
not exist yet.

## 8. Reproducing the table

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0741 --counts-only
0x0741: 35 direct MOV DPTR site(s)  bank0=30  bank1=5

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0741 --csv \
          --terminator-column \
          > ec/annotations/ap-oem-0741-bit7-sites.csv

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0xCFEE -n 6
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0xD078 -n 12
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --page 0x0B
```

The second command wrote the committed table; the first is the site count,
and the last exits non-zero because nothing resolvable reaches the page —
which is the §7 result, not an error.
`ec/tools/test_0741_bit7_chain.py` re-runs the second against the committed CSV
and holds the byte facts above against the image, so a stale pair fails rather
than agreeing with itself.