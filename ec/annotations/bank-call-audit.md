# Direct call targets in the main EC image — is the same-bank assumption safe?

`../tools/trace_xdata_refs.py`'s `offset_for_runtime()` maps a call target back
to a file offset on the ordinary Keil banking convention: a target below
`0x8000` is in the common area, a target at or above `0x8000` is in the *same*
bank as the caller. Every EC-side handoff `register_ref_table.py
--callee-depth 1` resolves inherits that convention, so this file counts the
populations it applies to and says what the bytes do and do not settle.

**Headline, and it is the §4c shape, not a proof.** `bank0` and `bank1` share
base `0x8000` in `REGIONS`, and nothing in an `lcall` names a bank: a
bank-to-same-bank call and a bank-to-other-bank call are the same three bytes.
No enumeration can prove the assumption from this image. What the enumeration
does establish:

- **No direct cross-bank call was found by this method.** Of the 1305 distinct
  (caller bank, target) pairs behind bucket B, not one has erased flash in the
  caller's own bank while the other bank holds live bytes — the shape that
  would falsify the assumption. Eleven have the reverse (own bank live, other
  bank erased), which is consistent with it. §4.
- **The linker's cross-bank path is visible and counted**, and it is not a
  direct call: 403 BL51 trampolines in the common area, and `bank1` reaches
  `bank0` through 229 of them while `bank0` reaches `bank1` through 61. §3.
- **Bucket C is *not* empty**: 140 common-area sites by byte scan, 83 of them
  anchored, target `≥ 0x8000`. `offset_for_runtime()` returns `None` for that
  shape and still should — the issue is right that it is unresolvable. Every
  one this file read the bytes for turned out to be a misframed address table
  rather than a call, but 83 sites were not cleared one by one and this file
  does not claim they were. §5.
- **The 2-byte paged family is now counted too, and it is not a banking
  question.** 3481 `ajmp`/`acall` sites by byte scan, 1667 of them anchored.
  An `ajmp`/`acall` target is inside the page the caller is already executing
  from, so it cannot cross a bank — which *narrows* the population the
  same-bank assumption carries rather than telling us anything new about it.
  §7.
- **The PC-relative family is now counted too, and it is the last
  statically-resolvable one.** 9076 `sjmp`/`jc`/`jnc`/`jz`/`jnz`/`jb`/`jnb`/
  `jbc`/`cjne`/`djnz` sites by byte scan, 6675 of them anchored. A rel8 target
  sits within [-128, +127] of the next PC, so unlike a paged target it *can*
  leave the caller's region — 4 of the 9076 do, all from within 96 bytes of
  `bank0`'s start, and all 4 were read byte by byte: three are operand bytes of
  an `lcall` and the fourth an address-table entry. §8.

No code change to `offset_for_runtime()` follows from this: its `None` return
for bucket C is unchanged, and its same-bank reading for bucket B is not
contradicted by anything here. The docstring's hedge is narrowed from "has not
verified" to "not found by this method, here is the enumeration", which is all
the evidence supports. Nothing in this file was measured on hardware; nothing
here is evidence about any register's behaviour, so no `status:` in
[`registers.yaml`](registers.yaml) moves.

## 1. Reproducing it

