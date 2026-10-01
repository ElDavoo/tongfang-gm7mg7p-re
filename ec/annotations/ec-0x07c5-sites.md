# `0x07C5` — the 10 reference sites, enumerated

`0x07C5` is `WHMS` in the DSDT's ECMG field list (`evidence/acpi/dsdt.dsl:52243-52245`:
`Offset (0x7C5)`, five unnamed bits, then `WHMS, 1`, so bit 5) and it is carried
in `ec/annotations/registers.yaml` as `WHMS`, bit 5, `present-untested`. The
four-byte block it sits in is the one `docs/findings.md` §4o reads as a GPU
dynamic-boost control, and this file is the EC-side walk of its one member that
[`ec-07c4-07d5-sites.md`](ec-07c4-07d5-sites.md) §9 handed to #106 and #101
rather than doing: 10 direct `MOV DPTR` references in the main EC image, where
each one is, what its bits do, and what the ten do not settle.

**Read the headline before the tables.** All ten sites are in the main EC
firmware and **none** is in the separate `ITE8850-PD` image — the opposite of
`0x07D0`/`0x07D1`, whose sites are all `pd-image`
([`ec-0x07d0-sites.md`](ec-0x07d0-sites.md),
[`ec-0x07d1-sites.md`](ec-0x07d1-sites.md)). So this is a main-EC walk and the
`region` column is uniform rather than a warning; the lower bound §7 records
still applies to it in full. Six of the ten read the byte and four
read-modify-write it; **no site writes it outright**, and nothing here sets
`WHMS`.

**The four masks clear bits 7, 5, 5 and 7.** Two of them — `0xAD8C` and
`0xCC6B`, both `anl a,#0xdf` — clear bit 5, which is the bit the ASL calls
`WHMS`, in two separately named init routines (§3.1). That is the piece
`ec-07c4-07d5-sites.md` §9 records as unanswered, and it is *a fact about the
instruction stream, not a claim that the EC acts on `WHMS`*: §3.1 says exactly
how far it reaches and §7 says what would settle the rest.

## 1. Reproducing the map

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07C5 --counts-only
0x07C5: 10 direct MOV DPTR site(s)  bank0=10

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07C5 --csv \
          --terminator-column \
          > ec/annotations/ec-0x07c5-sites.csv
$ tail -n +2 ec/annotations/ec-0x07c5-sites.csv | wc -l
10
```

`ec-0x07c5-sites.csv` is committed next to this file and every table below is
derived from it. The trailing `terminator` column says which of the guards
`walk_why()` stopped each window on, so a window the instruction budget cut is
not the same shape as one that stopped on a real terminator; the census and the
split between read and write are two commands over the same rows, and the third
is independent of both:

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07c5-sites.csv')))
print(collections.Counter(r['region'] for r in rows))
print(collections.Counter('read+write' if 'write' in r['access'] else 'read'
                          for r in rows))
print(len({r['file_offset'] for r in rows}), 'distinct file offsets')"
Counter({'bank0': 10})
Counter({'read': 6, 'read+write': 4})
10 distinct file offsets

$ python3 ec/tools/census_xdata_writers.py ec/firmware/GMxMGxx_11.800 0x07C5
0x07C5: 4 writer site(s) and 6 read-only site(s) of 10 found by sites_for()
  4 store instruction(s): read-modify-write 4
```

`census_xdata_writers.py`'s 4/6 split is computed from the image rather than
read out of the CSV, which is what makes it a check on the table above rather
than a restatement of it. It also prints ten lines of

```
census_xdata_writers.py: 0x08410: a 0x07C5 site this run finds that
    ec/annotations/manual-fan-ctrl-0751-sites.csv does not record
```

which is `WRITERS_CSV`/`SITES_CSV` defaulting to the `0x0751` walk's table, not
a defect in this walk and not a claim that anything is missing from
`0x0751`'s census: this run was not pointed at that file. A flag naming another
census table is a separate change to a shared tool, and this one does not make
it.

