# The `0xA73F` notify path, decoded end to end

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every site and every
code below is a byte read out of `ec/firmware/GMxMGxx_11.800` by
`ec/tools/a73f_notify_census.py`, and the tool re-derives the whole table on
every run.

`0xA73F` is the routine the fan-duty publish path calls twice. It is four
instructions, and until now the row describing it stopped one hop short of
saying what it did. This is what it does, and why every annotation row that
routed through `0x1114` was wrong about why it stopped.

## The retraction: `0x1114` was never missing

`0xA73F` tail-jumps to `0x1666`, which loads DPTR with the constant `0x896A` and
tail-jumps to `0x1114`. Every trampoline row in that group read:

> Ghidra's C names 0x1114 bl51_bank_select_1, and 0x896A lies in the 0x8000-0xFFFF
> banked CODE window, but 0x1114 is not present in this decompiled tree, so what
> it does with DPTR is not decoded here.

**That sentence was false, and it is why the wall held.** `0x1114` is present
and decoded: `ec/decompiled/common/1114.asm` and `ec/decompiled/common/1114.c`,
named `bl51_bank_select_1`. It is ten instructions:

```
1114  c0 08     push 0x08
1116  74 11     mov  A, #0x11
1118  c0 e0     push A
111A  c0 82     push DPL
111C  c0 83     push DPH
111E  75 08 1e  mov  0x08, #0x1e
1121  d2 90     setb 0x90          ; P1.0
1123  c2 91     clr  0x91          ; P1.1
1125  c2 92     clr  0x92          ; P1.2
1127  22        ret
```

`common` is a scope of its own in `ec/annotations/ghidra-functions.csv`, and
these rows are filed under `bank0`. Reading a bank-scoped listing cannot see a
row filed under another scope, and "not present in this decompiled tree" was
the reading of a scope that was never searched. The same sentence appeared, in
different words, against the sibling stub `0x1100`, and that one was the same
scope error: `ec/decompiled/common/1100.asm` and `ec/decompiled/common/110A.asm`
decode it too.

Both retractions are made **in place** in the CSV, with the wrong claim left
visible beside the correction, the way `docs/findings.md` §4a-4d does it and
the way the `0x0EA2` row in the same file already does. A silent edit would
have left a reader three merges back with the false claim and nothing next to
it.

## What the stub does with DPTR

The pushed DPL/DPH are the return address. So `push DPL` / `push DPH` /
`ret` is the linker entering the target, and **the constant loaded into DPTR is
the call target** — which answers the question issue #248 opened with. Posting
to `0x896A` does not signal another bank; it re-enters the CPU, in whichever
bank the stub selects, at the address in DPTR.

Which bank is P1.0-2. `0x1100` clears all three, `0x1114` sets P1.0 and clears
the other two, `0x1128` sets P1.1, `0x113C` sets P1.0 and P1.1. So the four
stubs at `0x1100`, `0x1114`, `0x1128`, `0x113C` are bank 0, 1, 2 and 3, and
`0x1666`'s `0x896A` is **bank1's `0x896A`** — `gate_06e6_0440_then_call_89b5`.

The stub never touches R7. That matters, because it is what lets the chain be
followed.

## The chain, end to end

```
caller, R7 = code
  0xA73F   mov 0x6a, R7 / mov A, 0x6a / mov R7, A / ljmp 0x1666
  0x1666   mov DPTR, #0x896A / ljmp 0x1114
  0x1114   push DPL / push DPH / set P1.0 / clr P1.1 / clr P1.2 / ret
             -> re-enters the CPU in bank 1 at 0x896A, R7 unchanged
  0x896A   gate: XDATA 0x06E6 == 1 and XDATA 0x0440 != 0, else ret
  0x89B5   if bit 3 of XDATA 0x09F1 set, return without storing
           else  R7 -> XDATA 0x09F2 + (0x09F1 & 7), via 0x89E7
                 0x09F1 = ((0x09F1 & 0x77) + 1) & 0x77
```

**So the code is the payload of a queued entry, not a command a routine
interprets.** Nothing on this path tests the code byte. `0x896A` tests two
unrelated XDATA bytes and then stores; `0x89B5` stores. That confirms the
hypothesis issue #248 raised from the shape of `0xA3C3`, and it is the reason
no code can be given a meaning from this evidence — see "What this does not
say".

### Internal RAM `0x6A` is scratch, and a census this document first got wrong

`0xA73F` stores R7 to internal RAM `0x6A` and reads it straight back, and that
round trip is a no-op on the value. Which is the easy half. The census of who
else touches `0x6A` is where this document was wrong, so the correction is
recorded rather than made silently.