```console
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800
## 1. Call-target buckets, as `byte-scan upper bound / anchored-decode count`

| region | A: target < 0x8000 | B: >= 0x8000 from a bank | C: >= 0x8000 from common |
|---|---:|---:|---:|
| `common` | 1783 / 1702 | - | 140 / 83 |
| `bank0` | 400 / 330 | 1612 / 1501 | - |
| `bank1` | 414 / 273 | 1649 / 1441 | - |

## 2. Where the linker's own cross-bank calls go

  stub 0x1100 selects bank 0: 350 trampoline(s) route through it
  stub 0x1114 selects bank 1: 53 trampoline(s) route through it
  stub 0x1128 selects bank 2: 0 trampoline(s) route through it
  stub 0x113C selects bank 3: 0 trampoline(s) route through it
  403 trampolines, common area 0x1150-0x1ABC, 403 of them targeting >= 0x8000

Calls into that trampoline block, by the bank the trampoline selects:

| caller region | -> bank 0 | -> bank 1 |
|---|---:|---:|
| `common` | 229 / 228 | 2 / 2 |
| `bank0` | 2 / 1 | 61 / 61 |
| `bank1` | 229 / 222 | - |

Calls to a stub address itself. Every one of these is a trampoline's
own tail instruction -- trampolines() found them by that shape -- so a
count here that exceeds the trampoline count would be a caller reaching
a stub without setting DPTR first:
  common: 350 / 350 to the bank-0 stub
  common: 53 / 53 to the bank-1 stub

## 3. Bucket B: what each target's own bank holds, against the other bank
[...heuristic caveat, reproduced in §4 below...]

| caller | distinct targets | own / other bank | targets | sites |
|---|---:|---|---:|---:|
| `bank0` | 697 | `entry` / `other` | 350 | 756 |
|  |  | `entry` / `entry` | 155 | 368 |
|  |  | `other` / `other` | 130 | 346 |
|  |  | `other` / `entry` | 47 | 105 |
|  |  | `entry` / `erased` | 9 | 27 |
|  |  | `erased` / `erased` | 4 | 4 |
|  |  | `other` / `erased` | 2 | 6 |
| `bank1` | 608 | `entry` / `other` | 306 | 613 |
|  |  | `entry` / `entry` | 131 | 258 |
|  |  | `other` / `other` | 125 | 582 |
|  |  | `other` / `entry` | 44 | 192 |
|  |  | `erased` / `erased` | 2 | 4 |

## 4. Bucket C: the sites offset_for_runtime() returns None for

  140 site(s) upper bound, 83 anchored, 102 distinct target(s)
  1 of those targets is/are also a banked entry point some trampoline names

The most strongly framed of them, by converges_from() score -- the ones
worth reading bytes for before treating any of this bucket as a call:

| file | ljmp/lcall | target | frame onto/over | preceding bytes |
|---|---|---|---:|---|
| `0x00686` | ljmp | `0xFD03` | 24/24 | `01 e3 01 e6 01 e9` |
| `0x021C6` | lcall | `0xE000` | 24/24 | `12 00 e0 59 00 e0` |
| `0x06952` | ljmp | `0xFF17` | 24/24 | `f6 ff 16 fc ff 17` |
| `0x06E83` | ljmp | `0xAA02` | 24/24 | `04 21 03 ba 03 32` |
| `0x0067E` | ljmp | `0x9B01` | 23/24 | `01 2c 01 2f 01 8c` |
| `0x055DC` | ljmp | `0xEC02` | 23/24 | `03 11 03 05 02 f9` |
| `0x055E0` | ljmp | `0xD402` | 21/24 | `02 f9 02 ec 02 e0` |
| `0x055E4` | ljmp | `0xBC02` | 19/24 | `02 e0 02 d4 02 c8` |
| `0x055EA` | ljmp | `0x9702` | 17/24 | `02 bc 02 af 02 a3` |
| `0x00381` | lcall | `0x9402` | 15/24 | `12 88 02 12 8e 02` |

## 5. The 2-byte paged family: `ajmp`/`acall`
[...the confinement argument and the over-counting caveat, both in §7 below...]

| region | ajmp | acall | both |
|---|---:|---:|---:|
| `common` | 692 / 378 | 784 / 439 | 1476 / 817 |
| `bank0` | 666 / 230 | 338 / 168 | 1004 / 398 |
| `bank1` | 703 / 306 | 298 / 146 | 1001 / 452 |

| region | entry | other | erased |
|---|---:|---:|---:|
| `common` | 309 / 151 | 1163 / 663 | 4 / 3 |
| `bank0` | 247 / 94 | 738 / 298 | 19 / 6 |
| `bank1` | 245 / 109 | 681 / 338 | 75 / 5 |

Paged sites landing on the BL51 path. The trampoline block 0x1150-0x1ABC
spans pages a common-area paged call can reach from inside, so unlike the
banks this is a route a paged instruction could take:
  common: 17 / 4 onto a bank-0 trampoline entry
  common: 1 / 0 onto a bank-1 trampoline entry

  0 of 3481 paged site(s) resolve outside the caller's own region

## 6. The PC-relative family: `sjmp`/`jc`/`jnc`/`jz`/`jnz`/`jb`/`jnb`/`jbc`/`cjne`/`djnz`
[...the rel8 reach argument and the over-counting caveat, both in §8 below...]

| region | sjmp | jc | jnc | jz | jnz | jb | jnb | jbc | cjne | djnz | all |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `common` | 340 / 307 | 200 / 160 | 69 / 58 | 255 / 241 | 203 / 183 | 197 / 157 | 359 / 306 | 423 / 65 | 566 / 307 | 173 / 107 | 2785 / 1891 |
| `bank0` | 383 / 331 | 194 / 147 | 165 / 158 | 431 / 421 | 291 / 270 | 212 / 150 | 253 / 219 | 192 / 40 | 870 / 406 | 290 / 115 | 3281 / 2257 |
| `bank1` | 601 / 532 | 256 / 217 | 161 / 151 | 289 / 279 | 295 / 288 | 289 / 230 | 236 / 195 | 127 / 59 | 570 / 462 | 186 / 114 | 3010 / 2527 |

| region | 2-byte | 3-byte |
|---|---:|---:|
| `common` | 1223 / 1048 | 1562 / 843 |
| `bank0` | 1737 / 1435 | 1544 / 822 |
| `bank1` | 1774 / 1573 | 1236 / 954 |

| region | entry | other | erased |
|---|---:|---:|---:|
| `common` | 1391 / 995 | 1393 / 896 | 1 / 0 |
| `bank0` | 1829 / 1549 | 1442 / 700 | 6 / 5 |
| `bank1` | 1766 / 1578 | 1244 / 949 | - |

Relative sites landing on the BL51 path. A common-area branch can
reach the trampoline block 0x1150-0x1ABC if it starts near enough to
it; a bank never can:
  common: 168 / 1 onto a bank-0 trampoline entry
  common: 2 / 0 onto a bank-1 trampoline entry

  4 of 9076 relative site(s) resolve outside the caller's own region
    0x0803B sjmp -> 0x7FD1, 59 byte(s) from a bank0 edge, frame 24/24
    0x0802C cjne -> 0x7FD2, 44 byte(s) from a bank0 edge, frame 3/24
    0x0805F cjne -> 0x7FF2, 95 byte(s) from a bank0 edge, frame 1/24
    0x08060 djnz -> 0x7FF2, 96 byte(s) from a bank0 edge, frame 0/24

$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test
  ok   4 BL51 stub sites at 0x1100, 0x1114, 0x1128, 0x113C selecting banks 0-3 (got 0x1100=bank0, 0x1114=bank1, 0x1128=bank2, 0x113C=bank3)
  ok   the `C0 08 74` prologue occurs 4 times in the main EC image (got 4)
  ok   and 0 times in the PD image (got 0)
  ok   offset_for_runtime()/runtime_addr() round-trip for every mapped region
  ok   a common-area call to 0x8000 stays unresolvable (bucket C returns None)
  ok   file 0x02190 (runtime 0x2190) is `01 09` targeting 0x2009 (got `01 09` -> 0x2009)
  ok   file 0x167FF (runtime 0xE7FF) is `01 53` targeting 0xE853 (got `01 53` -> 0xE853)
  ok   0xE7FF's target 0xE853 is in the next instruction's page 0xE800, not the opcode's own 0xE000
  ok   every mapped region is a whole number of 2 KiB pages aligned identically in file offset and runtime base -- the property the never-leaves-its-region claim rests on
  ok   all 3481 paged site(s) in the audited regions resolve inside the caller's own region
  ok   file 0x0B2EE (runtime 0xB2EE) is `80 6e` targeting 0xB35E in the site walk (got `80 6e` -> 0xB35E)
  ok   file 0x0B137 (runtime 0xB137) is `20 e0 07` targeting 0xB141 in the site walk (got `20 e0 07` -> 0xB141)
  ok   file 0x0F1B0 (runtime 0xF1B0) is `df e6` targeting 0xF198 in the site walk (got `df e6` -> 0xF198)
  ok   file 0x0FE24 (runtime 0xFE24) is `30 e1 e8` targeting 0xFE0F in the site walk (got `30 e1 e8` -> 0xFE0F)
  ok   reading a 3-byte form's displacement from the second byte instead of the last misses: 0x0B137 -> 0xB11A, not 0xB141, 0x0FE24 -> 0xFE08, not 0xFE0F
  ok   4 of 9076 relative site(s) resolve outside the caller's own region, every one of them within 128 bytes of a region edge as the rel8 range requires

self-test passed

$ python3 ec/tools/disasm8051.py --self-test | tail -6
  ok  file 0x0B2EE (runtime 0xB2EE) is `80 6e` targeting 0xB35E (got `80 6e` -> 0xB35E)
  ok  file 0x0B137 (runtime 0xB137) is `20 e0 07` targeting 0xB141 (got `20 e0 07` -> 0xB141)
  ok  file 0x0F1B0 (runtime 0xF1B0) is `df e6` targeting 0xF198 (got `df e6` -> 0xF198)
  ok  file 0x0FE24 (runtime 0xFE24) is `30 e1 e8` targeting 0xFE0F (got `30 e1 e8` -> 0xFE0F)

self-test passed: both charge-profile-flow.md windows decode identically and all 4 relative-branch sites resolve as hand-decoded
```