That is the reconciliation `registers.yaml` rests on, and it did not move:
`static_refs` / `static_refs_main_ec` / `static_refs_pd_image` are 10/10/0 and
`check_register_counts.py` reproduces them from the image.

```console
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
183 entries / 216 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

## 2. The 10 sites

Each site's containing routine is named from `ec/annotations/ghidra-functions.csv`
where that file has a row for it, and by the exported `ec/decompiled/bank0/*.asm`
banner (`FUN_CODE_…`) where it does not — the two `0xB5D3`/`0xB737` entries are
the only two of the ten without an annotation row, and the `FUN_CODE_` name is
Ghidra's made-up one, not a decode.

| addr | runtime | in routine | access | what the window does |
| --- | --- | --- | --- | --- |
| `0x07C5` | `0x8410` | `0x83FF=sync_0788_and_07d4_from_09e9` | read | `movx a,@dptr ; jnb acc.6,+0x09` — bit 6 gates a clear that is *past* the branch, §3.2 |
| `0x07C5` | `0x8CA9` | `0x8C46=ramp_1804_1809_toward_0461_0469` | read | `movx a,@dptr ; jb acc.7,+0x03` — bit 7 gates leaving for `0x8DE0`, §3.3 |
| `0x07C5` | `0xA777` | `0xA747=stage_0769_076e_convert_to_1803` | read | `movx a,@dptr ; anl a,#0x07 ; jnz +0x48` — bits 0-2 must be clear, §3.4 |
| `0x07C5` | `0xACFF` | `0xACB4=reset_xdata_flags_and_07d5_to_ff` | read+write | `anl a,#0x7f ; movx @dptr,a` — clears bit 7, §3.1 |
| `0x07C5` | `0xAD8C` | `0xACB4` (same routine) | read+write | `anl a,#0xdf ; movx @dptr,a` — clears bit 5, §3.1 |
| `0x07C5` | `0xB5F1` | `0xB5D3=FUN_CODE_b5d3` | read | `movx a,@dptr ; jnb acc.4,+0x03` — bit 4 picks the exit, §3.5 |
| `0x07C5` | `0xB751` | `0xB737=FUN_CODE_b737` | read | `movx a,@dptr ; jnb acc.4,+0x03` — bit 4, same shape in the sibling, §3.5 |
| `0x07C5` | `0xBB81` | `0xBB81=is_07c5_bit0_clear` | read | `movx a,@dptr ; xrl a,#0x01 ; ret` — returns bit-0-clear, §3.6 |
| `0x07C5` | `0xCC6B` | `0xCC64=init_06e6_1_clear_0743_07c5_and_07d5_ff` | read+write | `anl a,#0xdf ; movx @dptr,a` — clears bit 5, §3.1 |
| `0x07C5` | `0xCD18` | `0xCCFC=power_on_init_and_two_hang_paths` | read+write | `anl a,#0x7f ; movx @dptr,a` — clears bit 7, §3.1 |

Every window in that table is confirmed against the committed disassembly at
the address given, so a reader can check the decode rather than take it from
this file: `ec/decompiled/bank0/83FF.asm`, `8C46.asm`, `A747.asm`, `ACB4.asm`
(twice), `B5D3.asm`, `B737.asm`, `BB81.asm`, `CC64.asm` and `CCFC.asm`. The
`0xBB81` row is the only one whose window is its own whole routine, four
instructions long.

Two of the ten sites (`0xB5F1`, `0xB751`) sit in routines Ghidra has no
function row for, and both of those routines' boundaries are the call-target
byte scan's *upper bound* (`ec/annotations/bank-call-audit.md` §1) — the same
qualifier the `.asm` banner carries. "In routine `0xB5D3`" is that
hypothesis, read off the export, and is not independent of it.

### 2.1 `0xBB80` is a reader's neighbour, not a writer of this byte

`xdata-registers.csv`'s `0x07C5` row carries a `[writer]` tag on
`bank0:0xBB80=store_a_then_read_07c5` and a `[reader]` tag on
`bank0:0xBB81=is_07c5_bit0_clear`, and the cross-reference cell for `0x07C5` in
`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` §7 transcribes the first of
those as the row's writer. It is not one. `ec/decompiled/bank0/BB80.asm` is one
instruction:

```
BB80     f0 - -   movx     @DPTR, A
```

against whatever `DPTR` the caller left, and `0x07C5` is not an address this
instruction names — it does not load `DPTR` at all. The `0x07C5` access in this
pair is the *read* at `0xBB81`, which loads the address itself:

```
BB81     90 07 c5 mov      DPTR, #0x7c5
BB84     e0 - -   movx     A, @DPTR
BB85     64 01 -  xrl      A, #0x1
BB87     22 - -   ret
```

so the byte is read and never stored, and the census above is right to have
`0xBB80` in neither list. The row's own routine names already say this —
`store_a_then_read_07c5` is a name for a store followed by a fall-through into
a read, and `is_07c5_bit0_clear` is a name for the read. What is wrong is the
`[writer]` tag, and that tag is *generated* by `ec/tools/xdata_register_map.py`
(`ec/README.md`) from the routine's role, so the correction belongs in the
citation cell and in this section rather than in a hand-edit of the generated
CSV. §7 of the door procedure's cell now points here instead.

## 3. Bit by bit

The ten sites between them touch five distinct bit positions. Nothing sets any
of them.

### 3.1 The four writes: bits 7, 5, 5, 7

All four are read-modify-writes of a single bit, in three instructions, and all
four sit in a routine that masks a list of single bits across this and other
bytes as it goes. `census_xdata_writers.py` prints the mask for each:

| runtime | routine | mask | bit cleared | where the routine is annotated |
| --- | --- | --- | --- | --- |
| `0xACFF` | `0xACB4=reset_xdata_flags_and_07d5_to_ff` | `anl a,#0x7f` | 7 | `ghidra-functions.csv` — "clears bit 5 of `0x07C5`" in the same routine |
| `0xAD8C` | `0xACB4` | `anl a,#0xdf` | 5 | as above |
| `0xCC6B` | `0xCC64=init_06e6_1_clear_0743_07c5_and_07d5_ff` | `anl a,#0xdf` | 5 | `ghidra-functions.csv` — "clears bit 5 of `0x07C5` with an AND of 0xDF" |
| `0xCD18` | `0xCCFC=power_on_init_and_two_hang_paths` | `anl a,#0x7f` | 7 | `ghidra-functions.csv` — "bit 7 of `0x07C5` … the bit cleared above is bit 7, not that one" |

`0xACFF` and `0xAD8C` are 0x8D bytes apart in one routine, and both belong to
the same bit-masking run that `ec-07c4-07d5-sites.md` §4.3 transcribes at
`0xad93` when it reads `0x07D5`'s two `0xFF` stores:

```
AD8C     90 07 c5 mov      DPTR, #0x7c5
AD8F     e0 - -   movx     A, @DPTR
AD90     54 df -  anl      A, #0xdf
AD92     f0 - -   movx     @DPTR, A
AD93     90 07 88 mov      DPTR, #0x0788
AD96     74 ff -  mov      A, #0xff
AD98     f0 - -   movx     @DPTR, A
AD99     90 07 d5 mov      DPTR, #0x07d5
```

`0xCC6B` is the same three instructions in the same position in a different
init, and `0xCD18` the same in a third. All four are inside a whole-
machine reset pass or one of the two init entries, which is where a bit's
*power-on* value would be set rather than its steady-state one.

**What that does and does not say about `WHMS`.** The DSDT's field list
declares five unnamed, unallocated bits below `WHMS` at bit 5
(`dsdt.dsl:52243-52245`). `0xAD8C` and `0xCC6B` mask `0xdf`, which clears bit 5
and no other. So the instruction stream clears the bit position the ASL names
`WHMS`, in two places. **That the two are the same identity is a hardware
question and is not established here**: the field list is a naming fact and the
masks are a fact about three instructions, and nothing in the committed tree
joins them — no ASL reads the byte between the two, no capture exists, and
`windows/tools/gpu_block_watch.py`'s `WHMS b5` row is a *prepared* watch, not an
observation. What this walk adds to what §9 of the shared file had is a census
of every site that touches the byte and a statement that two of them clear that
bit position. Whether the EC, the ASL and the OS agree on what bit 5 of `0x07C5`
means is §7's first open question, and it is the one a human at the machine has
to answer.

### 3.2 `0x8410`: bit 6, and a clear the 8-instruction window does not reach

`0x83FF=sync_0788_and_07d4_from_09e9` is the routine
`ec-07c4-07d5-sites.md` §3 walks for the `0x07C4`/`0x07D4`/`0x07D5` block, and
`0x8410` is a read in it. The window stops at the branch one instruction after
the read:

```
8410     90 07 c5 mov      DPTR, #0x7c5
8413     e0 - -   movx     A, @DPTR
8414     30 e6 09 jnb      0xe6, 0x8420
8417     e0 - -   movx     A, @DPTR
8418     54 bf -  anl      A, #0xbf
841A     f0 - -   movx     @DPTR, A
841B     7d 85 -  mov      R5, #0x85
841D     12 16 3c lcall    0x163c
```

so the CSV classes `0x8410` as a read, and on this walk's own numbers that is
right — `0x07C5` is 4 read-modify-writes over 6 reads. It is also true that
`0x83FF` **clears bit 6 of `0x07C5` and then calls `0x163C` with `R5 = 0x85`**,
which is what the routine's own `ghidra-functions.csv` row says, and that
instruction pair is at `0x8417`-`0x841D` — three bytes past the window the CSV
stops at. The fifth store of this byte is therefore real, visible in the
disassembly and in the annotation, and **not** a row in the census, because the
census is a per-site window and this site's window ended at a flow opcode.

That is the same relationship §5 of the shared file draws for its three
truncated windows, and it is the honest limit of a per-address site table: a
`read` here is what an 8-instruction linear walk reached, not a statement that
the site does not write. This walk does not add `0x8417` as an eleventh site —
`MOV DPTR,#0x07C5` is at `0x8410` and there is one of those — but it does not
let the `read` class stand unqualified either.

### 3.3 `0x8CA9`: bit 7 as an entry condition

`0x8C46=ramp_1804_1809_toward_0461_0469` reads the byte to decide whether to
leave the routine at all:

```
8CA9     90 07 c5 mov      DPTR, #0x7c5
8CAC     e0 - -   movx     A, @DPTR
8CAD     20 e7 03 jb       0xe7, 0x8cb3
8CB0     02 8d e0 ljmp     0x8de0
```

bit 7 clear leaves for `0x8DE0`; bit 7 set falls through to the same test on
`AP_OEM` (`0x0741`) bit 0 and then `AP_OEM_6` (`0x07C6`) bit 2. The routine's
annotation states that triple as the condition, and `0x07C5` bit 7 is the first
of the three. This is the only site where `0x07C5` is one conjunct of a
larger guard rather than the thing being tested.

### 3.4 `0xA777`: bits 0-2, as "all clear"

```
A777     90 07 c5 mov      DPTR, #0x7c5
A77A     e0 - -   movx     A, @DPTR
A77B     54 07 -  anl      A, #0x7
A77D     70 48 -  jnz      0xa7c7
```

`0xA747=stage_0769_076e_convert_to_1803` proceeds only when the low three bits
of the byte are clear; non-zero skips to `0xA7C7`. Those are three of the five
bits the DSDT leaves unnamed, and the routine's own annotation lists them as
one of its guards.

### 3.5 `0xB5F1` and `0xB751`: bit 4, in a matched pair

The two sites have the same three instructions in two routines that are the
same shape, which is why they are one subsection rather than two:

```
B5F1     90 07 c5 mov      DPTR, #0x7c5
B5F4     e0 - -   movx     A, @DPTR
B5F5     30 e4 03 jnb      0xe4, 0xb5fb
B5F8     02 b7 16 ljmp     0xb716
B5FB     12 ba 36 lcall    0xba36
```

and the same at `0xB751`/`0xB754`/`0xB755`, with `ljmp 0xb82e` and the same
`lcall 0xba36` behind it. Bit 4 clear goes one way, set the other; the
destination differs, the shape does not. Both routines reach their site only
after a guard of their own — `0xB5F1` needs `0x06E6` to read `1` and bit 7 of
`0x0751` set, `0xB751` needs `0xB9D8` (`read_06e6_xor_01`) to return zero, bit
7 of `0x0751` set, bit 0 of `0x0490` set and `0x04AB` equal to `0x64` — and each
has its own exit rather than a shared one: `0xB5F8` tail-jumps to `0xB716`
(`clear_08eb_bit3_09e6_09e7_08a2_089e_089f`) and `0xB758` to `0xB82E`
(`clear_08eb_bit6_and_zero_08a0`), two near-siblings that each clear a different
bit of `0x08EB`. `0xB5D3` and `0xB737` have no `ghidra-functions.csv` row, so
what the two routines are *for* is not recorded here; the guard chains and the
two exits are read off the disassembly and are the only claims made about them.

Bit 4 is the bit `ec-07c4-07d5-sites.md` §9 says the *service* writes, and it
is the one bit these two firmware sites test and the one bit neither of the
four writes touches. That is a fact about the two halves' instruction streams
and is not evidence that the service and the firmware mean the same field by
it.

### 3.6 `0xBB81`: bit 0, as the routine's return value

`0xBB81=is_07c5_bit0_clear` is the whole of §2.1's read: it returns `1` when bit
0 is clear and `0` when it is set, and the `xrl` scrambles the other seven bits
into the return value without carrying information. Bit 0 is one of the five
the field list leaves unnamed, so what it gates is not determined by the DSDT
and is not determined here.

## 4. The two tens, reported apart

There are two independent counts of ten for `0x07C5` in the committed tree, and
they are different measurements that happen to agree. They are written as two
sentences for that reason.

**The firmware's ten** are the direct `MOV DPTR,#0x07C5` sites in the main EC
image, ten `bank0` rows in `ec-0x07c5-sites.csv`, reproduced by
`trace_xdata_refs.py --counts-only` and independently split 4/6 by
`census_xdata_writers.py` (§1). This file is about those ten and about nothing
else.

**The service's ten** are in `windows/decompiled/v3.1.39.0/ec-callsites-summary.csv`,
row `0x07C5,literal,10,10`, naming ten methods including
`GpuFeatures.SetGpuWhisperModeMainSwitch`,
`FanTable_Manager1p5.SetEcFanControlRespective` and the
`MyFanManager_RamFan1p5*` family. That is a count of the Windows stack's calls
into the EC, taken from a different binary by a different method.

**They are not the same ten**, and nothing here says they are: one is ten
places in a firmware image, the other is ten methods in a managed assembly, and
the firmware's ten include six sites that only read the byte. That the two
agree at ten is a coincidence worth recording and is not evidence of a
correspondence. §9 of the shared file records what the service does with
`0x07C5` — bit 4, and deferring the question to #106 and #101 — and this file
does not re-derive it. Note also that the service side is a count of call sites,
not of writes: `ec-callsites.csv`'s own `literal` column is a reference kind, and
a call site that only reads the byte would look the same.

## 5. What the table is not

Three limits, all of which apply to §2's rows as much as to the prose around
them, and the first of which §3.2 already used.

- **Each row is an 8-instruction linear window around one `MOV DPTR,#imm16`,
  decoded without control-flow recovery.** A window that ends at a branch is
  *this method stopping*. `0x8410` (§3.2) is the worked example: a `read` in the
  CSV and a bit-6 clear three bytes later.
- **Ten is what this method found, not what the firmware does with the byte.**
  The method sees direct `MOV DPTR` sites only. A register-held address, a
  table of pointers, `movx @Ri` or a `DPH` built at run time is invisible to
  it, which is the blind spot `docs/findings.md` §4c retracted a claim over.
- **Six reads are six sites, not six decisions.** `0xB5F1` and `0xB751` are the
  same three instructions in two routines; the two `0xACFF`/`0xAD8C` sites and
  the two `0xCC6B`/`0xCD18` sites are each one routine's masking list.

## 6. The status this walk leaves

`registers.yaml` keeps `WHMS` at `present-untested`, and its `static_refs` /
`static_refs_main_ec` / `static_refs_pd_image` stay `10` / `10` / `0`. Nothing
in this walk is a live observation, so nothing here could move a status value,
and a static site table is further from a live test than a live test is from
`confirmed-working`. The row's `note:` is extended with the per-site split, the
`0xBB80` correction and the two-tens distinction; its numbers did not move, and
`check_register_counts.py` still reproduces them from the image.

## 7. What this does not establish

- **Not that the EC acts on `WHMS`.** Four sites clear a bit of the byte; none
  of them is a live test, and a read-modify-write in a reset pass is what a
  bit's power-on value looks like whether or not anything reads it back. The
  fourth write is in `power_on_init_and_two_hang_paths`, whose own annotation
  records the two spin-forever arms it can end in.
- **Not that bit 5 is the identity `0xAD8C` and `0xCC6B` act on** (§3.1). The
  mask and the field-list name agree on a bit *position*; whether the ASL, the
  EC and the OS agree on what that position means needs a capture.
- **Not that the service's ten and the firmware's ten correspond** (§4).
- **Nothing about what sets `WHMS` to 1**, statically or live. No site in
  either image writes this byte outright; a set is not in the ten, and a set
  through a computed `DPTR` would not be in the ten either.
- **Not a `ret` count, a call graph, or a frequency.** The two `FUN_CODE_`
  routines' boundaries are the call-target scan's upper bound, and no site here
  is traced to a caller.
- **Nothing observed on hardware.** No register was read back and no write was
  attempted. This is static analysis of a committed image.
- **No Ghidra re-export.** Every routine named in §2 already had a
  `ghidra-functions.csv` row and an exported `.asm`/`.c`, so nothing was seeded
  and no project was rebuilt; that is issue #20's whole-program work.

## 8. What would settle the rest

`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` is the committed procedure and
`ec/tools/grade_gpu_door.py` grades its capture, and `0x07C5` is in both blocks'
watch set. Its §5 table is blank and this change leaves it blank: an example
row there reads as an observation. What a capture from a human at the machine
would add, and what nothing here can:

- **Whether bit 5 of `0x07C5` moves when the GPU block changes**, which is the
  question `windows/tools/gpu_block_watch.py`'s prepared `WHMS b5` watch
  exists to ask.
- **What `GpuFeatures.SetGpuWhisperModeMainSwitch` and
  `FanTable_Manager1p5.SetEcFanControlRespective` write into the same byte**,
  and whether the firmware's two bit-5 clears are re-run afterwards — the two
  halves of §4 meeting on one byte.
- **What bit 0 gates.** `0xBB81` returns it, `0xA777` tests bits 0-2 together,
  and the DSDT leaves the position unnamed.

Two questions this walk opened and deliberately did not answer: what bit 6's
clear in `0x83FF` is for, given the routine's stated job is syncing `0x0788`
and `0x07D4` from `0x09E9`-`0x09EB` (`0x09E9` still has no
`ec/annotations/registers.yaml` entry, so what it copies out of it is not
determined); and what the `0xB5D3`/`0xB737` pair is for, which is a decompile
of two unannotated routines rather than a question about `0x07C5`.
