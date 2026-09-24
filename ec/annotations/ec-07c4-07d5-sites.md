# `0x07C4`-`0x07D5` — the 15 main-EC reference sites, and what they are set from

`docs/findings.md` §4o reads `0x07C4`-`0x07D7` as a GPU dynamic-boost
control block, from the DSDT alone: `T1WR`'s `Arg0 == 0x73` branch and its
`_Q84` twin test `DBEN` and, if it is set, publish `CPUA * 8` and
`DBAP * 8` to `NPCF.ATPP` and `NPCF.AMAT` for the NVIDIA platform
controller. §4o closed with a census as the next step, and named the
sharper one: the EC firmware's own references to four of those bytes.
Those are what this file walks, the way
[`manual-fan-ctrl-0751.md`](manual-fan-ctrl-0751.md) walked `0x0751`.

**The short answer, and its limits.** Fifteen direct `MOV DPTR` sites in the
main EC image, against **zero** for `0x07D0` and `0x07D1` — the two bytes
§4o re-graded, one of which `ec-0x07d0-sites.md` enumerated and the other
of which `static-refs-audit.md` §6 recorded as un-walked. The EC image does
touch this block, and in a way that lines up with the ASL: the routine
entered at `0x83FF` copies `0x09EA`/`0x09EB` into `CPUA`/`DBAP` and then
sets bit 3 of `0x07C4` to follow bit 4 of the same byte, and a second
routine at `0x94C0` sets or clears bit 4 from a bit of `CTGP_DB_CTRL`
(`0x0743`). `0x07D3`'s `GFID` field is written outright, with the values 3,
4, 5 and 7.

**None of that is a live test.** The five `0x07C4` sites, the two `0x07D4`
and four `0x07D5` sites and the four `0x07D3` sites are statements about
an 8-instruction linear window around each site, plus the routine each one
sits in. A window that stops at a branch is *this method stopping*, never
"this site does not access the byte" — §5 gives the three that do, and
what each turns out to reach. Indirect `movx @Ri` and a `DPH` built at run
time are invisible to the scan, and §6 is the hunt for the second of those
on this page: it finds nothing, and a null there is the §4c error in
miniature, not an answer. All four entries stay `present-untested` in
`registers.yaml`; `0x0751` stayed there even after a live run, because the
run did not isolate the mechanism, and a static walk is further from that
than a live run is.

**Who wrote the `0x07C4` byte on this machine is still not established.**
The 2026-09-23 capture has two writes to it (§8), 0.44 s apart at an AC
plug-in. Nothing in the image labels a routine and no committed input
writes the byte at all, so the timing is a reason to keep looking and not
an attribution.

## 1. Reproducing the map

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x07C4 0x07D3 0x07D4 0x07D5 --counts-only
0x07C4: 8 direct MOV DPTR site(s)  bank0=5  pd-image=3
0x07D3: 11 direct MOV DPTR site(s)  bank0=4  pd-image=7
0x07D4: 70 direct MOV DPTR site(s)  bank0=2  pd-image=68
0x07D5: 28 direct MOV DPTR site(s)  bank0=4  pd-image=24

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x07C4 0x07D3 0x07D4 0x07D5 --csv \
      > ec/annotations/ec-07c4-07d5-sites.csv
$ tail -n +2 ec/annotations/ec-07c4-07d5-sites.csv | wc -l
117

$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-07c4-07d5-sites.csv')))
print(collections.Counter(r['region'] for r in rows))"
Counter({'pd-image': 102, 'bank0': 15})

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
73 entries / 105 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

That is the reconciliation this file rests on, and a reader can re-run all
four lines: 117 = 8+11+70+28 enumerated rows; `bank0` 15 = 5+4+2+4;
`pd-image` 102 = 3+7+68+24. The enumerated rows are the same sites
`registers.yaml` records as `static_refs`/`static_refs_main_ec`/
`static_refs_pd_image`, so the table cannot silently disagree with the
numbers the rest of the repo quotes.

The 102 `pd-image` rows are the `ITE8850-PD` program's own variables, at
its own `0x07C4` — a different 8051 program with a different XDATA map,
which `ec-0x07d0-sites.md` §1 sets out at length. The `region` column is
what separates the 15 from the 102, and nothing below is about the 102.