[`bank-call-targets.csv`](bank-call-targets.csv) is `--csv` on the same image —
one row per `lcall`/`ljmp` site, 5998 of them —
[`bank-paged-call-targets.csv`](bank-paged-call-targets.csv) is `--paged-csv`,
one row per `ajmp`/`acall` site, 3481 of them, and
[`bank-relative-branch-targets.csv`](bank-relative-branch-targets.csv) is
`--relative-csv`, one row per relative-branch site, 9076 of them:

```console
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --relative-csv \
    > ec/annotations/bank-relative-branch-targets.csv
```

Every table above is a group-by over committed data rather than a number to be
taken on trust — §8 shows the one that re-derives its own tables. The three
files are siblings rather than one file, because `bucket`, `own_bank` and
`other_bank` are absolute-form questions with no answer for a paged or relative
site, while `length` and `disp` only mean anything for a relative one;
`bank-call-targets.csv` and `bank-paged-call-targets.csv` are both
byte-identical to what they were before §8 existed.

## 2. Why two numbers per count, and why neither is the number

`0x02` and `0x12` are also operand bytes inside other instructions and inside
data tables, so a byte scan over-counts. A linear decode does not over-count
the same way but is only as good as its starting frame, which is why
`disasm8051.converges_from()` exists at all. Every count above is therefore
reported as `upper bound / anchored`, where `anchored` means at least one of
the 24 preceding byte anchors decodes exactly onto the site.

**The anchored number is not the phantom-free one.** `0x055DC` scores 23 of 24
and is inside a table of 16-bit addresses:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x55d0; pd 4' /tmp/bank0.bin
            0x000055d0      03             rr a
            0x000055d1      36             addc a, @r0
            0x000055d2      03             rr a
            0x000055d3      29             add a, r1
```

The bytes are `03 36 03 29 03 1d 03 11 03 05 02 f9 02 ec 02 e0 02 d4 …` — a
descending run of `0x0336`, `0x0329`, `0x031D`, `0x0311`, `0x0305`, `0x02F9`,
`0x02EC`, … read as big-endian words, which is a dispatch table, not six
`ljmp`s into bank space. A dense table converges because *any* walk through
uniform-length entries resyncs, not because the frame is right. Read the pair
of numbers, and read bytes before treating any individual site as a call.

## 3. The BL51 trampoline path — and what the stub evidence does not license

[`lightbar-bat-flow.md`](lightbar-bat-flow.md) §2 already records that the Keil
BL51 bank-switch stub prologue `C0 08 74` appears 4 times in the main EC image
and zero times in the PD image, and that `find_banks.py` finds no trampoline
callers for banks 2 and 3. `--self-test` re-checks all three of those, so they
are a guard here rather than a quotation.

What this audit adds is the traffic on that path. Each stub is fronted by a
block of trampolines — `mov dptr,#target ; ljmp/lcall <stub>` — occupying the
contiguous common-area range `0x1150`-`0x1ABC`, 403 of them, every one
targeting `≥ 0x8000`. Counting who calls *into* that block:

