# `0x07D6`/`0x07D7` — 213 sites, none of them in the EC firmware

[`ec-07c4-07d5-sites.md`](ec-07c4-07d5-sites.md) §9 hands these two over by
name: "**`0x07D6` (`DBSP`) and `0x07D7` (`CGCT`).** Left to the census pass;
this walk turned up nothing concrete about either." The hand-off sentence was
right that nothing was known and wrong about what there is to know — there are
213 direct `MOV DPTR` sites between them, and this file walks every one. The
correction is left visible in that file rather than edited out of it.

**Read the `region` column before anything else. All 213 sites are
`pd-image`; not one is in the main EC firmware.** They are the `ITE8850-PD`
program's own variables at its own `0x07D6`/`0x07D7` — a second 8051 program
with its own reset vectors, its own address space and therefore its own XDATA
map, which [`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) §1 sets out at length
and which `registers.yaml`'s own header spells out again. A `MOV DPTR,#0x07D6`
inside that image says nothing about what the EC does with its own `0x07D6`,
because they are not the same byte. Everything below is a decode of the PD
program. Nothing below is evidence about the EC.

**The finding that decides the two rows is on the ASL side, and it runs the
opposite way to the scan.** `0x07D7` has a decoded ASL writer and no
main-EC site at all: `T1WR`'s `Arg0 == 0x1176` branch does
`^^PCI0.LPCB.EC0.CGCT = Arg1` and then `Notify (^^PCI0.PEG0.PEGP, 0xC0)`
(`evidence/acpi/dsdt.dsl:50730-50733`). That is the shape of the
`0x07B0`-`0x07BE` blind spot `registers.yaml` already records, where
`0x07B9` is writable and working with no direct `MOV DPTR` reference
anywhere in the image. `0x07D6` has the mirror-image problem: it is named in
the DSDT's ECMG field list and **no ASL code touches it at all**. §7 works
through both.

So neither row is `present-untested`. All four rows in this change —
`0x07D6`, `0x07D7` and the companion `0x07C7`/`0x07C8` — are
`unknown-not-absent`, which is the value `registers.yaml`'s header defines
for exactly this situation: "the references that made it look present turned
out to belong to the PD image, so the EC image has none." `absent` is not
available either; §4c retracted that reading.

**None of this is a live test.** Every classification below is a statement
about an 8-instruction linear window around each site, plus the routine each
one sits in. A `write` class is an instruction storing to the address, never
evidence the PD firmware or the EC acts on it, and nothing here was measured
on hardware. The human step that would say what any of it is for is named in
§8 and is not written as a procedure that pretends to have run.

**One adaptation to the 07C4-07D5 shape, stated because it is a judgement.**
That file had **15** sites to put in a markdown table. This one has **213**.
The full per-site table therefore lives in the committed CSV, one row per
site, and this file carries the aggregate access table and the per-writer
narrative. That split is the one `ec-0x07d0-sites.md` used for its 254, which
is the precedent for a set this size. The `access` classification is still
per-site and still committed.

## 1. Reproducing the map

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x07D6 0x07D7 0x07C7 0x07C8 --counts-only
0x07D6: 142 direct MOV DPTR site(s)  pd-image=142
0x07D7: 71 direct MOV DPTR site(s)  pd-image=71
0x07C7: 0 direct MOV DPTR site(s)  none
0x07C8: 0 direct MOV DPTR site(s)  none

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x07D6 0x07D7 --csv \
      > ec/annotations/ec-07d6-07d7-sites.csv
$ tail -n +2 ec/annotations/ec-07d6-07d7-sites.csv | wc -l
213

$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-07d6-07d7-sites.csv')))
print(collections.Counter(r['region'] for r in rows))"
Counter({'pd-image': 213})

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
145 entries / 177 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

**The two counts a reader will meet are different units, not a
disagreement.** `trace_xdata_refs.py` counts raw `90 07 D6` / `90 07 D7` byte
patterns: 142 and 71, 213 in all. `ec/annotations/xdata-registers.csv` counts
*classified statements in the decompiled PD sources*, in buckets that sum to
its own `refs` column: **37** for `0x07D6` (cluster `pd-028` — 4 read, 11
write, 0 read+write, 14 passed-to-call, 8 address-taken, over 15 functions)
and **35** for `0x07D7` (cluster `pd-029` — 16, 6, 0, 7, 6, over 5
functions). The scan is additionally inflated by `inc dptr` walks, DPTR
re-loads, and byte patterns that are not instructions at all, so 142 against
37 is the expected relation and not a discrepancy to reconcile away.

Which number each claim rests on is stated where the claim is made. The four
`registers.yaml` rows carry **the scan's** numbers, because
`check_register_counts.py` measures those and the line above is what it
reproduces.

The `region` column is what separates the 213 from the main-EC firmware's
zero, and the arithmetic behind that zero is the whole result: 142 = 0 + 142
and 71 = 0 + 71, with `main EC` 0 in both. The `0x07C7`/`0x07C8` rows are
0 = 0 + 0. §5 is why those two zeros are a floor and not a total.

**The handoff bucket resolves one level deeper here, unlike the 07C4-07D5
set.** `register_ref_table.py --callee-depth 1` decodes the called routine's
own entry point:

| addr | read | write | r+w | handoff→read | handoff→write | handoff unresolved | none | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `0x07D6` | 86 | 14 | 3 | 32 | 3 | 1 | 3 | 142 |
| `0x07D7` | 45 | 14 | 1 | 9 | 0 | 0 | 2 | 71 |

`0x07D7`'s 9 handoffs all resolve as reads. `0x07D6`'s 36 resolve 35 ways and
one does not: the site at `0x951B` hands DPTR to `0xB2F7`, whose own entry
immediately hands it on again to `0x10C8`, and the second handoff is past
what depth 1 reaches. §4.4 resolves that one by hand from committed exports
rather than leaving it to be guessed at. Note the read/write columns here
(86/14 against §2's 85/10) are the same sites counted after the handoffs are
classified, which is why they do not match; §2's split is the raw walk.

Framing, in the `frame_onto`/`frame_over` sense of
[`bank-call-audit.md`](bank-call-audit.md) §8: **148 of the 213 have all 24
preceding anchors converging onto them** (94 of 142 for `0x07D6`, 54 of 71 for
`0x07D7`), and the rest carry 20-23 with a handful at 0. The majority verdict
holds everywhere, so the `frame_onto` column is not load-bearing for any claim
below, but it is named rather than smoothed over. The listings the argument
rests on (§3, §4, §5, §7) were re-run in `r2 -a 8051`; the commands are §6.

## 2. The sites, by access class

From `ec-07d6-07d7-sites.csv`, committed next to this file. `access` is that
file's own column — the verdict of the 8-instruction linear walk that follows
each `mov dptr` — reproduced here as the exact string the tool emits so the
tally reconciles against the CSV without a second parse:

| `access` | `0x07D6` | `0x07D7` |
| --- | ---: | ---: |
| `read x1` | 85 | 44 |
| `read x2, walks 2 consecutive bytes (inc dptr)` | 1 | 1 |
| `read x1, write x1` | 3 | 1 |
| `write x1` | 10 | 11 |
| `write x2, walks 2 consecutive bytes (inc dptr)` | 2 | 3 |
| `write x2, walks 3 consecutive bytes (inc dptr)` | 2 | — |
| `DPTR handed to lcall … -- direction unresolved here` | 36 | 9 |
| `no movx found in the decoded window` | 3 | 2 |
| **total** | **142** | **71** |

129 = 85+44 rows are a plain `read x1` and 21 = 10+11 a plain `write x1`; on
top of those, 4 rows are read-modify-write, 9 walk on through `inc dptr` into
the bytes above, 5 are the window stopping, and 45 hand DPTR to a subroutine.
The walk buckets overlap where a row both reads and walks, which is why this
table lists the tool's own strings rather than a set of mutually exclusive
categories. `movc a,@a+dptr` and `jmp @a+dptr` — the CODE-pointer blind spot
`ec-0x07d0-sites.md` §5 warns about, where a site builds a jump table rather
than touching XDATA — are **0** for both addresses, so no site in this set is
a miscounted table lookup.

That is a count of instructions, not of decisions, and the same distinction
the 0751 and 07C4-07D5 files draw. The two bytes are the loudest pair in the
whole `0x07C4`-`0x07D7` block by site count, and 100% of that loudness is in
another program.

## 3. The three functions the census tags `[writer]`, and what the values come from

`xdata-registers.csv` tags three of the fifteen `0x07D6` functions `[writer]`
and two of the five `0x07D7` ones. All five are already named, seeded and
exported in `../decompiled/pd/`, so this section reads committed decompiles
rather than hand-decoding anything new.

### 3.1 `pd:0xBECB` — the one site that writes both bytes

`write_07d6_07d7_07d8_07d9_then_store_07df` (`../decompiled/pd/BECB.c`). This
is the CSV row at `0xBECB`, `write x2, walks 3 consecutive bytes (inc dptr)`,
and it is the only site in either address that touches both:

```
0xbecb  90 07 d6  mov  dptr,#0x07d6
0xbece  ed        mov  a,r5
0xbecf  f0        movx @dptr,a        ; 0x07D6 = R5
0xbed0  a3        inc  dptr
0xbed1  eb        mov  a,r3
0xbed2  f0        movx @dptr,a        ; 0x07D7 = R3
0xbed3  e4        clr  a
0xbed4  a3        inc  dptr
0xbed5  f0        movx @dptr,a        ; 0x07D8 = 0
0xbed6  a3        inc  dptr
0xbed7  f0        movx @dptr,a        ; 0x07D9 = 0
0xbed8  ef        mov  a,r7
0xbed9  12 ac d3  lcall 0xacd3
0xbedc  e0        movx a,@dptr
0xbedd  90 07 da  mov  dptr,#0x07da
0xbee0  f0        movx @dptr,a
0xbee1  7b 01     mov  r3,#0x1
0xbee3  7a 07     mov  r2,#0x7
0xbee5  79 d9     mov  r1,#0xd9
0xbee7  90 07 df  mov  dptr,#0x07df
0xbeea  12 10 e8  lcall 0x10e8
```

**Where each value comes from: R5 and R3, and nothing else.** Both are
caller-supplied registers — there is no `mov a,#imm` on the path into either
byte — and the decompile's `param_2`/`param_1` are Ghidra's rendering of that,
not an argument list the vendor wrote. The two bytes are written as a pair,
adjacent, with no gap. So the narrow answer to "what is `0x07D6` set from"
for this function is: **from R5, in the same three-byte run that puts R3 into
`0x07D7` and zeroes the next two**. What R5 and R3 hold is not established
here; that is the caller, and it is one level out.

Two further sites in the same routine are reads, and they read the pair as a
pair:

```
0xbef3  90 07 d7  mov  dptr,#0x07d7
0xbef6  e0        movx a,@dptr
0xbef7  64 01     xrl  a,#0x01
0xbef9  70 61     jnz  0xbf5c
0xbefb  90 07 d6  mov  dptr,#0x07d6
0xbefe  e0        movx a,@dptr
0xbeff  64 01     xrl  a,#0x01
0xbf01  70 42     jnz  0xbf45
```

Both bytes are compared against `0x01`, `0x07D7` first. That is the one place
in this walk where the two are read back and tested against the same value,
and it is worth naming precisely because it is a *test*, not an assignment:
whether either branch is taken, and what it then does, is outside the window.

### 3.2 `pd:0xF247` — writes the caller's byte, then destroys it

`write_07d6_then_table_entry_then_0_3` (`../decompiled/pd/F247.c`), two CSV
rows: `0xF247` `write x1` and `0xF253` `DPTR handed to lcall 0x70a3`.

```
0xf247  90 07 d6  mov  dptr,#0x07d6
0xf24a  ef        mov  a,r7
0xf24b  f0        movx @dptr,a        ; 0x07D6 = R7
0xf24c  e4        clr  a
0xf24d  fc        mov  r4,a
0xf24e  7d 7f     mov  r5,#0x7f
0xf250  12 f3 cc  lcall 0xf3cc
0xf253  90 07 d6  mov  dptr,#0x07d6   ; reload -- the CSV row at 0xF253
0xf256  12 70 a3  lcall 0x70a3
0xf259  e4        clr  a
0xf25a  f0        movx @dptr,a        ; 0x07D6 = 0
0xf25b  a3        inc  dptr
0xf25c  74 03     mov  a,#0x03
0xf25e  f0        movx @dptr,a        ; 0x07D7 = 3
0xf25f  22        ret
```

The caller's byte survives only until `0xF256`. The CSV row at `0xF253` is
the **reload** — `walk()` starts a site's window three bytes in, past the
`mov dptr` itself, so what that row's `access` string calls a handoff is the
`lcall 0x70A3` two instructions further on, with `DPTR` back at `0x07D6`. The
function then overwrites `0x07D6` with `0` and `0x07D7` with `3` on the way
out. **The `0x07D7 = 3` store is the only immediate this walk finds for
either byte**, and it is the second half of a pair that leaves `0x07D6` at
zero: this function ends with the two bytes reading `0x00, 0x03`.

That `0x03` is also what §4's `0x8A04` site writes on one of its two arms,
which is the kind of agreement that makes `3` look like a state rather than a
constant — and it is still a statement about the instruction stream.

### 3.3 `pd:0xF440` — writes, calls, reads back, then sets 1

`write_07d6_then_set_1` (`../decompiled/pd/F440.c`), two CSV rows: `0xF440`
`write x1` and `0xF448` `read x1`. The routine is nineteen bytes:

```
0xf440  90 07 d6  mov  dptr,#0x07d6
0xf443  ef        mov  a,r7
0xf444  f0        movx @dptr,a        ; 0x07D6 = R7
0xf445  12 ab bf  lcall 0xabbf        ; the 0x07D7 writer, §3.4
0xf448  90 07 d6  mov  dptr,#0x07d6
0xf44b  e0        movx a,@dptr        ; read back whatever ABBF left
0xf44c  12 96 ed  lcall 0x96ed        ; ... and hand it to 0x96ED in A
0xf44f  74 01     mov  a,#0x01
0xf451  f0        movx @dptr,a        ; 0x07D6 = 1
0xf452  22        ret
```

**This is the most interesting sequencing in the walk**, and it is worth
being exact about what it does and does not show. The caller's byte goes in,
`0xABBF` runs, the byte is read back and passed to `0x96ED` in `A`, and the
function then stores `0x01` over it regardless and returns. So the value
`0x96ED` receives is whatever `0xABBF` left — `0xABBF` touches `0x07D7`, and
§3.4's read-back sites show it reads `0x07D7` repeatedly, but whether it also
writes `0x07D6` is not established here. **A `write` class is a write class**:
the read at `0xF44B` and the call at `0xF44C` are the parts that could make
this byte mean something, and neither is decoded here.

The CSV's third row in this neighbourhood, `0xF465` `read x1, write x1`, is
**not** in this routine — `0xF452` is its `ret`. `0xF465` sits in the run
starting at `0xF453` (`mov dptr,#0xFFCF ; mov a,#3 ; movx @dptr,a`), between
the seed at `0xF440` and the next one at `0xF477`, and that run's entry point
is not determined by anything used here. Its own window is
`mov a,r5 ; movx @dptr,a ; clr a ; mov r4,a ; mov r5,a ; mov r6,a ; movx
a,@dptr` — it writes `R5` and reads the byte straight back. The naming
convention here is the one `ec-07c4-07d5-sites.md` §4.3 uses for `0xCC78`:
the value is a `write`, the entry is not established, and it is not filled
in.

### 3.4 `pd:0xABBF` — the `0x07D7` writer, and the largest routine in the set

`build_masked_indexed_table_bytes` (`../decompiled/pd/ABBF.c`), seven CSV
rows: `0xABBF` `write x1`, then `0xABC7`, `0xABFF`, `0xAC13`, `0xAC1D`,
`0xAC29` and `0xAC40`, all `read x1`.

```
0xabbf  90 07 d7  mov  dptr,#0x07d7
0xabc2  ef        mov  a,r7
0xabc3  f0        movx @dptr,a        ; 0x07D7 = R7
0xabc4  12 e4 58  lcall 0xe458
0xabc7  90 07 d7  mov  dptr,#0x07d7
0xabca  e0        movx a,@dptr        ; read it back
```

**The value comes from R7 and is then used as an index, repeatedly.** The
decompile's header says what that index reaches: five address bytes —
`0x9028`, `0x906D`, `0x907E`, `0x9066`, `0x909A` — each of which builds DPTR
as `(R6 - 3 + carry)` in the high byte and the index in `A` as the low byte,
with indices built from `0x07D7` as 0, 4, 5, 6, 0x13, 0x15, 0x63 and 0x64.
The byte is then written with `0xFF`, `0x20`, `0x4B` or `0x44`, or masked
with `0xFC`, `0xF7` or `0xEF`, at whichever of those indices the current
value selects.

So `0x07D7` is used here as **an index or selector into a table**, not as a
value the program consumes. That is a reading of the addressing, and it is
the same shape the 07D0/07D1 walk found (index or state variable of the PD
firmware, `ec-0x07d0-sites.md` §7). It says nothing about the EC's own
`0x07D7`, and it does not say what the tables at `0x9028`-`0x909A` hold.

### 3.5 The other three functions, read the same way

- **`pd:0x88BE` `update_07d6_table_entries`** (`../decompiled/pd/88BE.c`) is
  the densest `0x07D6` routine, with six CSV rows. It stores the caller's
  byte, reads it straight back (`0x88C2`-`0x88C3`), multiplies it by `0x5E`
  and uses the result to address a table — `0x0900 + byte*0x5E`, the
  `0x08F6 + byte*0x5E` run, `0x0908 + byte*0x5E` — then ends in a
  three-byte store through `0x10E8` and, per the decompile's own note, has no
  `ret` after that call. **The byte is an index.** Whether it is the same
  index `0x07D7` is in §3.4 is not established: the strides are `0x5E` and
  the table bases are different.
- **`pd:0x805E` `update_07d4_state`** (`../decompiled/pd/805E.c`) holds the
  one `0x07D7` store this walk finds outside `0xBECB`, at `0x80A3`:

  ```
  0x80a3  90 07 d7  mov  dptr,#0x07d7
  0x80a6  ec        mov  a,r4
  0x80a7  f0        movx @dptr,a        ; 0x07D7 = R4
  0x80a8  6e        xrl  a,r6
  0x80a9  60 1d     jz   0x80c8
  ```

  and its paired `0x806F`, `write x2, walks 2 consecutive bytes`, which is the
  other half of the same shape:

  ```
  0x8068  90 07 d5  mov  dptr,#0x07d5
  0x806b  12 97 1b  lcall 0x971b
  0x806e  e0        movx a,@dptr        ; the byte 0x971B left DPTR on
  0x806f  90 07 d6  mov  dptr,#0x07d6
  0x8072  f0        movx @dptr,a        ; 0x07D6 = that byte
  0x8073  e4        clr  a
  0x8074  fe        mov  r6,a
  0x8075  a3        inc  dptr
  0x8076  f0        movx @dptr,a        ; 0x07D7 = 0
  ```

  So `0x07D6` is set here from a table byte and `0x07D7` is cleared, in one
  run — the "copies the byte `0x971B` returns to `0x07D6`, writes 0 to
  `0x07D7`" sequence in the decompile's header. The two bytes are set
  together here as well, and `0x805E` names the routine after `0x07D4`, which
  is the byte it is really about.
- **`pd:0x34D6` `index_stride_5e_from_07d6`** (`../decompiled/pd/34D6.c`) is
  the shortest read and the only `[math]`-tagged one: load `0x07D6`, multiply
  by `0x5E`, store the product into `DPL`. Its own annotation note records the
  reason the entry addresses look unaligned — the head loads `0x07D6` where
  `0x34D9`'s callers load `0x07D0`, and the two share the multiply. **The
  same stride-index shape, one byte over**, which is the closest thing to a
  shared mechanism between the two bytes in this walk.

**Across all five, one sentence covers the writers: they are writes in the
PD program's instruction stream, from caller-supplied registers, and none of
them is evidence that the EC acts on either byte.**

## 4. The five `none` rows, and the handoffs one level deeper

`trace_xdata_refs.py` classes a site by the instructions in the 8 that follow
the `mov dptr`, and a window that ends on a branch has no `movx` in it yet.
`static-refs-audit.md` §5.3 wrote down what a `none` cell is worth —
"this method stopped" — and reading it as "this site does not access the
register" is the `docs/findings.md` §4c error in miniature. Three of the
`0x07D6` sites and two of the `0x07D7` ones are `none`, and four of the five
resolve when the window is expanded:

| site | the walk stopped at | what is there |
| --- | --- | --- |
| `0x3474` | `ret` | a two-instruction stub: `mov dptr,#0x07d6 ; ret` — DPTR is the return value, §4.1 |
| `0xBB50` | `jnz +0x0f` | both arms run `lcall 0xB293` then `push dph ; push dpl ; lcall 0x0FAF`, §4.2 |
| `0xBD80` | `jnz +0x0f` | the same three, differing only in the mask that follows — `0x04` against `0x08` |
| `0x8A04` | `jc +0x05` | both arms store: `0x07D7 = 0x02` or `0x07D7 = 0x03`, then reload `0x07D6` |
| `0xAC79` | `jz +0x0d` | the fall-through reads it; the arm past the branch is a second read — §4.3 |

### 4.1 `0x3474` is a DPTR returned to the caller, and the stub has no entry

```
0x3474  90 07 d6  mov  dptr,#0x07d6
0x3477  22        ret
0x3478  90 07 d0  mov  dptr,#0x07d0
0x347b  e0        movx a,@dptr
0x347c  fb        mov  r3,a
0x347d  75 f0 60  mov  b,#0x60
```

There is no `movx` because there is no access *at this site*: the routine
loads the address and hands it back in `DPTR` for its caller to dereference.
Three bytes later sits the `0x07D0` twin, which falls through into
`read_byte_to_r3_stride_60_alt` at `0x347B`. The `0x34D6` annotation already
records this tail-sharing for `0x07D0`; this is the same shape on the
`0x07D6` side.

**The gap this lands on is named in §8, not filled here:** nothing in
`ghidra-functions.csv` covers `0x3474`, and seeding a routine is whole-program
work belonging to issue #20, the precedent `ec-07c4-07d5-sites.md` §9 sets.

### 4.2 `0xBB50` and `0xBD80` are the same passed-to-call shape, twice

```
0xbb50  90 07 d6  mov  dptr,#0x07d6
0xbb53  70 0f     jnz  0xbb64
0xbb55  12 b2 93  lcall 0xb293
0xbb58  c0 83     push dph
0xbb5a  c0 82     push dpl
0xbb5c  12 0f af  lcall 0x0faf       ; reads [0x07D6..0x07D9] into R4..R7
0xbb5f  ef        mov  a,r7
0xbb60  54 f7     anl  a,#0xf7        ; fall-through arm: clear bit 3
0xbb62  80 0d     sjmp 0xbb71
0xbb64  12 b2 93  lcall 0xb293        ; the jnz target: same three
0xbb67  c0 83     push dph
0xbb69  c0 82     push dpl
0xbb6b  12 0f af  lcall 0x0faf
0xbb6e  ef        mov  a,r7
0xbb6f  44 08     orl  a,#0x08        ; branch arm: set bit 3
0xbb71  ff        mov  r7,a
0xbb72  ec        mov  a,r4
0xbb73  d0 82     pop  dpl            ; restore the pushed 0x07D6
0xbb75  d0 83     pop  dph
0xbb77  12 10 41  lcall 0x1041        ; writes R4..R7 back at 0x07D6
0xbb7a  90 07 d7  mov  dptr,#0x07d7
0xbb7d  e0        movx a,@dptr
```

Both `jnz` arms run the identical `lcall 0xB293 ; push dph ; push dpl ; lcall
0x0FAF` sequence and differ only in the mask applied afterwards. Neither
accesses the byte through `DPTR` in place: it is pushed, and the routine
works on it through registers. That is a *passed-to-call* access, which is why
the census's `0x07D6` row carries a `passed-to-call: 14` bucket that the raw
`MOV DPTR` walk has no way to see. `0xBD80` is the same instructions with
`0x04` where `0xBB50` has `0x08`.

**The two callees are committed exports, so the direction is not a guess:**
`0x0FAF` is `read4xdata_to_r4_r7` (`../decompiled/pd/0FAF.c`) — four
`movx a,@dptr` with three `inc dptr`, so `R4`..`R7` are `[0x07D6]`, `[0x07D7]`,
`[0x07D8]`, `[0x07D9]` — and `0x1041` is its four-byte store counterpart
(`../decompiled/pd/1041.c`), invoked here with the pushed `DPTR` popped back
so it writes the same four bytes.

**So each of these sites is a read-modify-write of the four-byte window
`0x07D6`-`0x07D9`, and the bit it flips is bit 3 of `0x07D9`** — the mask is
applied to `R7`, which is the *fourth* byte read, not the one the site's
`DPTR` names. The site's own address is the base of a group, not the byte
being changed. That is the second place in this walk (§4.4's `0x951B`) where
these two bytes are handled as adjacent halves of a wider access, and it is
why reading a `none` cell as "no access" would have lost a write.

`0xB293` is not decoded here; it runs before the push on both arms and does
not receive `DPTR`.

### 4.3 `0xAC79`: the arm that resolves, and the one that does not

```
0xac79  90 07 d7  mov  dptr,#0x07d7
0xac7c  60 0d     jz   0xac8b
0xac7e  e0        movx a,@dptr         ; read, fall-through arm
0xac7f  fe        mov  r6,a
0xac80  e4        clr  a
0xac81  24 05     add  a,#0x05
0xac83  12 90 28  lcall 0x9028
0xac86  74 44     mov  a,#0x44
0xac88  f0        movx @dptr,a         ; ...but DPTR is the callee's now
        ...
0xac8b  e0        movx a,@dptr         ; branch arm: a second read
0xac8c  ff        mov  r7,a
0xac8d  e4        clr  a
0xac8e  fd        mov  r5,a
0xac8f  12 bb e7  lcall 0xbbe7
0xac92  90 07 d7  mov  dptr,#0x07d7
0xac95  12 91 15  lcall 0x9115
```

This is the honest `none`, and it is worth showing rather than resolving.
Both arms **read** `0x07D7`. The `movx @dptr,a` at `0xac88` looks like a
write of `0x44`, but it follows `lcall 0x9028`, and `0x9028` is one of the
five index-builders §3.4 described — it loads `DPTR` itself. **That store is
therefore not to `0x07D7`,** and reading it as one is exactly the error the
`none` classification exists to prevent. The branch arm reloads `0x07D7` at
`0xac92` before its own call, so both arms read the byte and neither is
shown writing it here.

### 4.4 The 45 handoffs, and the one that stays unresolved

Thirty-six `0x07D6` sites and nine `0x07D7` sites hand `DPTR` to a subroutine
rather than dereferencing it in place. §1 has the depth-1 resolution: 32 of
`0x07D6`'s resolve as reads and 3 as writes, and all nine of `0x07D7`'s as
reads, across 8 and 6 distinct callees. The largest single group is the 17
sites that hand to `0x34A5`, whose entry is `movx a,@dptr` and reads.

**One does not resolve by the tool, and is resolved here by hand from
committed exports** — the `ec-07c4-07d5-sites.md` §4.4 precedent. The site at
`0x951B` hands DPTR to `0xB2F7`, whose own first instruction hands it on to
`0x10C8`; depth 1 decodes one level, so the second handoff is past its reach.
Both callees are already exported:

```
0x951b  90 07 d6  mov  dptr,#0x07d6
0x951e  12 b2 f7  lcall 0xb2f7
0x9521  ef        mov  a,r7
0x9522  12 0c 58  lcall 0x0c58
0x9525  90 07 dc  mov  dptr,#0x07dc
```

`0xB2F7` is `read3_from_dptr_then_set_dptr_0002`
(`../decompiled/pd/B2F7.c`): it calls `0x10C8` and then overwrites DPTR with
`0x0002`. `0x10C8` is `read3_xdata_to_r3r1_10c8` (`../decompiled/pd/10C8.c`):
`movx a,@dptr / mov r3,a / inc dptr / movx a,@dptr / mov r2,a / inc dptr /
movx a,@dptr / mov r1,a / ret` — three consecutive reads.

**So the site is a read, and a three-byte one.** It reads `0x07D6`, `0x07D7`
and `0x07D8` into R3, R2 and R1, and the `mov dptr,#0x0002` that follows is
discarded by the caller's own next `mov dptr` at `0x9525`. That makes this the
one site in the set where the handoff is *known* to span both bytes, and it
corroborates the census's `address-taken` bucket: the PD program treats
`0x07D6`/`0x07D7` as adjacent halves of one 16-bit-ish read, exactly as
`ec-0x07d1-sites.md` found for the `0x07D0`/`0x07D1` pair.

It is still a read in a program that has its own `0x07D6`. The other eight
`0x07D6` callees — `0x38B6`, `0x35E8`, `0x3509`, `0x3539`, `0x34D9`, `0x884E`,
`0x70F8`, `0x70BA` — each take one site and all resolve at depth 1.

## 5. A computed `DPH` onto this page: null, and what a null is worth

This is the section that keeps `0x07C7`/`0x07C8`'s zero honest, so it runs the
same control `ec-07c4-07d5-sites.md` §6 did rather than asserting a null.
`manual-fan-ctrl-0751.md` §6 found the reason `0x0F00`'s zero direct-site count
is wrong: the EC reaches that page by building `DPH` at run time with
`addc a,#0x0f ; mov DPH,a` (`34 0F F5 83`), which no `MOV DPTR` scan sees.
The same construction aimed at the `0x07` page is `34 07 F5 83`:

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

**The control reproduces the eight `0x0F00` sites byte for byte and the `0x07`
page is empty.** The idiom itself is common — the same four-byte shape
appears in the EC image with 20 different immediates, `0x0F` eight times and
`0x0D` seven — so this is a real absence of one idiom on one page, not an
absence of the idiom.

It is still a narrow negative, and the reason has to be stated rather than
assumed away, because §4c is exactly this mistake. The register form (`mov
0x83,...` and `mov DPH,a` from a register) and an indirect `movx @Ri` are
equally invisible to this grep; `mov DPH,a` (`F5 83`) appears 87 times in the
EC image by itself, and this hunt only asks what *follows* it in the
immediate form. So: **no path found by this method reaches the `0x07` page
through a computed `DPH`, and 0 for `0x07C7`/`0x07C8` is a floor for that
reason rather than a total.**

What the null does *not* license is the word `absent`. `0x07C7` and `0x07C8`
are graded `unknown-not-absent` in `registers.yaml`, `0` is recorded verbatim
as `static_refs`/`static_refs_main_ec`/`static_refs_pd_image` because
`check_register_counts.py` measures it, and the note on each row cites §4c and
#110 — the computed-DPTR blind spot that owns the `0x07B9` case where a byte is
writable and working with no direct reference anywhere in the image.

## 6. Spot-checks against an independent disassembler

`ec/tools/disasm8051.py` is a linear decoder, not a disassembler, so every
listing this file's argument rests on was re-run in radare2 (installed by
`.github/actions/project-setup`, as `pd-xdata-overlap.md` §3 and
`ec-07c4-07d5-sites.md` §7 did). The PD image is flat, so `pd.bin` is a plain
64 KiB extract of the region at file 0x20000:

```console
$ dd if=ec/firmware/GMxMGxx_11.800 bs=1 skip=$((0x20000)) count=65536 of=/tmp/pd.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xbecb; pd 8'  /tmp/pd.bin   # the 0x07D6/0x07D7 pair write
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xbef3; pd 6'  /tmp/pd.bin   # the two == 1 reads
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x3474; pd 4'  /tmp/pd.bin   # the DPTR-return stub
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xbb50; pd 14' /tmp/pd.bin   # the push dph/dpl round trip
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8a04; pd 6'  /tmp/pd.bin   # the 0x02/0x03 pair
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xac79; pd 7'  /tmp/pd.bin   # the 0x9028-callee DPTR change
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xac8b; pd 5'  /tmp/pd.bin   # its branch arm
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xabbf; pd 5'  /tmp/pd.bin   # 0x07D7 = R7
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf247; pd 12' /tmp/pd.bin   # 0x07D6 = R7, then 0 and 3
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf440; pd 8'  /tmp/pd.bin   # write, call, read back, set 1
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf465; pd 5'  /tmp/pd.bin   # the run with no determined entry
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x88be; pd 5'  /tmp/pd.bin   # the 0x5E stride index
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x34d6; pd 6'  /tmp/pd.bin   # the 0x07D0 twin's multiply
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8068; pd 8'  /tmp/pd.bin   # the copy then the zero pair
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x80a3; pd 5'  /tmp/pd.bin   # 0x07D7 = R4
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x951b; pd 5'  /tmp/pd.bin   # the hand-resolved double handoff
```

All matched the listings in §3 and §4 instruction for instruction.
`python3 ec/tools/disasm8051.py --self-test` holds the opcode tables against
two hand-transcribed r2 windows, so the decoder underneath the site table is
itself pinned to r2:

```console
$ python3 ec/tools/disasm8051.py --self-test
self-test passed: both charge-profile-flow.md windows decode identically, all 4 relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode as transcribed
```

## 7. The ASL side, which is the opposite of the scan

The firmware scan is blind to ASL by construction — it reads the EC image and
the PD image, not the DSDT — and on these two bytes that blindness is the
whole story. Both are named in the DSDT's `ECMG` field list
(`dsdt.dsl:52254-52258`, `Offset (0x7D4)` then `CPUA`, `DBAP`, `DBSP`,
`CGCT`), and there the similarity ends.

**`0x07D7` (`CGCT`) has a decoded ASL writer and zero main-EC sites.**
`T1WR`'s `Arg0 == 0x1176` branch:

```
dsdt.dsl:50730      ElseIf ((Arg0 == 0x1176))
dsdt.dsl:50731      {
dsdt.dsl:50732          ^^PCI0.LPCB.EC0.CGCT = Arg1
dsdt.dsl:50733          Notify (^^PCI0.PEG0.PEGP, 0xC0) // Hardware-Specific
```

Two things are worth separating here. The **write** is a fact about the ASL:
an unconditional store of `Arg1` into the byte, with no guard on `DBEN` or any
other field — unlike the `Arg0 == 0x73` branch four branches above, which
wraps the same block's `CPUA`/`DBAP` publish in `If ((DBEN == One))`. The
**notification** is to `^^PCI0.PEG0.PEGP`, the PCI device behind the PEG0
root complex, and *not* to `\_SB.NPCF` as the `0x73` branch does. What that
notification is for is not recovered here and is not guessed at.

**`0x07D6` (`DBSP`) has no ASL site at all.** `grep -nE '0x7D6|DBSP'
evidence/acpi/dsdt.dsl` returns exactly one line — the field-list entry at
`dsdt.dsl:52257` — and no method in the DSDT reads or writes it. That is a
different statement from `0x07D7`'s and is recorded as such: `CGCT` has a
writer, `DBSP` has a name.

**The gap this opens, in `windows/tools/t1wr_callers.py`.** Its `ACPI_ARGS`
still reads `[0x1171, 0x1172, 0x1173, 0x2273]` and has never searched for a
caller of `0x1176`, so the counts in `docs/findings.md` §4f say nothing about
this branch. Adding the term re-bakes that tool's `EXPECTED_*` tables and the
corresponding figures, which is a calibration change with its own review and
a follow-up rather than a line in this change. **Whether `0x1176` is ever
issued on this board is not established by anything here** — a decoded ASL
branch is not an observed one, and the test that would decide it is a human's.

## 8. What is still open

- **Whether `0x1176` is ever issued, and what the EC then does with `CGCT`.**
  This is a `needs-hardware-test` question and no runner can take it. The
  prepared side of it already exists: `windows/tools/gpu_block_watch.py`
  sweeps `0x07D6` and `0x07D7` in one capture with the rest of the block, and
  `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` is the written procedure
  with its §7 citation list. The capture has not been taken and this file
  does not pretend otherwise.
- **What `DBSP` is for, given nothing in the ASL touches it.** A name with no
  access behind it is a real thing to find — the field list allocates it 8
  bits — but this walk cannot say what fills it, and the PD program filling
  its *own* `0x07D6` is not an answer.
- **The handoffs' second levels are covered only where §4 and §4.4 say so.**
  `--callee-depth 2` does not exist as a tool mode, so the other 44 handoffs'
  own callees are not systematically read. The two the walk does need
  (`0x0FAF`/`0x1041` at `0xBB50`, `0x10C8` at `0x951B`) were answerable from
  committed exports; `0xB293`, which runs before the push at `0xBB50` and
  does not receive `DPTR`, is the one left unread.
- **The stub at `0x3474` has no function entry.** Nothing in
  `ghidra-functions.csv` covers it, and the `0x34D6` annotation already
  records the tail-sharing that explains the unaligned entries. Seeding it
  and re-exporting is the whole-program work of issue #20, not a static
  walk's, and `ec-07c4-07d5-sites.md` §9 sets that precedent.
- **Widening `t1wr_callers.py` to `0x1176`** (§7), with its `EXPECTED_*` and
  `docs/findings.md` §4f re-bake.
- **The other eight `no row` cells in §7 of the door doc** — `0x07C9`-
  `0x07CF` and `0x07D2` — and the rest of the `0x07C4`-`0x07D7` block. Named,
  not done.
- **`0x07C7` and `0x07C8`.** Recorded as `unknown-not-absent` with a `0` that
  means "not found by this method". What reaches the `0x07` page at run time
  is not established, and #110 owns the blind spot that would have to close
  before the zero means more than that.
- **Whether any of the five PD writers is reached on this machine.** Every
  function in §3 is decoded statically and none of it is exercised; a
  `write` class is not evidence the program acts on the byte, and the EC
  side has no site at all.