Two further tools were run over the same set and their result is narrated
rather than pasted. `register_ref_table.py --callee-depth 1` adds nothing
for these four addresses: the `callee`/`callee_window` columns are empty
for all 15, because no site hands DPTR to a subroutine. The three `none`
cells in `0x07C4`'s and `0x07D3`'s rows are §5's, not the tool's.

Framing, in the `frame_onto`/`frame_over` sense of
[`bank-call-audit.md`](bank-call-audit.md) §8: **14 of the 15 have all 24
preceding anchors converging onto them**, and `0x8483` has 22 of 24 with 2
stepping over it — still the majority verdict, so the `frame_onto` column
is not load-bearing for any claim below, but it is named rather than
smoothed over. The listings the argument rests on (§2, §3, §4, §5) were
re-run in `r2 -a 8051`; the commands are in §7.

## 2. The 15 sites

From `ec-07c4-07d5-sites.csv`, committed next to this file. `access` and
`what the window does` are that file's columns read by hand, with the
windows expanded where the 8-instruction walk stopped at a branch (§5).

| addr | runtime | access | what the window does |
| --- | --- | --- | --- |
| `0x07C4` | `0x843D` | read | `movx a,@dptr ; jnb acc.4` — bit 4 into R7, §3 |
| `0x07C4` | `0x844A` | read | `movx a,@dptr ; jnb acc.3` — bit 3 into R6, §3 |
| `0x07C4` | `0x8483` | read+write | `orl a,#0x08` / (at `0x8490`) `anl a,#0xf7` — bit 3 follows bit 4, §3 |
| `0x07C4` | `0x8490` | read+write | the same block's other arm, `anl a,#0xf7` then `movx @dptr,a`, §3 |
| `0x07C4` | `0x94C1` | read+write | `jz +0x05`, then `orl a,#0x10` / `anl a,#0xef` — bit 4 from R7, §4 |
| `0x07D3` | `0x94D5` | read | `anl a,#0xf0 ; xrl a,#0x30 ; jnz +0x26` — "is GFID 3?" |
| `0x07D3` | `0xBA46` | read+write | `anl a,#0xf0 ; movx @dptr,a ; movx a,@dptr ; ret` — clear the low nibble, return the byte, §4 |
| `0x07D3` | `0xDA2D` | write | `jnb acc.4` on `0x166A`, then `0x30` or `0x40` — GFID 3 or 4, §4 |
| `0x07D3` | `0xDA41` | write | the same shape, `0x50` or `0x70` — GFID 5 or 7, §4 |
| `0x07D4` | `0x8460` | read | `xrl a,r7 ; jnz +0x0c` — compare against `0x09EA`, §3 |
| `0x07D4` | `0x8477` | write | `movx @dptr,a` — the copy, §3 |
| `0x07D5` | `0x846C` | read | `xrl a,r7 ; jz +0x29` — compare against `0x09EB`, §3 |
| `0x07D5` | `0x847F` | write | `movx @dptr,a` — the copy, §3 |
| `0x07D5` | `0xAD99` | write | stores the `0xFF` staged for `0x0788`, then `ljmp 0x83D6`, §4 |
| `0x07D5` | `0xCC78` | write | the same three instructions, in a different reset-shaped run, §4 |

**Nine of the fifteen read, six write, and four are read-modify-writes**
once the three stopped windows are expanded — 6/4/2 with three
unresolved before that, the split `trace_xdata_refs.py` prints. That is a
count of instructions, not of decisions, and the same distinction the 0751
file draws: a `write` class is an instruction storing to the address, not
evidence the EC acts on it. §5 gives the expansion and the arithmetic.

The PD-image share is not uniform either, and the asymmetry is worth
noting because it is what makes the block a *main-EC* one: `0x07C4` is
5/8 in the EC image, while `0x07D4` is 2/70 and its 68 `pd-image` sites
are the loudest. This is the opposite of `0x07D0`/`0x07D1`, which are
100% `pd-image`.

## 3. `0x83FF`: the routine that holds four `0x07C4` sites and all four `0x07D4`/`0x07D5` ones