| caller region | → bank-0 trampolines | → bank-1 trampolines |
|---|---:|---:|
| `common` | 229 / 228 | 2 / 2 |
| `bank0` | 2 / 1 | 61 / 61 |
| `bank1` | 229 / 222 | — |

`bank1` calls 229 bank-0 trampolines and no bank-1 ones; `bank0` calls 61
bank-1 trampolines. That is the cross-bank traffic, and it is indirect by
construction — a bank never names the other bank's code address in an
instruction, it calls a common-area thunk whose target `≥ 0x8000` is only
meaningful after the stub has switched the bank in. `bank0`'s two calls to
bank-0 trampolines are a same-bank call taking the long way round; only one of
the two is anchored, so one may be a phantom, and neither changes anything.

**What the stub evidence licenses.** It shows the *compiler and linker's* path
for a cross-bank call in this build, with counts. It does not show that no
cross-bank `lcall` exists: hand-written assembly, an interrupt vector, or a
tail call emitted outside BL51's banking discipline would not appear in the
trampoline block, and nothing in this image rules that out. It is evidence
about the mechanism, not an exhaustion argument.

## 4. Bucket B, target by target

For every distinct target `≥ 0x8000` called from a bank, the byte at that
address is read in *both* banks and labelled: `entry` if it is one of
`find_banks.py`'s `START_OPCODES`, `erased` if it sits inside a run of at least
16 `0xFF` bytes, `other` otherwise. `START_OPCODES` is a scoring heuristic, not
a decode, and is used here as exactly that.

**Why 16 bytes and not one.** `find_banks.py` tests a single byte for `0xFF`,
which is right for the question it asks and wrong for this one: `0xFF` is
`mov r7,a`, one of the commonest bytes in Keil C51 output. Four bucket-B
targets in this image begin with a lone `0xFF` and continue into ordinary code
— `0xBAD4`, `0xBAF4`, `0xBB90`, `0xBD54` — and a one-byte test reported all
four as calls into erased flash, i.e. as cross-bank candidates. They are not:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xbaf4; pd 6' /tmp/bank0.bin
            0x0000baf4      ff             mov r7, a
            0x0000baf5      ec             mov a, r4
            0x0000baf6      fe             mov r6, a
            0x0000baf7      ee             mov a, r6
            0x0000baf8      f0             movx @dptr, a
            0x0000baf9      a3             inc dptr
```

With the run-length definition, the falsifying shape — **own bank erased,
other bank live** — occurs **zero times** across all 1305 distinct
(caller bank, target) pairs. The three spot-checks below are the cases that matter, each
listed in both banks so the claim is checkable by eye.

**Own bank live, other bank erased (11 targets, 33 sites).** `bank0` runtime
`0xF1F0` does `lcall 0xF495`; bank 0 has code there, bank 1 has erased flash:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf1f0; pd 1' /tmp/bank0.bin
            0x0000f1f0      12f495         lcall 0xf495
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf495; pd 3' /tmp/bank0.bin
            0x0000f495      900f60         mov dptr, #0x0f60
            0x0000f498      f0             movx @dptr, a
            0x0000f499      900a56         mov dptr, #0x0a56
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf495; pd 3' /tmp/bank1.bin
            0x0000f495      ff             mov r7, a
            0x0000f496      ff             mov r7, a
            0x0000f497      ff             mov r7, a
```

Bank 1's `0xF495` is inside the `0x17460`-`0x18000` erased tail of that bank,
so the same-bank reading is the only one that lands on code. This is the
strongest positive case the bytes offer, and it covers 33 of the 3261
bucket-B sites.

**Both banks live — the ambiguity, and it is 1288 of the 1305 pairs** (286 of
them score `entry` in both banks, the rest `other` somewhere). `bank0` runtime
`0x8040` does `ljmp 0x811A`, and `0x811A` decodes as plausible code in both:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x811a; pd 3' /tmp/bank0.bin
            0x0000811a      90190c         mov dptr, #0x190c
            0x0000811d      e0             movx a, @dptr
        ┌─< 0x0000811e      20e703         jb acc.7, 0x8124
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x811a; pd 3' /tmp/bank1.bin
            0x0000811a      900982         mov dptr, #0x0982
            0x0000811d      e0             movx a, @dptr
        ┌─< 0x0000811e      6002           jz 0x8122
```

Nothing in the instruction distinguishes them. This is the population the
assumption actually carries, and it is the majority of it. The assumption is
what decides these, not the evidence.

**Both banks erased (6 targets, 8 sites) — the site is misframed.** `bank0`
runtime `0x863D` scans as `ljmp 0xF566`, and `0xF566` is erased in both banks.
Reading from an anchored frame shows why:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8638; pd 5' /tmp/bank0.bin
            0x00008638      fd             mov r5, a
            0x00008639      cf             xch a, r7
            0x0000863a      e569           mov a, 0x69
        ┌─< 0x0000863c      7002           jnz 0x8640
        │   0x0000863e      f566           mov 0x66, a
```

