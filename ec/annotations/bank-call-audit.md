# Direct `lcall`/`ljmp` targets in the main EC image — is the same-bank assumption safe?

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

$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test
  ok   4 BL51 stub sites at 0x1100, 0x1114, 0x1128, 0x113C selecting banks 0-3 (got 0x1100=bank0, 0x1114=bank1, 0x1128=bank2, 0x113C=bank3)
  ok   the `C0 08 74` prologue occurs 4 times in the main EC image (got 4)
  ok   and 0 times in the PD image (got 0)
  ok   offset_for_runtime()/runtime_addr() round-trip for every mapped region
  ok   a common-area call to 0x8000 stays unresolvable (bucket C returns None)

self-test passed
```

[`bank-call-targets.csv`](bank-call-targets.csv) is `--csv` on the same image —
one row per call site, 5998 of them — so every table above is a group-by over
committed data rather than a number to be taken on trust.

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

**Blind spots, named rather than left implicit.** `ajmp`/`acall` are not
enumerated — `trace_xdata_refs.call_target()` deliberately does not recognise
them and this tool inherits that, so an `acall` crossing a bank would be
invisible here. Computed targets (`jmp @a+dptr`, and the trampoline's own
DPTR-carried target) are invisible to any byte scan. Instruction framing is
unsettled in both directions, as §2 shows in both. Banks 2 and 3 are taken as
unused on `find_banks.py`'s word and were not re-derived. And none of this was
run on the machine: the whole file is a statement about bytes in
`ec/firmware/GMxMGxx_11.800`, not about anything observed executing.