Eight of the fifteen sites are in one routine entered at `0x83FF`, already
named `sync_0788_and_07d4_from_09e9` in
[`ghidra-functions.csv`](ghidra-functions.csv) and exported as
`../decompiled/bank0/83FF.c`. The `0x07C4` block is the tail of it:

```
0x8436  900743   mov  dptr,#0x0743     ; CTGP_DB_CTRL
0x8439  e0       movx a,@dptr
0x843a  30e05f   jnb  acc.0,0x849c     ; bit 0 clear -> skip the whole block
0x843d  9007c4   mov  dptr,#0x07c4
0x8440  e0       movx a,@dptr
0x8441  30e404   jnb  acc.4,0x8448
0x8444  7f01     mov  r7,#0x01          ; bit 4 set
0x8446  8002     sjmp 0x844a
0x8448  7f00     mov  r7,#0x00          ; bit 4 clear
0x844a  9007c4   mov  dptr,#0x07c4
0x844d  e0       movx a,@dptr
0x844e  30e304   jnb  acc.3,0x8455
0x8451  7e01     mov  r6,#0x01          ; bit 3 set
0x8453  8002     sjmp 0x8457
0x8455  7e00     mov  r6,#0x00          ; bit 3 clear
0x8457  ee       mov  a,r6
0x8458  6f       xrl  a,r7
0x8459  7018     jnz  0x8473            ; bit 3 already follows bit 4 -> done
0x845b  9009ea   mov  dptr,#0x09ea
0x845e  e0       movx a,@dptr
0x845f  ff       mov  r7,a
0x8460  9007d4   mov  dptr,#0x07d4
0x8463  e0       movx a,@dptr
0x8464  6f       xrl  a,r7
0x8465  700c     jnz  0x8473            ; CPUA already matches -> done
0x8467  9009eb   mov  dptr,#0x09eb
0x846a  e0       movx a,@dptr
0x846b  ff       mov  r7,a
0x846c  9007d5   mov  dptr,#0x07d5
0x846f  e0       movx a,@dptr
0x8470  6f       xrl  a,r7
0x8471  6029     jz   0x849c            ; DBAP already matches -> done
0x8473  9009ea   mov  dptr,#0x09ea
0x8476  e0       movx a,@dptr
0x8477  9007d4   mov  dptr,#0x07d4
0x847a  f0       movx @dptr,a           ; CPUA = [0x09EA]
0x847b  9009eb   mov  dptr,#0x09eb
0x847e  e0       movx a,@dptr
0x847f  9007d5   mov  dptr,#0x07d5
0x8482  f0       movx @dptr,a           ; DBAP = [0x09EB]
0x8483  9007c4   mov  dptr,#0x07c4
0x8486  e0       movx a,@dptr
0x8487  30e406   jnb  acc.4,0x8490
0x848a  e0       movx a,@dptr
0x848b  4408     orl  a,#0x08           ; bit 4 set   -> set bit 3
0x848d  f0       movx @dptr,a
0x848e  8007     sjmp 0x8497
0x8490  9007c4   mov  dptr,#0x07c4
0x8493  e0       movx a,@dptr
0x8494  54f7     anl  a,#0xf7           ; bit 4 clear -> clear bit 3
0x8496  f0       movx @dptr,a
0x8497  7d84     mov  r5,#0x84
0x8499  12163c   lcall 0x163c
0x849c  22       ret
```

That answers "what are `0x07D4`/`0x07D5` set from" as narrowly as the
evidence allows: **from `0x09EA` and `0x09EB`**, and only when they differ
from what is already there, and only when `CTGP_DB_CTRL` (`0x0743`) bit 0
is set. Neither `0x09EA` nor `0x09EB` has an entry in `registers.yaml`,
and this file does not give them one — the same gap `0x83FF`'s own
annotation row records. What produces `0x09EA`/`0x09EB` is the open
question this raises.

**The bit-3 logic is a real find, and the identification is an inference.**
`0x843D`-`0x8496` is a read-modify-write of `0x07C4` that makes bit 3
equal bit 4. The DSDT field list
(`evidence/acpi/dsdt.dsl:52238-52242`) names bit 3 `DBEN` and bit 5
`DBST`, and both ASL sites gate on `If ((DBEN == One))`; §4o had recorded
`DBEN` as bit 0 and is corrected in place there. So the EC firmware
contains a bit-3 writer for the byte the ASL gates on. That this is *the
same* gate — that `DBEN` is the vendor's name for what this bit does — is
an inference from the bytes, not a decode of what the routine is for. The
exact opcodes are beside it above; what the routine is *for* is not
recoverable from them.