The `02 f5 66` the scan read is the `02` displacement of a `jnz` plus a
`mov 0x66,a`. All 8 such sites were checked this way and all 8 are phantoms of
the same kind; they are the byte scan's over-count made visible, which is why
both framings are printed.

## 5. Bucket C: 140 sites, and they stay `None`

The third bucket — a common-area `lcall`/`ljmp` to `≥ 0x8000` — is genuinely
unresolvable from the bytes, because `REGIONS` gives both banks base `0x8000`.
`offset_for_runtime()` returns `None` for it and this audit does not change
that. What the audit supplies is the number nobody had: **140 sites by byte
scan, 83 of them anchored, across 102 distinct targets.**

Two readings of that population, neither of them a clearance:

- **Only 1 of the 102 targets is an address some trampoline also names**, i.e.
  a banked entry point the linker knew about. If these were real calls into
  banked code one would expect them to land on entry points; 101 of 102 do
  not.
- **Every one this file read bytes for is a data table, not a call.** The ten
  best-framed are listed in §1. `0x00378`-`0x003B4` is a `ljmp` dispatch table
  read one byte out of frame — from `0x0035C` the bytes run
  `02 12 4c | 02 12 52 | 02 12 58 | 02 12 5e …`, `ljmp` entries whose targets
  step by 6 and stay in the common area, while the scan's frame turns each
  `12 XX 02` into a phantom `lcall 0xXX02`. `0x0055D0`+ and `0x006E78`+ are
  big-endian word tables (§2), `0x0066C`+ is a table of common-area addresses,
  `0x006940`+ is a table of `FF <addr>` triples, and `0x0219C`+ is the same
  triple shape inside bank-crossing pointer data:

  ```console
  $ r2 -a 8051 -e scr.color=0 -q -c 's 0x2190; pd 4' /tmp/bank0.bin
          └─< 0x00002190      0109           ajmp 0x2009
              0x00002192      900a54         mov dptr, #0x0a54
              0x00002195      e0             movx a, @dptr
              0x00002196      f4             cpl a
  ```

  `0x219C` onward is `ff 1e 1a  ff 1e 6e  ff 1f 85  ff 1f fe …`, three-byte
  entries, and the `lcall 0xE000` at `0x021C6` scoring 24 of 24 sits inside
  them.

**What is not claimed.** 83 anchored sites exist and fewer than ten were read
byte by byte. "No direct common-to-bank `lcall`/`ljmp` was found by this
enumeration" is the statement this file stands behind; "there is none" is not,
and per [`../../docs/findings.md`](../../docs/findings.md) §4c a scan that
finds nothing never licenses the second. Anyone who needs bucket C settled
should decode the common area from a recovered function boundary set, which is
a disassembler's job and a different issue.

## 6. Verdict, in the §4c form

**Not determined by this method; here is the blind spot.** The same-bank
assumption cannot be verified from these bytes, because a same-bank and a
cross-bank direct call are byte-identical. What the enumeration establishes is
narrower and is what the docstring now says:

1. No bucket-B target has the falsifying shape (own bank erased, other bank
   live) — zero out of 1305 distinct (caller bank, target) pairs.
2. Eleven targets have the confirming shape (own bank live, other bank
   erased), covering 33 of the 3261 bucket-B sites. Eight more sites are
   phantoms (§4). The other 3220 are decided by the assumption, not by
   evidence.
3. The linker's cross-bank path in this build is the 403-entry trampoline
   block, exercised 229 times from `bank1` and 61 from `bank0`, and it is
   indirect — so BL51-generated cross-bank calls are not in bucket B at all.
   Assembly outside that discipline would not show up here.
4. Bucket C is non-empty (140 / 83) and stays `None`.

The one EC-side handoff this bears on today is `0x04A6`'s, at `bank1` runtime
`0xDFD0`, whose `lcall 0x888C` sits at `0xDFD3`
([`static-refs-audit.md`](static-refs-audit.md) §5.2). It is a bucket-B site,
and it falls in the ambiguous `other`/`other` population — both banks hold
non-erased bytes at `0x888C`, and they are different instructions:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x888c; pd 3' /tmp/bank1.bin
            0x0000888c      e9             mov a, r1
            0x0000888d      f0             movx @dptr, a
            0x0000888e      a3             inc dptr
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x888c; pd 3' /tmp/bank0.bin
            0x0000888c      3e             addc a, r6
            0x0000888d      900f5d         mov dptr, #0x0f5d
            0x00008890      e0             movx a, @dptr