**The retracted claim.** An earlier version of this section said a scan of the
three EC code regions for direct accesses to `0x6A` "finds exactly two stores
and two loads", and concluded from that there was no second reader for `0x6A`.
Both halves are wrong. The repository already ships the tool for that question
— `ec/tools/intmem_refs.py`, whose docstring is explicit that the question it
answers is who *writes* a direct byte — and the committed image answers
differently. It is a much better answer than the one it replaces, because the
sites it turns up are mostly **not accesses to internal RAM `0x6A` at all**:

```sh
python3 ec/tools/intmem_refs.py ec/firmware/GMxMGxx_11.800 0x6A
```

That prints `refs=11 ec=11 pd=0`, and every one of the eleven is accounted for
below. The figures are stated once, here, because they are a property of the
committed image that no change to this repository can move.

**What the tool finds, and what each hit is.** Two `mov a,0x6a` reads, one
`dec 0x6a`, and eight `inc 0x6a`:

- The two reads are real and both are the readback half of a store in the same
  routine. Bank0 `0xA741` is `0xA73F` itself. Bank0 `0x85F7` is the readback
  of a `mov 0x6a,r7` two bytes earlier at `0x85F5`, in bytes that fall in no
  exported listing — `lcall 0x445E`, then `mov 0x6a,r7` / `mov a,0x6a` /
  `clr c` / `ret`.
- The stores are **not in the tool's output**, and that is the tool's own
  stated gap: `mov direct,Rn` (`0x8F`) has no row in its `OPCODE_TABLE`. The
  two `mov 0x6a,r7` sites are therefore counted here by looking for `8f 6a`,
  which is what the earlier version of this document did and what
  `intmem_refs.py` does not.
- The `dec 0x6a` at common `0x0E4D` is a misframing the tool's header predicts:
  the bytes are `02 15 6a`, which is `ljmp 0x156a`, and the pair a scan
  anchored one byte in reads as a `dec 0x6a`. Its framing score, 1 of 24,
  says so.
- **Seven of the eight bank1 `inc 0x6a` sites are not internal-RAM accesses.**
  Each is the `05 6a` inside `90 05 6a` — `mov dptr,#0x056a`, naming XDATA
  `0x056A`, which is a different address space. Their framing scores are 0 of
  24 and 1 of 24, and that 24 is the documented standing warning about this
  method: `docs/findings/scheduler-divide-down-cycle.md` corrects the same
  `90 05 44` misreading. XDATA `0x056A` is a real byte with its own annotated
  readers (`dispatch_on_056a_low3` at bank1 `0xADFD` and the writers beside
  it), which is exactly why reading its low two bytes as an internal-RAM
  instruction is a mistake worth naming rather than counting.
- The eighth, bank1 `0x8486`, is the one the `frame` column scores 24 of 24 and
  so cannot be dismissed on framing alone. Its bytes are
  `04 98 00 06 8a 00 05 60 00 05 6a 00 05 6b 00 04 95 00 04` — a run of 2-byte
  values in which every byte decodes as a 1- or 2-byte instruction, which is
  the shape `intmem_refs.py` pins as `0x16434` and warns is *why* a 24-of-24
  score is evidence and not proof. It sits in no exported listing and
  `ec/annotations/data-regions.yaml` does not label the span, so **this site is
  not adjudicated here**.

**What survives.** Of the eleven, the only direct internal-RAM `0x6A` accesses
are the two `mov 0x6a,r7` / `mov a,0x6a` pairs — one of them `0xA73F`, one in
the unlisted bytes at bank0 `0x85F5` — and each pair is a store immediately
followed by the readback of the byte it just stored. No routine in the image
was found to read a `0x6A` that another routine stored, so the byte reads as
`0xA73F`'s scratch rather than a mailbox. That remains a claim about what was
**found**: `intmem_refs.py` sees direct addressing only, indirect access is
invisible to it, and bank1 `0x8486` is left open above.

### The consumer side

The ring drains at bank1 `0x8940`, inside `saturating_count_09f0_then_call_88f0`
(`0x8915`), which pops the oldest entry through `0x897B` and stores it at XDATA
`0x047C`, then calls `0x88F0` with R5 preset to `0x53`. `0x88F0` pushes R5
into a second ring at `0x070F` and never branches on the code. `0x8915` is
already named and annotated in the CSV; **no seed row was added**, because
`0x8940` is inside that function rather than a function of its own, and adding
one would have split an existing export.