**Its one direct caller is in the unresolved stub run.** `0x83FF` is
called from exactly one place, `0x8551`, and that address sits in the run
of consecutive three-byte `lcall`/`ljmp` entries starting at `0x851B` that
[`bank-call-audit.md`](bank-call-audit.md) has not resolved — the same run
`manual-fan-ctrl-0751.md` §4 hit and handled by deferring. So whether
`0x83FF` runs on a mode switch, a poll or a boot chain is **not**
established here, and the timing of the two `0x07C4` writes in §8 cannot
be lined up against it.

## 4. The other two `0x07C4` writers' neighbours, and `0x07D3`/`0x07D5`'s other writers

### 4.1 `0x94C0` — bit 4 of `0x07C4` from a bit of `CTGP_DB_CTRL`

```
0x94c0  ef       mov  a,r7
0x94c1  9007c4   mov  dptr,#0x07c4
0x94c4  6005     jz   0x94cb            ; R7 == 0 -> clear bit 4
0x94c6  e0       movx a,@dptr
0x94c7  4410     orl  a,#0x10
0x94c9  f0       movx @dptr,a
0x94ca  22       ret
0x94cb  e0       movx a,@dptr
0x94cc  54ef     anl  a,#0xef
0x94ce  f0       movx @dptr,a
0x94cf  22       ret
```

This is the `0x94C1` site the 8-instruction walk stopped on: the `jz`
tests `a`, which `0x94C0` loaded from R7, so the access is at `0x94C6` and
`0x94CB` and the window is where the method gave up, not where the byte
is left alone. The routine is already named `set_07c4_bit4_from_r7` in
[`ghidra-functions.csv`](ghidra-functions.csv) and exported as
`../decompiled/bank0/94C0.c`.

Where R7 comes from is one call away, and it is the useful half:

```
0x9704  900743   mov  dptr,#0x0743     ; CTGP_DB_CTRL
0x9707  e0       movx a,@dptr
0x9708  30e104   jnb  acc.1,0x970f
0x970b  7f01     mov  r7,#0x01
0x970d  8002     sjmp 0x9711
0x970f  7f00     mov  r7,#0x00
0x9711  1294c0   lcall 0x94c0
```

`0x94C0` has exactly one direct caller in the image, and it passes bit 1
of `0x0743`. So the EC sets or clears bit 4 of `0x07C4` from bit 1 of
`CTGP_DB_CTRL` — the same `0x0743` byte whose bit 0 gates §3's block. What
bit 1 of `CTGP_DB_CTRL` means is not established here.

So `0x07C4` has **two** bit-level writers this method finds, and they
disagree about the bit: §3's `0x83FF` block makes bit 3 follow bit 4, and
`0x94C0` sets bit 4 from elsewhere. They are not in conflict — `0x83FF`'s
gate is `0x0743` bit 0 and `0x94C0`'s source is `0x0743` bit 1 — but
nothing here says which one runs when.

### 4.2 `0x07D3`'s four sites: `GFID` gets 3, 4, 5 and 7

Two of the four are in the routine entered at `0xD9FE`, reached by one
`lcall` from `0xD905` in bank0. They write the byte outright:

```
0xda29  90166a   mov  dptr,#0x166a
0xda2c  e0       movx a,@dptr
0xda2d  9007d3   mov  dptr,#0x07d3
0xda30  30e405   jnb  acc.4,0xda38
0xda33  7430     mov  a,#0x30           ; GFID = 3
0xda35  f0       movx @dptr,a
0xda36  8017     sjmp 0xda4f
0xda38  7440     mov  a,#0x40           ; GFID = 4
0xda3a  f0       movx @dptr,a
0xda3b  8012     sjmp 0xda4f
0xda3d  90166a   mov  dptr,#0x166a
0xda40  e0       movx a,@dptr
0xda41  9007d3   mov  dptr,#0x07d3
0xda44  30e405   jnb  acc.4,0xda4c
0xda47  7450     mov  a,#0x50           ; GFID = 5
0xda49  f0       movx @dptr,a
0xda4a  8003     sjmp 0xda4f
0xda4c  7470     mov  a,#0x70           ; GFID = 7
0xda4e  f0       movx @dptr,a
```