```

The same-bank reading picks the bank-1 listing, which is the 16-bit store
[`pd-xdata-overlap.md`](pd-xdata-overlap.md) §2 reached by hand against a
`make_bank_image.py` bank-1 image — and the bank-0 bytes do not dereference
the DPTR the site handed over at all, so the `handoff->write` verdict would
not survive the other reading. That is one agreement with an independent hand
decode, on one site, which is what §5.2 already said it was; it is not a
validation of the other 1304 pairs.

**Blind spots, named rather than left implicit.** `ajmp`/`acall` *are* now
enumerated (§7), and they are not a fifth cross-bank risk: the opcode cannot
name an address outside the caller's own 2 KiB page. What is still uncovered
is the framing of those 3481 sites, which is worse than for the 3-byte forms
rather than better — 16 byte values open a paged instruction, so the byte
scan produces paged phantoms wherever the image holds dense data. The
PC-relative family is enumerated as well now (§8), and it carries the same
two properties one step further: it is not a cross-bank risk either — a rel8
target is within 128 bytes of the branch, so it can only leave the caller's
region from within 128 bytes of a region edge, and the 4 sites in this image
that do were read one by one — while its framing is worse again, 29 byte
values against 16 and 2. Computed targets (`jmp @a+dptr`, and the
trampoline's own DPTR-carried target) remain invisible to any byte scan,
relative, paged or absolute: three enumerated classes is not all control
flow. Instruction framing is
unsettled in both directions, as §2 shows in both. Banks 2 and 3 are taken as
unused on `find_banks.py`'s word and were not re-derived. And none of this was
run on the machine: the whole file is a statement about bytes in
`ec/firmware/GMxMGxx_11.800`, not about anything observed executing.

## 7. The 2-byte paged family — counted, and why it shrinks the question

`ajmp` is `0x01/0x21/…/0xE1` and `acall` is `0x11/0x31/…/0xF1`: the low five
bits fix the family, the high three carry target bits. The target is the
*next* instruction's address with its low 11 bits replaced by the opcode's
high 3 and the operand byte —

```
target = ((pc + 2) & 0xF800) | ((op & 0xE0) << 3) | operand
```

— so it is always inside one fixed 2 KiB page, and the caller is executing
from that same page unless the instruction straddles the page boundary.

**Why that shrinks the same-bank population instead of growing it.** Every
mapped main-EC region in `REGIONS` is a whole number of 2 KiB pages, aligned
identically in file offset and runtime base; `--self-test` checks that rather
than assuming it. A target inside the caller's page is therefore inside the
caller's region, so `offset_for_runtime()` resolves it without choosing a
bank at all, and §6's assumption is simply not consulted for these 3481
sites. This is opcode semantics plus a checked property of the region table
— **not** a result derived from this image, and **not** evidence about bucket
B, which stays exactly where §6 left it.

The one shape that would escape is an instruction in a region's last two
bytes, whose next PC is already past the end of the region. `paged_sites()`
does not read the first byte of the next region as an operand, and the
image-wide self-test confirms **0 of 3481** sites resolve outside their
caller's region. Both are statements about this image; a different dump gets
them re-checked, not inherited.

**The counts, and the framing caveat is bigger here.** 3481 sites by byte
scan, 1667 anchored — 48%, against 89% for the absolute forms in §1. That is
the expected direction: 16 of 256 byte values open a paged instruction
against 2 of 256, so a byte scan over-counts harder, not less. Read the pair,
and do not read the upper bound as a site count.

**Page arithmetic, pinned against two hand decodes.** The first is the `ajmp`
already transcribed in §5 while reading bucket C; the second is this image's
only paged site whose next PC crosses a page boundary, so its target is in
the *following* page — the off-by-one the arithmetic invites:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x2190; pd 1' /tmp/bank0.bin
        └─< 0x00002190      0109           ajmp 0x2009
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xe7fd; pd 3' /tmp/bank1.bin
        └─< 0x0000e7fd      015b           ajmp 0xe05b
        ┌─< 0x0000e7ff      0153           ajmp 0xe853
       ┌──< 0x0000e801      014a           ajmp 0xe84a
```

`0xE7FD` and `0xE7FF` are the same opcode two bytes apart and land 2 KiB
apart, because `0xE7FF`'s next PC is `0xE801`. Both sites are `--self-test`
cases; if `paged_target()` ever loses the `+ 2`, the second fails.

**The BL51 path, and what the 18 hits on it actually are.** 17 paged sites
resolve onto a bank-0 trampoline entry and 1 onto a bank-1 one; none resolves
onto a stub. That is a route the geometry allows — the trampoline block
`0x1150`-`0x1ABC` is in the common area, so a common-area paged call can
reach it from inside its own page, which a bank never can. The sites do not
look like real calls, though: the best of the 18 scores 1 of 24 anchors and
14 score 0. Two were read by hand, and both are the trampoline block's own
bytes misframed:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x15b8; pd 2' /tmp/bank0.bin
            0x000015b8      90c881         mov dptr, #0xc881
        └─< 0x000015bb      021100         ljmp 0x1100
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x110d; pd 3' /tmp/bank0.bin
            0x0000110d      c290           clr p1.0
            0x0000110f      c291           clr p1.1
            0x00001111      c292           clr p1.2
```

The scan's `ajmp` at `0x15BA` is the `0x81` low byte of a trampoline's
`mov dptr,#0xc881`; its `acall` at `0x1110` is the `0x91` of a `clr p1.1`
inside the bank-0 stub. The other 16 were **not** read one by one, so "these
18 are phantoms" is not the claim — "two of them are, and the anchor scores
of the rest give no reason to think otherwise" is.