**Correction, on the merged tree (issue #1861).** An earlier version of this
section said the four ring bytes — `0x09F1`, `0x09F2`, `0x047C` and `0x09F0` —
"appear nowhere in `ec/annotations/registers.yaml`" and that they were "not added
here" as a scope decision, with the re-measurement of the `DAT_EXTMEM`/`symbol`
split and the `ORACLE` block named as the reason. **That is no longer true of
this tree, and the reason it gave is the one that did not hold.** All four are
rows in `ec/annotations/registers.yaml` now, filed by
`docs/findings/a73f-09f1-mailbox-payload.md` (issue #1444), together with
`0x070F`, `0x09EF`, `0x0A47`, the rest of both rings at `unknown-not-absent`,
and `site-resolution.csv` regenerated under them. The split and the pins moved,
and it was a sentence to write rather than a wall: `NOT_IN_TREE.update({...})`
has a block below every line a citation names, added for issue #575 for exactly
this case. What is left of the original reasoning is only that this decode did
not itself file them, and the item under "What this opens" below is closed by
that change rather than still open.

## The site census

Every call or jump site of `0xA73F`, and the code each carries. Generated by

```sh
python3 ec/tools/a73f_notify_census.py
```

| runtime | region | kind | code | verdict | R7 write | listing | note |
|---|---|---|---|---|---|---|---|
| 0x8867 | bank0 | lcall | 0xBB | resolved | 0x8865 | 0x8749 mode_tick_084c_07a5_09ee |  |
| 0x8993 | bank0 | lcall | 0xAC | resolved | 0x8991 | 0x8931 gate_0751_0741_blocks_then_tail_jump_8c46 |  |
| 0x8F17 | bank0 | lcall | 0xA7 | resolved | 0x8F15 | 0x8F0F store_a_to_dptr_then_075c_and_notify |  |
| 0x8F1C | bank0 | lcall | 0x43 | resolved | 0x8F1A | 0x8F0F store_a_to_dptr_then_075c_and_notify |  |
| 0x9FA0 | bank0 | lcall | 0xBC | resolved | 0x9F9E | 0x9D9B compute_level_blocks_086b_086c_086e |  |
| 0xA33D | bank0 | lcall | 0xAE | resolved | 0xA33B | 0xA312 gate_0494_then_dispatch_0851_and_7 |  |
| 0xA3D3 | bank0 | ljmp | - | unresolved | 0xA3D1 | 0xA3C3 on_0767_bit3_send_f160_then_896a | 2 paths into this site carry different codes |
| 0xABD0 | bank0 | ljmp | 0xB0 | resolved | 0xABCE | 0xAB9E set_0751_and_07a6_bits |  |
| 0xB10E | bank0 | lcall | 0xB6 | resolved | 0xB10C | 0xB0DC sync_0983_bit5_against_support_2_bit4 |  |
| 0xC5A5 | bank0 | lcall | - | unresolved | 0xC5A2 | 0xC55F FUN_CODE_c55f | fall-through: a lcall carries the value into the site, and no R7 write in this window follows it |
| 0xC603 | bank0 | lcall | - | unresolved | 0xC600 | 0xC5BD FUN_CODE_c5bd | fall-through: a lcall carries the value into the site, and no R7 write in this window follows it |
| 0xC729 | bank0 | ljmp | 0xB0 | resolved | 0xC727 | none exported |  |
| 0xC77F | bank0 | lcall | - | unresolved | 0xC77D | none exported | 2 paths into this site carry different codes |
| 0xC848 | bank0 | lcall | - | unresolved | 0xC845 | none exported | fall-through: a lcall carries the value into the site, and no R7 write in this window follows it |
| 0xC936 | bank0 | ljmp | 0xB9 | resolved | 0xC934 | none exported |  |

The `listing` column is the exported listing each site falls inside, joined on
`ec/decompiled/index.csv`. **Four of the sites fall in no exported listing**,
which is why an earlier reading of this list stopped at a subset: the codes
there are just as real, they are simply in regions the decompiler never
exported.

The issue's own table named six codes from four sites. The census is larger on
both axes, and four of the sites it adds carry a code the issue had not seen:
`0xAC`, `0xB6`, `0xB9` and `0xBC`.

### The refusals, and why they are refusals

Five sites are **unresolved**, and each says why rather than guessing:

| site | why |
|---|---|
| `0xA3D3` | reached two ways carrying `0xA8` (fall-through) and `0xA6` (a tail-jump from `0xA3AE`) |
| `0xC77F` | reached two ways carrying `0xB8` (fall-through) and `0xBA` (a `sjmp` from `0xC774`) |
| `0xC5A5` | the R7 in flight arrives in a callee's return value |
| `0xC603` | the R7 in flight arrives in a callee's return value |
| `0xC848` | the R7 in flight arrives in a callee's return value |

`0xA3D3` is worth a second look, because the `0xA3C3` annotation row reads as
though that site carries only `0xA8`. It does not: `0xA3AE` sets `0xA6` and
jumps to the same site, so `0xA6` is queued too. Two entries, two codes, and
which one ran depends on the path — which is exactly the kind of thing a
scan that reads only the fall-through gets wrong, and the reason the tool
refuses rather than picking one.

### A second census of the same sites, and where the two disagree

`docs/findings/a73f-09f1-mailbox-payload.md` (issue #1444) carries its own
table of the same sites, from `ec/tools/a73f_call_sites.py`, and **the two
censuses do not agree on the sites this one refuses.** That tool reads the
committed transfer census rather than re-scanning, and for two sites it settles
by a forward branch what this one refuses: it publishes `0xB1` at `0xC5A5` and
`0xB2` at `0xC603`, from `MOV R7,#0xb1` at `0xC579` + `SJMP 0xC5A5` at `0xC57B`
and `MOV R7,#0xb2` at `0xC5D7` + `SJMP 0xC603` at `0xC5D9`, each site's only
inbound branch. It also publishes `0xB8` at `0xC77F` and `0xA8` at `0xA3D3` —
the fall-through values this tool also sees — and it reports `0xC848` as
not-found, which is where the two agree.

**Neither tool is wrong and neither row should be edited to match the other.**
The difference is the method and it is a real one: this tool refuses a site it
reaches two ways carrying two codes, because "which one ran depends on the
path" is not a question a scan answers, whereas `a73f_call_sites.py` publishes
the fall-through reading and says so in its own column set. A reader sent here
for `0xC5A5` gets `unresolved`; a reader sent there gets `0xB1` with the
branch named. Both are true of the same bytes, and **the disagreement is the
finding**: a site reachable carrying two codes has no single answer, and a tool
that prints one without saying which path it took has answered a narrower
question than it appears to.

What the two share is more useful than where they differ: `a73f_call_sites.py`
and this tool find the same sites, read each one the same way wherever both of
them resolve it, and both leave `0xC848` open.

## What this does not say

- **No code is given a meaning.** Nothing on the decoded path tests the code
  byte. Naming what `0xA7` or `0x43` "selects" would be a guess with a byte
  behind it, which is the shape of overclaim CLAUDE.md puts above every other
  rule. The fan pair is *characterised by* a publish that is already fully
  understood (`0x8F0F` -> `0x075C` / `MAIN_FAN_R_DUTY`) and is enqueued only
  under `0x06E6 == 1 && 0x0440 != 0`; that is a fact about when it is posted,
  not about what it means.
- **No code is confirmed against an observable register change.** Issue #248
  hoped for one code tied to an effect. Static evidence does not reach one, and
  this does not claim it. A human at the machine would hold `0x047C` and
  `0x09F1` while a fan write happens; that run is not performed here and is not
  prepared by this document.
- **A site is found by a byte scan.** `12 a7 3f` in a table or a data region
  would still be reported, with its region and its framing verdict. Every site
  here decodes cleanly onto the address, but that is framing evidence and not
  proof that each is a call the CPU takes.
- **`0x6A`'s census is "not found by this method".** The census is
  `intmem_refs.py`'s and its figures are read off its output in "Internal RAM
  `0x6A`" above; indirect access would not appear to it, and the one site it
  leaves unadjudicated is named there rather than counted either way.
- **The constants reaching `0x1114` are a much larger open surface than the one
  entry group this decode walked, and none of the rest was followed.**
  An earlier version of this bullet named **seven** of them — `0x88F0`,
  `0xAA30`, `0xA916`, `0xF381`, `0xF160`, `0x8955`, `0xE56F` — as "the other
  constants reaching `0x1114`". That was wrong in the way this file's other
  corrections are wrong: the seven are the contiguous `0x163C`-`0x1672`
  trampoline entry group minus `0x896A`, the sentence never said so, and they
  are a small part of the population.

  `ec/tools/bl51_trampolines.py`, whose rule is the whole-body shape
  (`mov DPTR,#imm16` then `ljmp <stub>`) rather than the name, reports
  `0x1114=20` on its *annotated* line — twenty annotation rows, carrying
  twenty distinct constants, which is the whole of the annotated population.
  `0x896A` is one of them and the table below is the other nineteen. (The
  same tool's *across the export* line reads `0x1114=21`: the shape rule finds
  one more listing than the annotation CSV has a row for. That gap is the
  method's, not this section's, and the twenty is what a reader of the CSV can
  go and check.)

  Above the annotated rows, `ec/tools/census_forwarder_targets.py` counts the
  constants that reach the stub in the image itself rather than in an
  annotation row, and `ec/annotations/bank-call-audit.md` §2 records the same
  figure — so the annotated twenty are a subset of a larger population, and
  this section is not the place that population is enumerated.

  | trampoline | DPTR constant | its destination in `ec/annotations/ghidra-functions.csv` |
  |---|---|---|
  | `0x163C` | `0x88F0` | `bank1` `push_r5_into_070f_ring_when_gates_pass` |
  | `0x1648` | `0xAA30` | none in the CSV |
  | `0x164E` | `0xA916` | `bank1` `clamp_078b_level_into_0804` |
  | `0x1654` | `0xF381` | none in the CSV |
  | `0x1660` | `0xF160` | `bank1` `toggle_045b_bit0_set_0709_bit0` |
  | `0x166C` | `0x8955` | `bank1` `init_09f1_and_zero_09f2_through_09f9` |
  | `0x1672` | `0xE56F` | none in the CSV |
  | `0x18AC` | `0x83F8` | none in the CSV |
  | `0x18B2` | `0x81C5` | none in the CSV |
  | `0x18B8` | `0x823A` | none in the CSV |
  | `0x18BE` | `0x8261` | none in the CSV |
  | `0x18C4` | `0x818A` | none in the CSV |
  | `0x1906` | `0x8652` | none in the CSV |
  | `0x1936` | `0x9F01` | none in the CSV |
  | `0x1948` | `0xA694` | none in the CSV |
  | `0x194E` | `0xA69F` | none in the CSV |
  | `0x1954` | `0x92F7` | `bank1` `write_057b_057c_057d_and_call_888c` |
  | `0x1978` | `0xA710` | none in the CSV |
  | `0x197E` | `0xA6F7` | none in the CSV |

  The last column is the correction to an earlier reading of this section,
  which said each of these was "one `gate`/`writer` row away in
  `ec/annotations/ghidra-functions.csv`". Five of the nineteen are; **fourteen
  are not**, and a reader sent to the CSV for the other fourteen finds
  nothing. That is the difference between a question with a next step and one
  without, and it is why the column is here rather than a reassurance.

## Reproducing it

```sh
python3 ec/tools/a73f_notify_census.py            # the table above
python3 ec/tools/a73f_notify_census.py --csv      # one row per site
python3 ec/tools/a73f_notify_census.py --self-test
python3 ec/tools/test_a73f_notify_census.py       # the suite holding it to the image
python3 ec/tools/intmem_refs.py ec/firmware/GMxMGxx_11.800 0x6A   # the 0x6A census
python3 ec/tools/bl51_trampolines.py                # the 0x1114 constant table
python3 ec/tools/census_forwarder_targets.py        # every constant reaching the stub
python3 ec/tools/build_ec_decompile.py --work /tmp/ec --check
```

## What this opens

- **The four ring bytes want `registers.yaml` entries** — *closed by
  `docs/findings/a73f-09f1-mailbox-payload.md` (issue #1444), which files them
  and the rest of both rings; see the correction above.*
- **The ring has a producer and a consumer, so there is a second-writer
  question.** Who else writes `0x09F1` or `0x09F2` outside bank1 `0x89B5` and
  `0x8955`, and what acts on the code after `0x88F0` pushes `R5` past it?
  `0x88F0` pushes R5 and never branches on the code — the code's only consumer
  on this path is the zero test at `0x047C`.
- **The five unresolved sites are resolvable by a deeper method than this one.**
  Following into the callees at `0xC9FF`, `0xCA1D` and `0xA747` would say what
  the three `R7`-in-flight sites carry, and resolving the two two-candidate
  sites needs the branch conditions at `0xA3AE` and `0xC774`, not more scanning.
- **The four sites with no exported listing are a decompiler blind spot**, and
  seeding them as functions is how a listing would exist to read.
- **The `0x1100` family is now decoded too**, so the 403-trampoline audit in
  `ec/annotations/bank-call-audit.md` can attribute callers to banks it
  previously could not.
- **The other `0x1114` destinations are the natural next rows of a wider
  table.** `0x896A` was followed because it is on the fan-duty publish path,
  not because it was the only one decoded. `0xA916` and `0xF160` are already
  named at their destinations and are the cheapest of the rest to read, and
  the fourteen in the table above with no destination row are the ones where
  `docs/findings/trampoline-target-census.md`'s method — resolve the immediate
  in the bank the stub selects — is what turns a bare address into a body.