`0x30`/`0x40`/`0x50`/`0x70` are `GFID` = 3, 4, 5 and 7 in bits 4-6 — the
field the DSDT field list names (`dsdt.dsl:52254-52256`). So the EC
firmware writes that field with four distinct values, and that is a
statement about the instruction stream, not about what any of them means
to the GPU. The branch is on bit 4 of the byte at `0x166A`, which has no
entry in `registers.yaml` and is not given one here.

The other two sites touch only the low nibble, so they do not contradict
the above:

- `0xBA46` is the routine entered at `0xBA46`, named
  `clear_low_nibble_07d3` in [`ghidra-functions.csv`](ghidra-functions.csv)
  and exported as `../decompiled/bank0/BA46.c`: it reads the byte, ANDs
  with `0xF0`, writes it back, re-reads it and returns. It has ten direct
  callers in bank0, and all ten sit in one run at `0x91AF`-`0x91FA` of the
  same six-byte shape — `lcall 0xBA46 ; orl a,#N ; movx @dptr,a ; sjmp
  0x91FB` — for `N` = `0x00` through `0x09`. So bits 0-3 of `0x07D3` are a
  **ten-value selector**: the run clears them and then sets the one the
  entry point chooses, and all ten join at `0x91FB`, which calls `0xBA36`
  and compares that against `0x03`. What selects the entry point is not
  established here.
- `0x94D5` is inside the routine entered at `0x94D0`, named
  `copy_code_table_into_0730_07a7` in
  [`ghidra-functions.csv`](ghidra-functions.csv): it reads the byte, masks
  the high nibble, XORs `0x30` and branches — that is, it tests for
  `GFID == 3` before choosing between two seed pairs. It is a **read**.

### 4.3 `0x07D5`'s two reset-shaped writers

`0xAD99` and `0xCC78` store the immediate `0xFF`, and both do it in a run
that also writes `0xFF` to `0x0788` and clears `0x07C5` bit 5:

```
0xad93  900788   mov  dptr,#0x0788
0xad96  74ff     mov  a,#0xff
0xad98  f0       movx @dptr,a
0xad99  9007d5   mov  dptr,#0x07d5
0xad9c  f0       movx @dptr,a
0xad9d  7fe1     mov  r7,#0xe1
0xad9f  0283d6   ljmp 0x83d6
```

`0xAD99` is inside the decompiled function `reset_xdata_flags_and_07d5_to_ff`
(`../decompiled/bank0/ACB4.c`), a 238-byte whole-machine reset that ends
in that tail jump — its decompile clears a long list of XDATA bits,
zeroes 96 bytes at `0x0F00`, clears `CPU_TCC_OFFSET` (`0x0786`) and
`0x0787`, and sets `0x0788` and `0x07D5` to `0xFF`. `0xCC78` is the same
three instructions at a different address, in a run that then sets bits 7,
6 and 3 of `0x200D` and calls `0x2896`.

**Both runs' entry points are now established.** `0xAD99` sits inside the
exported `reset_xdata_flags_and_07d5_to_ff` at `0xACB4`. `0xCC78` sits
inside `init_06e6_1_clear_0743_07c5_and_07d5_ff` at `bank0:0xCC64`, entered
through the common-area bank-select trampoline at `0x17DA`, which loads DPTR
with `0xCC64` and jumps to the bank-0 select stub. The far boundary is
sharp rather than a guess: `0xCCCE` is a `ret`, `0xCCCF` is a separate
thunked entry in its own right, and the preceding function tail-jumps at
`0xCC61`, so nothing falls through into `0xCC64`.

**The earlier "two overlapping `ljmp`s" reading of `0xCC60`/`0xCC61` was
wrong, and it is wrong in the §4c shape.** The bytes there are `0xCC5F: c2
02` (`clr 0x02`) followed by `0xCC61: 02 39 7d` (`ljmp 0x397D`) — the tail
of the annotated `0xCC51`. Read one byte early, `0xCC60 02 39 7d` looks
like a second `ljmp`: an operand byte of a known instruction reported as a
call target by a byte scan. `0xCC64` has no *direct* `lcall` or `ljmp` to it
anywhere in the EC image, which is exactly why the entry had to be settled
by a different method rather than by scanning harder for calls. So:
`0xFF` is what these two sites store, and "a default" is a reading of their
surroundings, not a decode.