**What the false-negative fix found: nothing, in this image.** The mission
half of this was `register_ref_table.py --callee-depth 1` silently dropping a
handoff made by `acall`. `classify()` now treats a paged opcode as a handoff
on the same footing as `lcall`/`ljmp`, and `resolve_handoff()` passes the
handing-off instruction's runtime address down so the page can be named. Both
`--callee-depth 0` and `--callee-depth 1` come out **byte-identical to
before** across all 19 entries / 29 addresses in
[`registers.yaml`](registers.yaml): not one of those sites' decoded windows
contains a paged instruction at all in this image, so no committed
transcript in [`static-refs-audit.md`](static-refs-audit.md),
[`lightbar-bat-flow.md`](lightbar-bat-flow.md),
[`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) or [`../README.md`](../README.md)
moves. Per [`../../docs/findings.md`](../../docs/findings.md) §4c that is "not
found by this method", not "there are none": the false-negative shape was
real, the tool no longer has it, and this image happens not to exhibit it.
Nothing here is evidence about behaviour, so no `status:` in
[`registers.yaml`](registers.yaml) moves either.

## 8. The PC-relative family — the last statically-resolvable class

`sjmp` (`0x80`), `jc`/`jnc`/`jz`/`jnz` (`0x40`/`0x50`/`0x60`/`0x70`),
`jbc`/`jb`/`jnb` (`0x10`/`0x20`/`0x30`), `cjne` (`0xB4`/`0xB5` and
`0xB6`-`0xBF`) and `djnz` (`0xD5`, `0xD8`-`0xDF`) all end in a signed 8-bit
displacement added to the address of the *next* instruction:

```
target = (pc + OPCODE_LEN[op] + signed(disp)) & 0xFFFF
```

`disasm8051.relative_target()` is that one line, and `mnemonic()`'s printed
branch targets now go through it, so the listing and the enumeration cannot
drift apart.

**Where the displacement byte is, and why it is the off-by-one to pin.** The
2-byte forms (`sjmp`, the four `j*`, `djnz Rn`) put it second; the 3-byte ones
(`jb`/`jnb`/`jbc`, every `cjne`, `djnz direct`) put a bit or operand byte in
between and the displacement *last*. Taking `d[i + 1]` for all of them is the
mistake the opcode map invites, and it is silent — it yields a plausible
in-region address, not an error. Four hand decodes from `r2 -a 8051` pin it,
two of them backward branches, which neither
[`charge-profile-flow.md`](charge-profile-flow.md) window contains:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb136; pd 2' /tmp/bank0.bin
            0x0000b136      e0             movx a, @dptr
        ┌─< 0x0000b137      20e007         jb acc.0, 0xb141
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb2ee; pd 1' /tmp/bank0.bin
       ┌──< 0x0000b2ee      806e           sjmp 0xb35e
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf1ae; pd 3' /tmp/bank0.bin
        ╎   0x0000f1ae      ee             mov a, r6
        ╎   0x0000f1af      f0             movx @dptr, a
        └─< 0x0000f1b0      dfe6           djnz r7, 0xf198
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xfe20; pd 3' /tmp/bank0.bin
       ╎╎   0x0000fe20      901500         mov dptr, #0x1500
       ╎╎   0x0000fe23      e0             movx a, @dptr
       └──< 0x0000fe24      30e1e8         jnb acc.1, 0xfe0f
```

`0xFE24` is the load-bearing one: its second byte is `0xE1`, the bit address
`acc.1`, and its displacement is the third, `0xE8`. Reading the second would
give `0xFE08` instead of `0xFE0F`, and `0xB137`'s would give `0xB11A` instead
of `0xB141`. `disasm8051.py --self-test` checks all four sites through
`relative_target()` and `audit_call_targets.py --self-test` re-checks them
through its own site walk, so the two cannot agree on a wrong byte index; the
audit's self-test also asserts those two *wrong* answers stay wrong, which is
the half a passing case alone would not catch.

**The geometric bound, and why it is not §7's.** A rel8 target lies within
[-128, +127] of the next PC, so a relative branch can only leave the caller's
region from within 128 bytes of a region edge — opcode arithmetic plus the
`REGIONS` table, not a result read out of this image. That is weaker than §7's
claim: a paged target *cannot* leave its region, a relative one *can*, it just
needs to start near an edge. So the escape count is a checked property of this
image rather than an opcode fact, and `--self-test` walks all 9076 sites,
counts the escapes and asserts of each only what the arithmetic guarantees
(that it sits within 128 bytes of an edge). A different dump gets this
re-checked, not inherited.

**The four escapes, all read.** 4 of 9076 sites resolve outside the caller's
region, all in `bank0` within 96 bytes of its start, all branching back into
the common area — which is a legal place to branch to, since the common area
is mapped in every bank image. All four were read byte by byte, and all four
are byte-scan phantoms:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8020; pd 8' /tmp/bank0.bin
            0x00008020      901902         mov dptr, #0x1902
            0x00008023      7415           mov a, #0x15
            0x00008025      f0             movx @dptr, a
            0x00008026      901905         mov dptr, #0x1905
            0x00008029      7480           mov a, #0x80
            0x0000802b      12bcb6         lcall 0xbcb6
            0x0000802e      a3             inc dptr
            0x0000802f      f0             movx @dptr, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8058; pd 3' /tmp/bank0.bin
        ┌─< 0x00008058      20e703         jb acc.7, 0x805e
       ┌──< 0x0000805b      028274         ljmp 0x8274
       │└─> 0x0000805e      12b9df         lcall 0xb9df
```

`0x0802C`'s `0xBC` is the middle byte of `lcall 0xbcb6`; `0x0805F`'s `0xB9` and
`0x08060`'s `0xDF` are the two operand bytes of `lcall 0xb9df`, which is why
they produce the same target `0x7FF2` from two different opcodes. The fourth,
`0x0803B`, scores 24 of 24 anchors and still reads as data rather than a
branch — the §2 shape again. From `0x08038` the bytes run
`80 54 | 00 | 80 94 | 01 80 d7 | 02 81 1a | 03 81 …`: past the `sjmp 0x808e`
at `0x8038` they fall into `index, big-endian address` triples, indices `00`,
`01`, `02`, `03` and addresses stepping by `0x43` — `0x8094`, `0x80D7`,
`0x811A` — and the scan reads the `80 94` of the first entry as
`sjmp 0x7FD1`. Its target is inside a run of `0xFF`, which is the tool's own
scoring aid pointing at the same conclusion. That is a reading of the bytes,
not an execution trace; what it does establish is that a 24-of-24 anchor score
is not evidence of a branch, which §2 already said.

**The counts, and the framing caveat is worse again.** 9076 sites by byte scan,
6675 anchored — 74%, against 48% for the paged forms (§7) and 89% for the
absolute ones (§1). 29 of the 256 byte values open a relative branch, against
16 and 2, so the upper bound over-counts harder here than anywhere else in this
file, and **74% anchored is not a cleanliness score**: `converges_from()` says
a linear walk syncs onto the byte, and §2 shows a dense table does that too.
The per-opcode spread is the visible warning: `sjmp` scores 1170 of 1324 while
`jbc` scores 164 of 742, a fourfold difference in anchor rate between two
families of the same instruction class. Read the pair, and read it per opcode;
the upper bound is not a site count, and nothing here is a claim that any
individual site executes.

**The BL51 path.** 168 relative sites resolve onto a bank-0 trampoline entry
and 2 onto a bank-1 one; none onto a stub. The geometry allows it for the same
reason §7 gives — the trampoline block `0x1150`-`0x1ABC` is common-area, so a
common-area branch starting within 128 bytes of an entry can reach it, and a
bank never can. Exactly 1 of the 170 is anchored at all, which is a weaker
population than §7's 18 rather than a stronger one. None of the 170 was read
one by one, so "these are phantoms" is not the claim here; "one of 170 has any
frame evidence behind it" is.

**Reproducing every table in this section from the committed CSV.** Each of
them is a group-by over
[`bank-relative-branch-targets.csv`](bank-relative-branch-targets.csv), not a
number the tool asks to be trusted on:

```console
$ python3 -c '
import csv
rows = list(csv.DictReader(open("ec/annotations/bank-relative-branch-targets.csv")))
def pair(sel):
    return "%d / %d" % (len(sel), sum(1 for r in sel if int(r["frame_onto"]) > 0))
for key in ("opcode", "length", "target_class"):
    for region in ("common", "bank0", "bank1"):
        sel = [r for r in rows if r["region"] == region]
        keys = sorted({r[key] for r in sel})
        print(region, key, {k: pair([r for r in sel if r[key] == k]) for k in keys})
print("escaped", pair([r for r in rows if r["in_region"] == "no"]), "of", len(rows))
print("bank-0 trampoline", pair([r for r in rows if r["calls_trampoline"] == "0"]))
'
common opcode {'cjne': '566 / 307', 'djnz': '173 / 107', 'jb': '197 / 157', 'jbc': '423 / 65', 'jc': '200 / 160', 'jnb': '359 / 306', 'jnc': '69 / 58', 'jnz': '203 / 183', 'jz': '255 / 241', 'sjmp': '340 / 307'}
bank0 opcode {'cjne': '870 / 406', 'djnz': '290 / 115', 'jb': '212 / 150', 'jbc': '192 / 40', 'jc': '194 / 147', 'jnb': '253 / 219', 'jnc': '165 / 158', 'jnz': '291 / 270', 'jz': '431 / 421', 'sjmp': '383 / 331'}
bank1 opcode {'cjne': '570 / 462', 'djnz': '186 / 114', 'jb': '289 / 230', 'jbc': '127 / 59', 'jc': '256 / 217', 'jnb': '236 / 195', 'jnc': '161 / 151', 'jnz': '295 / 288', 'jz': '289 / 279', 'sjmp': '601 / 532'}
common length {'2': '1223 / 1048', '3': '1562 / 843'}
bank0 length {'2': '1737 / 1435', '3': '1544 / 822'}
bank1 length {'2': '1774 / 1573', '3': '1236 / 954'}
common target_class {'entry': '1391 / 995', 'erased': '1 / 0', 'other': '1393 / 896'}
bank0 target_class {'': '4 / 3', 'entry': '1829 / 1549', 'erased': '6 / 5', 'other': '1442 / 700'}
bank1 target_class {'entry': '1766 / 1578', 'other': '1244 / 949'}
escaped 4 / 3 of 9076
bank-0 trampoline 168 / 1
```

(`bank0`'s empty `target_class` is the four escapes: the column is only filled
for a target inside the caller's own region.)

**What this section is not.** It is a byte scan; it establishes edges, not
behaviour, and nothing in it was run on the machine. It says nothing about the
same-bank assumption of §6, which stays exactly where §6 left it — a relative
target needs no bank chosen for it, so this family simply is not in that
population either. No `status:` in [`registers.yaml`](registers.yaml) moves,
because an edge is not evidence the EC acts on anything. And this is the
enumeration half only: `classify()` in `../tools/register_ref_table.py` still
stops at a relative opcode rather than following it, so a `--callee-depth 1`
handoff made by a conditional branch is still invisible to it. That is issue
#40, and it stays open.