Both halves of the entry claim reproduce from the committed image — the
positive (one DPTR-load trampoline) and the negative (no direct call) —
with the two tools already in `ec/tools/`:

```console
$ python3 -c "
data = open('ec/firmware/GMxMGxx_11.800','rb').read()[:0x20000]
pat = bytes([0x90, 0xCC, 0x64])          # MOV DPTR,#0xCC64, high byte first
i = data.find(pat)
while i != -1:
    print('0x%04X file-offset -> %s' % (i, data[i+3:i+6].hex(' ')))
    i = data.find(pat, i+1)
"
0x17DA file-offset -> 02 11 00

$ python3 -c "
data = open('ec/firmware/GMxMGxx_11.800','rb').read()[:0x20000]
hits = [i for i in range(len(data)-2)
        if data[i] in (0x12, 0x02) and (data[i+1] << 8 | data[i+2]) == 0xCC64]
print('direct lcall/ljmp to 0xCC64:', len(hits), hits)
"
direct lcall/ljmp to 0xCC64: 0 []
```

The one DPTR-load site is at file offset `0x17DA`, which is the common area
— it is the trampoline itself, and the three bytes after it (`02 11 00`,
`ljmp 0x1100`) are the bank-0 select stub. `ec/annotations/bank-call-audit.md`
§3 counts 403 such trampolines in the common area `0x1150`-`0x1ABC`; three
siblings in the same family name entries in this very block
(`0x1852 → 0xCCFC`, `0x1864 → 0xCCE5`, `0x1882 → 0xCCCF`).

### 4.4 The `0x07C4` fifth site is the one that needed hand-decoding

`0x94C1` is the one row of the five whose 8-instruction window ends
immediately: the CSV's `access` for it is `no movx found in the decoded
window` and its `window` is `jz +0x05`, with the `movx` a byte past the
branch. §4.1 resolves it. That is what "this method stopped" looks like in
practice — see `static-refs-audit.md` §5.3 for the same three words on
three other addresses.

## 5. The three `none` rows, and the `access` column's weakest cell

`trace_xdata_refs.py` classes a site by the instructions in the 8 that
follow the `mov dptr`, and a window that ends on a branch has no `movx` in
it yet. `static-refs-audit.md` §5.3 wrote down what a `none` cell is —
"this method stopped", and reading it as "this site does not access the
register" would be the `docs/findings.md` §4c error in miniature. Three of
the fifteen are `none`, and all three resolve when the window is expanded:

| site | the walk stopped at | what is there |
| --- | --- | --- |
| `0x94C1` | `jz +0x05` on R7 | `orl a,#0x10` / `anl a,#0xef` — a read-modify-write of bit 4, §4.1 |
| `0xDA2D` | `jnb acc.4` on `[0x166A]` | `mov a,#0x30` / `mov a,#0x40` then `movx @dptr,a` — a write, §4.2 |
| `0xDA41` | `jnb acc.4` on `[0x166A]` | `mov a,#0x50` / `mov a,#0x70` then `movx @dptr,a` — a write, §4.2 |

So the corrected split for the 15 is **5 read, 6 write, 4
read-modify-write**: the five reads are `0x843D`, `0x844A`, `0x8460`,
`0x846C` and `0x94D5`; the six writes are `0x8477`, `0x847F`, `0xDA2D`,
`0xDA41`, `0xAD99` and `0xCC78`; the four read-modify-writes are `0x8483`,
`0x8490`, `0x94C1` and `0xBA46`. `register_ref_table.py` still reports
`0x07C4` as 3 read / 1 r+w / 3 handoff-unresolved / 1 none across all 8
sites and `0x07D3` as 4 read / 1 write / 1 r+w / 3 handoff-unresolved / 2
none across all 11, and those are left as they are: the tool's depth-1
callee resolution resolves none of them — every one of the 15 has an empty
`callee` column, §1 — so the `handoff` rows are all `pd-image` sites and
the per-site table above is the reading of the 15.

## 6. A computed `DPH` onto this page: null, and what a null is worth

`manual-fan-ctrl-0751.md` §6 found the reason `0x0F00`'s zero direct-site
count is wrong: the EC reaches that page by building `DPH` at run time with
`addc a,#0x0f ; mov DPH,a` (`34 0F F5 83`), which no `MOV DPTR` scan sees.
The same construction aimed at the `0x07C4` page is `34 07 F5 83`:

```console
$ python3 - <<'EOF'
from pathlib import Path
ec = Path('ec/firmware/GMxMGxx_11.800').read_bytes()[:0x20000]
for page in (0x07, 0x0f):
    pat = bytes([0x34, page, 0xf5, 0x83])
    hits = [i for i in range(len(ec) - 3) if ec[i:i+4] == pat]
    print(f"addc a,#0x{page:02x} ; mov DPH,a -> {len(hits)}: "
          + ", ".join(f"0x{i:04X}" for i in hits))
EOF
addc a,#0x07 ; mov DPH,a -> 0:
addc a,#0x0f ; mov DPH,a -> 8: 0x8AC6, 0x8AD8, 0x8AF3, 0x8B0C, 0xBCE3, 0xBDEC, 0xE86B, 0xF312
```

**The control reproduces the eight `0x0F00` sites byte for byte and the
`0x07` page is empty.** The idiom itself is common — the same four-byte
shape appears in the EC image with 20 different immediates, one of them
eight times (`0x0F`) and `0x0D` seven times — so this is a real absence of
one idiom on one page, not an absence of the idiom.

It is still a narrow negative and the reason has to be stated rather than
assumed away. The register form (`mov 0x83,...` and `mov DPH,a` from a
register) and an indirect `movx @Ri` are equally invisible to this grep;
`mov DPH,a` (`F5 83`) appears 87 times in the EC image by itself, and this
hunt only asks what *follows* it in the immediate form. So: **no path found
by this method reaches `0x07C4`-`0x07D5` through a computed `DPH`, and the
15 is a floor for that reason rather than a total.** The one `0x08` hit
(`0x8360`, `addc a,#0x08 ; mov DPH,a`) builds `0x08D0 + [0x0A56]`, a
different page.

## 7. Spot-checks against an independent disassembler

`ec/tools/disasm8051.py` is a linear decoder, not a disassembler, so every
listing this file's argument rests on was re-run in radare2 (installed by
`.github/actions/project-setup`, as `pd-xdata-overlap.md` §3 and
`manual-fan-ctrl-0751.md` §7 did):

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8436; pd 14'  /tmp/bank0.bin   # 0x07C4 bits 4 and 3 into R7/R6
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8473; pd 9'   /tmp/bank0.bin   # the 0x07D4/0x07D5 copies
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x94c0; pd 5'   /tmp/bank0.bin   # the 0x94C1 site
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9704; pd 6'   /tmp/bank0.bin   # its one caller's 0x0743 bit 1
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x94d0; pd 6'   /tmp/bank0.bin   # the 0x94D5 read
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xba46; pd 4'   /tmp/bank0.bin   # the 0xBA46 low-nibble clear
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xda29; pd 8'   /tmp/bank0.bin   # the 0xDA2D GFID write
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xad93; pd 6'   /tmp/bank0.bin   # the 0xAD99 0xFF store
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xcc72; pd 6'   /tmp/bank0.bin   # the 0xCC78 0xFF store
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xcc64; pd 4'   /tmp/bank0.bin   # 0xCC64's own head, the boundary §4.3 settles
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x17da; pd 2'    /tmp/bank0.bin   # the common-area trampoline that reaches it
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x854b; pd 5'   /tmp/bank0.bin   # 0x83FF's one caller, in the stub run
```

All matched the listings in §3, §4 and §6 instruction for instruction.
`python3 ec/tools/disasm8051.py --self-test` holds the opcode tables
against two hand-transcribed r2 windows, so the decoder underneath the site
table is itself pinned to r2:

```console
$ python3 ec/tools/disasm8051.py --self-test
self-test passed: both charge-profile-flow.md windows decode identically and all 4 relative-branch sites resolve as hand-decoded
```

## 8. The `0x07C4` observation from 2026-09-23, and its scope

`docs/findings.md` §7c carries this beside §7, the capture section, and
`registers.yaml`'s `0x07C4` entry carries the citations. Quoted here
because the walk is what it bears on:

```
2026-09-23T17:57:51.161+02:00,0x07C4,0x08,0x28
2026-09-23T17:57:51.597+02:00,0x07C4,0x28,0x38
```

Two writes, 0.44 s apart, in the same capture where `0x0743`, `0x0745`
and `0x0746` land at the AC plug-in. The first sets bits 3 and 5; the
second sets bit 4. **Unattributed.** The byte has no committed Windows
writer (`ec-callsites-summary.csv` has no `0x07C4` row and `1988` is
absent from `ECSpec.cs`, which steps from 1987 to `ADDR_AP_OEM_BYTE5 =
1989`), so the writer is the EC firmware or firmware outside the committed
inputs, and §3 and §4.1 give the two bit-level writers this method finds
without either of them being the one that ran.

The scope is exactly what the file holds: one capture, one AC plug-in and
six Fn-key mode switches, observed passively. **No register was written or
read back to establish any of this.** A re-capture across an AC plug-in on
a wider window, with a human at the machine, is the step that would move
it, and this file names it rather than writing a procedure for it — the
issue asks for the walk, not for a new test.

## 9. What is still open

- **Who wrote `0x07C4` on 2026-09-23.** §3's `0x83FF` block and §4.1's
  `0x94C0` are the two bit-level writers this method finds, and §3's
  caller is in the unresolved three-byte stub run at `0x851B`, so neither
  can be lined up against a capture timestamp. Resolving that run
  (`bank-call-audit.md`) is the way in.
- **What `0x09EA`/`0x09EB` are.** They are the source `CPUA` and `DBAP`
  are copied from, and neither has a `registers.yaml` entry. Following
  their writers is the same kind of work as this file and is not done here.
- **What `0x166A` and `0x0743` bit 1 are.** The first selects between four
  `GFID` values; the second sets `0x07C4` bit 4. Both have no entry.
- **Whether the `DBEN` identification is the right one.** §3's bit-3
  write is an inference from the bytes. A test that flips `CTGP_DB_CTRL`
  bit 0 and watches bit 3 would decide it, and that is a hardware step no
  runner can take.
- **The 102 `pd-image` sites.** A different 8051 program's variables, and
  out of scope here as `ec-0x07d0-sites.md` §1 sets out. Issue #30 owns
  discovery of the ECMG-named address list; this is the EC-firmware-side
  decode of four of them.
- **A bank0 decompile sweep for the 15 sites' own containing routines.**
  All six are now named and exported (`0x83FF`, `0x94C0`, `0x94D0`,
  `0xBA46`, `0xACB4` and `0xCC64`), and none is left undetermined: §4.3
  settles the last two, the second of them positively rather than by
  elimination. Seeding further bank0 entries, and re-exporting, is the
  whole-program work of issue #20 rather than a static walk's. Two further
  thunked entries in the same family as `0xCC64` — `0xCCCF` and `0xCCE5`,
  reached the same way from the common area — are still unannotated and
  are the nearest remaining work of this kind.
- **`0x07C5` (`WHMS`, bit 5) and `0x07C6` (`WMS0`).** Issues #106 and #101
  own them. The service writes `0x07C5` bit 4, not bit 5, and this file
  does not answer that.
- **`0x07D6` (`DBSP`) and `0x07D7` (`CGCT`).** Left to the census pass;
  this walk turned up nothing concrete about either. **Superseded 2026-09-24
  (issue #282):** [`ec-07d6-07d7-sites.md`](ec-07d6-07d7-sites.md) walks both,
  along with the companion `0x07C7`/`0x07C8`. "Nothing concrete" was right
  about this walk, which is a *main-EC* one: all 213 of their direct `MOV
  DPTR` sites are in the ITE8850-PD image and none is in the EC firmware. The
  concrete part is on the other side of the boundary — `0x07D7` has a decoded
  ASL writer (`T1WR`'s `Arg0 == 0x1176`, `dsdt.dsl:50730-50733`) and `0x07D6`
  has no ASL site at all, which is why all four are graded
  `unknown-not-absent` rather than `present-untested`.
