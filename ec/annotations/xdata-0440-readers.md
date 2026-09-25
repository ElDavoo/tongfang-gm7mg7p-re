# XDATA `0x0440`: what the 43 readers consult, and who writes the byte

`ec/annotations/xdata-0400-045f.md` §3 and §11 item 2 left this open: `0x0440` is
the busiest byte on the battery/temperature page — 43 EC-side direct sites, every
one a read — and no direct `MOV DPTR,#0x0440` site writes it in any image. This is
the answer to both halves. The machine-readable table is
**`xdata-0440-readers.csv`**, one row per site, keyed row-for-row to
`xdata-0400-045f-sites.csv`.

**Nothing here is a live observation.** No hardware is reachable from a
GitHub-hosted runner, so every status here is `present-untested` and a zero is
"not found by this method", never "absent" (`docs/findings.md` §4c, and the
`0x07B9` caveat in `ec/annotations/registers.yaml`).

## 1. How to reproduce it

The sweep, which reproduces the 43 rows and nothing else:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0440 --csv
```

`43 rows, all read x1` — 27 bank1, 13 bank0, 3 common. Every branch target in
§3-§5 was read with `r2 -a 8051` over the bank images the page document builds
in its own §1:

```console
$ cd ec/tools
$ python3 make_bank_image.py ../firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ python3 make_bank_image.py ../firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8328; pd 8' /tmp/bank1.bin
```

The table reconciles row-for-row against the committed site table — the same
check §7 of the page document does, keyed on `region` + `runtime`:

```console
$ python3 - <<'EOF'
import csv
a = [(r['region'], r['runtime']) for r in csv.DictReader(
        open('ec/annotations/xdata-0400-045f-sites.csv')) if r['addr'] == '0x0440']
b = [(r['region'], r['runtime']) for r in csv.DictReader(
        open('ec/annotations/xdata-0440-readers.csv'))]
print(len(a), len(b), a == b, sorted(set(a) ^ set(b)))
EOF
43 43 True []
```

43 in, 43 out, same order, no row on either side without its partner.

## 2. The grouping, and why it is by consequence and not only by constant

Grouping by the comparison constant alone gives 39 `jz`/`jnz` and 4 `cjne`, and
stops there. A constant table cannot say what the byte *selects*, so
`xdata-0440-readers.csv` carries four columns the site table does not: what the
equal path does, what the non-equal path does, and whether the site is co-gated
on `0x06E6 == 1`. Read with them, the 43 sites fall into five groups, disjoint
and covering all 43.

| group | n | what the value decides |
|---|---:|---|
| tick and countdown timers that stop | 3 | a per-tick `dec` is skipped: `0x8088` on `0x06D8`, `0x80EC` on `0x085B`, `0x8153` on `0x06DB` |
| flag and mode bits set, cleared or toggled | 9 | `0xABA5` and `0xC703` on `0x0751` bit 6; `0xAC0F` on `0x1606` bit 3; `0xC62A` and `0xF167` on `0x045B`/`0x0709`; `0xF24D` on `0x047B`/`0x097A` bit 4; `0x9046` and `0x8FD8` on `0x06E1`; `0x97F8` stores four whole constants |
| seeds and defaults | 4 | `0x8C9D` seeds `0x0670` to `0xA0`; `0x8F7C` seeds `0x081E`/`0x081F`; `0x933B` gates the whole `MODE_TCC_OFFSET_DEFAULTS` seeding; `0x9D05` syncs `0x046A`-`0x046F` from `0x086B`-`0x086E` |
| event-ring producers | 9 | `0x88F0` is the push; `0xF154` and `0xF18A` do nothing but call it, and `0x891C`, `0xA921`, `0xF198`, `0xF220`, `0xF2D5`, `0xF2FE` reach it from their own routines |
| state machines, clamps, dispatch selection | 18 | `0x1BC1`, `0x1BE0`, `0x3DA8`, `0x8328`, `0x87F5`, `0x8971`, `0x9675`, `0xA12D`, `0xA2F3`, `0xAAE5`, `0xB065`, `0xB0E1`, `0xB395`, `0xC71A`, `0xF275`, `0xF326`, `0xF33B`, `0xF350` — one line each in the CSV |

Two things fall out of the consequence column that the constant column hides.

**The byte is a selector, not an enable.** At **32 of the 39** zero tests, zero
is inert — the branch is a `ret`, a `sjmp` past the body, or a forward call to
somewhere else. That is the shape of an enable flag, and it is the reading to
start from. But at the other **7** the zero arm does work of its own, and
always of a *seeding* kind: `0x3DA8` clears internal-RAM bit `0x20.4`, `0x8C9D`
writes `0xA0` to `0x0670`, `0x8F7C` writes `0x00`/`0x28` to `0x081E`/`0x081F`,
`0x933B` clears `0x098C`, `0x9675` clears `0x06FD`, `0xA2F3` dispatches on
`0x0974 & 0x0F`, and `0xF275` toggles bit 7 of `0x0471`. So zero is not one
state either. A byte with a live zero arm, a live non-zero arm, and a value
that four sites compare by name is selecting between behaviours.

**The fan byte is the one consumer with a name attached.** `0xC703` is a
complete 14-byte stub — `mov dptr,#0x0440 / movx a,@dptr / jz +7 / mov dptr,#0x0751
/ movx a,@dptr / xrl a,#0x40 / movx @dptr,a / ret` — and `0xABA5` is the longer
version of the same arm, reached only when `0x06E6 == 1` and `0xC1CB` returns 1.
Both **toggle** bit 6 of `0x0751`; from a zero byte the result is `0x40`, which
is what makes the toggle read as "writes `0x40`". `0x40` is
`MANUAL_FAN_CTRL.FAN_MODE_BOOST` in `ec/annotations/registers.yaml` and
`MyFanCTLByteFlag.FanBoost_Mode` in
`windows/decompiled/v3.1.6.0/ECSpec.cs:25`. Nothing in either file ties a host
profile to that bit, so this is a consumer, not a decode.

## 3. The four sites that read the value itself

The other 39 never look at it. These four do, and following the `cjne` chains
past what the site table records is what turns "a flag" into "an enumeration".

| site | constant | equal | non-equal |
|---|---|---|---|
| bank1 `0x8328` `clear_and_set_xdata_flag_bits` | `0x07` | clears bit 1 of `0x097A` and of `0x0720` | `ret` — the rest of the routine is skipped |
| bank1 `0xA12D` `set_0724_bit7_after_06c5_threshold` | `0x08` | `ljmp 0xA1BE`, a bare `ret` | continues into the `0x045A` bit-0 test and the `0x0724`/`0x097A`/`0x0720`/`0x07F6` writes |
| bank1 `0xF2D5` `dec_0443_low3_unless_0440_5_6_7` | `0x05` | skip the `0x0443` decrement | `cjne` against `0x06`, then `0x07` |
| bank1 `0xF2FE` `inc_0443_low3_unless_0440_5_6_7` | `0x05` | skip the `0x0443` increment | `cjne` against `0x06`, then `0x07` |

`trace_xdata_refs.py` records one site per `MOV DPTR`, so the `0x06` and `0x07`
comparisons at `0xF2DE`/`0xF2E3` and `0xF307`/`0xF30C` are folded into the two
rows above — the accumulator is already loaded, so there is no second
`movx`. Read whole, the two `0x0443` routines skip on **5, 6 or 7** and step
`0x0443`'s low three bits on everything else.

So the set of values the firmware compares against is **{0, 5, 6, 7, 8}** — and
that is the *only* claim the readers support. It is not a closed enumeration.
Thirty-nine sites accept any non-zero byte without looking at it, so 1, 2, 3, 4
and 9-255 are not excluded by any reader. "The value is a small enumeration" is
a shape; "the value is in {0, 5, 6, 7, 8}" is not, and is not what is written in
`registers.yaml`.

`0x0443` is the tie that makes 5, 6 and 7 one thing rather than three: it is a
counter that freezes while the byte holds 5, 6 or 7, and `0x8300` (value 7)
clears bit 1 of `0x097A` and `0x0720` — the same two bytes
`dispatch_on_dpl_5b_7b_40` at bank1 `0x9F04` writes `0xF2` to. Whatever 5, 6 and
7 are, the firmware treats them as neighbours of each other and distinct from 8.

## 4. The `0x06E6` parallel, and which parts of this are load-bearing

**16 of the 43** sites are co-gated on `0x06E6` reading `0x01` — either a
`cjne a,#0x01` of their own (`0x88F0`, `0xF326`, `0xF33B`, `0xF350`) or a
`0x06E6 == 0x01` test in the routine they sit in (`0x87F5`, `0x933B`,
`0x9D05`, `0xABA5`, `0xAC0F`, `0xB065`, `0xB0E1`, `0x891C`, `0x8971`, `0xF167`,
`0xF220`, `0xF24D`). The `xdata-0440-readers.csv` `co_gate_06e6` column names
which, and which of the rest are merely in a routine that reads `0x06E6` later
(`0x8FD8`, `0x9046`) or not at all.

`0x06E6` is itself read as a mode index rather than a flag: it is written `5` at
power-on by `power_on_init_and_two_hang_paths` (bank0 `0xCCFC`, §8.5 below),
dispatched on `0x81`-`0x84` at bank0 `0xCF48`, and tested against `0x01` in the
same routines that gate on `0x0440`. `0xB9D8` is a three-instruction routine that
returns `0x06E6 ^ 1`, so `lcall 0xB9D8 / jnz` is the house idiom for "and
`0x06E6 == 1`".

The 16 are the profile-shaped sites — the fan toggle, the thermal-ceiling seed,
the ring producer — and those are mode-scoped. **The other 27 are not:** they
branch on `0x0440` whatever `0x06E6` holds, 21 of them with no `0x06E6` test
anywhere in the routine and 6 with a qualified reason recorded in the CSV column
(§4's own `co_gate_06e6`). `0x8088` (`807E.c`) and `0x8153` (`80EF.c`) contain no
`0x06E6` token at all, and all four `cjne` sites that compare the byte's value
are in the ungated 27. So the byte is read inside the `0x06E6 == 1` mode and
outside it, and the scoping is an observation about 16 of the 43 rather than a
property of the byte. What that leaves is a real but narrower claim: the
subsystems that would carry a host profile are the mode-scoped ones. The ungated
27 — mostly always-running tick and countdown sites — are equally consistent with
a global enable, so the scoping does not account for them.

Three further facts are consistent with the reading, not decisive:

- the `0x0751` FanBoost toggle (§2) says a host profile reaches the fan;
- `0x9334` seeds `MODE_TCC_OFFSET_DEFAULTS` only when `0x0440` is non-zero, so a
  host profile reaches the thermal ceiling;
- the ring at `0x070F`-`0x071F` is filled only when the byte is non-zero and
  `0x06E6` is 1, and `0x88F0` hands off to `0x19EA`.

None of the three names the value. A byte that gates three unrelated subsystems,
two of them only inside one mode, is consistent with a platform profile; it is
equally consistent with a vendor-internal state byte that happens to be
initialised externally. §6 is what separates the two.

## 5. The writer: found, and it writes zero

**`0x0440` has a writer, and no direct `MOV DPTR,#0x0440` site reaches it.**
The address is a CODE-table *record*, and the store goes through a helper.

`code_table_scatter_to_xdata` at bank1 `0xA530` loops `R2` times over a table in
CODE. Each pass reads three bytes at DPTR — destination high, destination low,
value — pops the first two back into `DPH:DPL` and stores the third there:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa530; pd 13' /tmp/bank1.bin
        ┌─< 0x0000a530      ba0002         cjne r2, #0x00, 0xa535
       ┌──< 0x0000a533      801f           sjmp 0xa554
       │└─> 0x0000a535      c083           push dph
       │    0x0000a537      c082           push dpl
       │    0x0000a539      e4             clr a
       │    0x0000a53a      93             movc a, @a+dptr
       │    0x0000a53b      c0e0           push acc
       │    0x0000a53d      a3             inc dptr
       │    0x0000a53e      e4             clr a
       │    0x0000a53f      93             movc a, @a+dptr
       │    0x0000a540      c0e0           push acc
       │    0x0000a542      a3             inc dptr
       │    0x0000a543      e4             clr a
```

and the store itself, ten instructions later at `0xa545`:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa545; pd 6' /tmp/bank1.bin
       ┌─< 0x0000a545      d082           pop dpl
       │    0x0000a547      d083           pop dph
       │    0x0000a549      f0             movx @dptr, a
       │    0x0000a54a      d082           pop dpl
       │    0x0000a54c      d083           pop dph
       └──> 0x0000a54e      a3             inc dptr
```

`ec/annotations/ghidra-functions.csv` already calls it *"Each pass pushes the
incoming DPTR, reads three CODE bytes at the source pointer, pops the first two
of them back into DPH and DPL so they form a big-endian XDATA address, writes the
third CODE byte there"*. What was not decoded is what the seven callers point it
at, and that is the whole of the question.

`ec/annotations/bank-call-targets.csv` has exactly seven `lcall 0xA530` sites,
all in bank1, and every one of them passes a literal `DPTR`/`R2` pair:

| call site | containing routine | CODE base | records | destinations in `0x0400`-`0x04FF` |
|---|---|---|---:|---|
| bank1 `0x83B7` | unexported; entry bank1 `0x8354` | `0x8453` | 67 | **`0x0440` ×2** (`0x00`), `0x0457` (`0x00`), `0x043E` (`0x20`), `0x045B` (`0x00`), `0x045C` (`0x00`), `0x045F` (`0x00`), `0x046A`/`0x046B`/`0x046E`/`0x046F` (`0x00`), `0x0474`/`0x0475` (`0x00`), `0x0495`/`0x0496`/`0x0498`/`0x049D`/`0x049E` (`0x00`) |
| bank1 `0x841D` | `zero_1510_and_clear_xdata_flag_bits` (`0x8418`) | `0x851C` | 23 | **`0x0440` (`0x00`)**, `0x0457` (`0x05`), `0x0459` (`0x00`), `0x0480` (`0x00`) |
| bank1 `0x82FD` | unexported (nearest exports `0x820F` / `0x8300`) | `0x8561` | 17 | `0x0457` (`0x80`), `0x046A`/`0x046B`/`0x046E`/`0x046F` (`0x00`) |
| bank1 `0x82C9` | unexported (nearest exports `0x820F` / `0x8300`) | `0x8594` | 1 | `0x0457` (`0x83`) |
| bank1 `0xC740` | `setup_state_and_copy_30_byte_table` (`0xC700`) | `0xC6E2` | 10 | none (`0x0390`-`0x0898`) |
| bank1 `0xC7AC` | `copy_6_bytes_via_a530_and_clear_0497b7` (`0xC7A7`) | `0xC7A1` | 2 | none (`0x038E`-`0x038F`) |
| bank1 `0xC7F2` | `copy_48_bytes_via_a530_from_c7bd` (`0xC7ED`) | `0xC7BD` | 16 | none (`0x0363`-`0x082F`) |

The first three bases are contiguous — `0x8453` + 67×3 = `0x851C`, + 23×3 =
`0x8561`, + 17×3 = `0x8594` — so 108 records over `0x8453`-`0x8596` are one table
walked in four chunks. Reading all 108 records against the committed image:

```console
$ python3 - <<'EOF'
d = open('ec/firmware/GMxMGxx_11.800','rb').read()
def fo(rt): return rt if rt < 0x8000 else 0x10000 + (rt - 0x8000)
for name, base, n in [("0x83B7", 0x8453, 0x43), ("0x841D", 0x851C, 0x17),
                      ("0x82FD", 0x8561, 0x11), ("0x82C9", 0x8594, 0x01)]:
    for i in range(n):
        o = fo(base) + 3*i
        if (d[o] << 8 | d[o+1]) == 0x0440:
            print(f"bank1 {name}  record i={i}  CODE file 0x{o:05X} "
                  f"= {d[o:o+3].hex(' ')}  ->  XDATA 0x0440 = 0x{d[o+2]:02X}")
EOF
bank1 0x83B7  record i=0  CODE file 0x10453 = 04 40 00  ->  XDATA 0x0440 = 0x00
bank1 0x83B7  record i=2  CODE file 0x10459 = 04 40 00  ->  XDATA 0x0440 = 0x00
bank1 0x841D  record i=9  CODE file 0x10537 = 04 40 00  ->  XDATA 0x0440 = 0x00
```

**Three records, and all three store `0x00`.** Both decoders agree
(`ec/tools/disasm8051.py` and the `r2` hexdump at `0x8453` and `0x8537`).

So every write to `0x0440` found in any image is a **zero**, and nothing found by
the methods below writes it anything else. That is the shape the 43 readers are
written for: a byte the EC puts to zero in code that reads as initialisation, and
then only reads.

Two limits on this, both real. **When** these two tables are walked is not
established here: the routine holding `0x83B7` has no export and no recorded
caller (its entry is bank1 `0x8354`), the one holding `0x841D` is exported but is
reached from `0x86EE`, which is neither, and `ec/annotations/bank-call-targets.csv`
has no row targeting either. The surrounding code — clearing `0x045A`, `0x1510`,
`0x0801`, `0x06E1`, `0x0442` — reads as initialisation, and that is the whole of
the basis for saying "initialisation" at all. And `0x0440` appears in only three
of the 108 records, so this is a record that happens to name the byte, not a
table whose purpose is to set it.

## 6. The hypothesis, named as one

**`0x0440` is an OS/control-centre-written platform-profile or mode index, in
the same family as `0x06E6`; non-zero means a host profile is active, and the
value selects which. The EC initialises it to zero and never changes it.**

What supports it, in descending order of weight:

1. **§4 — 16 of the 43 are scoped to `0x06E6 == 1`, and they are the
   profile-shaped ones.** A second selector scoped to one mode is what a profile
   looks like; a global flag would not need scoping. The other 27 are not
   scoped, so this is weaker than it looks: 16 of 43 with the ungated remainder
   unexplained by the scoping, and all four value-comparing sites among it.
2. **§5 — every writer found writes zero, in code that reads as init.** A byte
   the firmware puts to zero and never sets is a byte the host owns.
3. **§2/§3 — the byte selects between behaviours rather than switching one on.**
   Zero is inert at 32 of the 39 zero tests and seeds at the other 7; 5, 6, 7
   and 8 each reach a different arm, and 39 sites are indifferent to which.

What would falsify it: a live read of `0x0440` showing a value outside
{0, 5, 6, 7, 8} while a reader that cares is reached, which would make it an open
enumeration rather than the small one the four `cjne` sites imply; a writer
found in an unexported routine that stores a non-zero; or `0x06E6` turning out to
be a state variable that happens to be 1 whenever this byte is interesting, which
would leave `0x0440` as an EC-internal state byte written by a code path §8 does
not reach.

One counterexample to support 1 is already in hand rather than pending, and it
cuts against the hypothesis: 27 of the 43 readers reach `0x0440` while
`0x06E6 != 1` (§4), so the byte is demonstrably not scoped to that mode. The
scoping survives only as a property of the 16, and the hypothesis has to stand on
supports 2 and 3 without it.

The experiment that would settle it is a human with the machine, and it is
**not** run here: a read of `0x0440` (with `0x06E6` beside it) across a Control
Center profile switch, in the shape of
`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv`. That capture watched
`0x0400`-`0x07FF` and recorded six bytes on this page moving; `0x0440` was not
one of them, which bounds the question and does not answer it — the capture
cycled the battery profile, whatever writes `0x0440` may be a different switch.

## 7. What the writer hunt found, method by method

Each entry gives the method, its scope, and what it did **not** exclude. The
issue asked for this as the deliverable in place of a writer, and §5 turned one
of the five methods into a positive; the other four stay negative, bounded.

### 7.1 Register-indirect `movx @Ri` — not found

A correction first, because it changes the arithmetic. The obvious candidate
opcodes are `0xE6`/`0xE7` (605 byte occurrences in `0x00000`-`0x17FFF`), and
`0xE7` is **not** an XDATA write: on this opcode map `0xE6`/`0xE7` are
`mov a,@Ri` / `mov @Ri,A` against **internal** RAM, and `0xF2`/`0xF3` are
`movx @R0,a` / `movx @R1,a`. Both `ec/tools/disasm8051.py` and `r2 -a 8051`
agree, and `disasm8051.py:205-212` is the table that settles it. The
register-indirect XDATA write class is therefore **154** bytes, not 605:

```console
$ python3 -c "
d=open('ec/firmware/GMxMGxx_11.800','rb').read()[0x00000:0x18000]
for n,ops in (('movx @Ri,a  (F2/F3)',(0xF2,0xF3)),('movx a,@Ri  (E2/E3)',(0xE2,0xE3)),
              ('mov a,@Ri   (E6/E7)',(0xE6,0xE7)),('mov @Ri,a   (F6/F7)',(0xF6,0xF7))):
    print(f'  {n:22}', '  '.join(f'0x{o:02X}={sum(1 for b in d if b==o)}' for o in ops))"
  movx @Ri,a  (F2/F3)    0xF2=84  0xF3=70
  movx a,@Ri  (E2/E3)    0xE2=190  0xE3=125
  mov a,@Ri   (E6/E7)    0xE6=422  0xE7=183
  mov @Ri,a   (F6/F7)    0xF6=199  0xF7=78
```

Reducing those 154 bytes to instructions this repo has exported, and then asking
whether the pointer register held `0x0440`:

| step | count |
|---|---:|
| `0xF2`/`0xF3` byte occurrences in the EC image | 154 |
| on an instruction boundary in an exported `.asm` listing | 21 |
| with `mov Ri,#0x0440` anywhere earlier in the same listing | **0** |

Two of the 21 are in listings the index itself labels as data
(`bank1/852F.asm` in `table_bytes_disassembled_as_code_8504`, `bank1/ED09.asm` in
`data_run_1a_1e`), so the instruction-aligned count is an upper bound on real
code. **Excluded:** any `movx @Ri,a` in code no listing covers, and any pointer
register set from memory or a subroutine rather than an immediate.

### 7.2 Computed DPTR — not found

| step | count |
|---|---:|
| `movx @DPTR,A` on an instruction boundary in the exported listings | 3731 |
| with both `DPH` and `DPL` last written as immediates in the 12 instructions before | **0** |
| `addc a,#imm` immediately followed by `mov DPH,A` / `mov DPL,A` | **0** |

The whole exported corpus contains nine `mov DPH,#..` / `mov DPL,#..` in all:
`mov DPH,#0x04` at bank0 `0xD585` (`read_xdata_0400_plus_r7`, which sets `DPH`
hard and loads `DPL` from R7, so it addresses `0x0400`+R7) and at bank0 `0xD7C2`
and `0xD7CA`; `mov DPH,#0x03` at bank1 `0xD3A7`, `0xD438`, `0xD440` and `0xE37A`;
`mov DPL,#0` at common `0x7180` and `0x0E1B`. The `0x04xx` one is a **reader** —
`ec/annotations/ghidra-functions.csv` types it `reader` and its body is
`movx a,@dptr` — and the `0x03xx` ones cannot reach `0x0440` from a `0x03` high
byte. A byte-level scan of the whole EC window finds the same nine and no
`mov DPL,#0x40` and no `mov DPH,#0x44`.

> **CORRECTION (2026-09-25, issue #250) to this subsection, in two places,
> both of which run in the direction that *opens* a hole rather than closing
> one.** The first is the "same nine": a byte-level scan of the EC window
> `0x00000`-`0x17FFF` finds **eight**, not nine. The ninth, at `0x0E1B`, is in
> the **PD image** — `ec/decompiled/pd/0E54.asm` — not the EC common area, so
> it is outside the window the sentence names and the PD program has its own
> XDATA map. The nine figure is right for the whole exported corpus, which
> includes the `pd` scope; it is wrong for the EC window, and the sentence
> conflates the two.
>
> The second is the §7.2 table's third row, which reads "`addc a,#imm`
> immediately followed by `mov DPH,A` / `mov DPL,A` | **0**". The count is
> **not 0**. Scanning the same EC window for the byte pattern `34 xx f5 83`
> finds **64** `addc A,#imm ; mov DPH,A` sites and **0** of the `DPL` form, of
> which **58** are immediately preceded by `clr A` and so build the high byte
> exactly, and **exactly one** of the 64 builds page `0x08` — a page that
> does not matter for `0x0440`, but the construction is real and the row is
> not. The consequence for §5 and §6 is the same in kind as the correction
> above: the "**Excluded**" sentence that closes this subsection is a **real
> and open** exclusion rather than a closed one, and one instance of the shape
> it names is a store. `ec/annotations/xdata-1c3x-consumers.md` §6.2 re-runs
> the method, reports all 64 with their immediates, and names the six sites
> that are not preceded by `clr A` — the residual this subsection does not
> reach. The old rows stay visible here for the reason the rest of the tree's
> corrections do.

This is the method issue #110 is adding to `trace_xdata_refs.py`; the general
tool is that issue's work and this is the bounded single-address version.
**Excluded:** a DPTR built from a register or memory value that reaches `0x0440`
without any `DPH`/`DPL` immediate in the preceding 12 instructions, and a
DPTR built inside a callee and handed back.

### 7.3 CODE-table copy at init — **found** (§5)

73 exported listings contain both a `movc` and an XDATA store. 34 store sites
across 32 of them have the bulk-store stride `clr A / inc DPTR / movx @DPTR,A`
in either order; walking the DPTR base back from each of the 34 finds **none**
in `0x0400`-`0x04FF`, so none of them is seeded into `0x0440`'s page. The
remaining `movc` writers build the destination out of the table instead, and one
of them is `code_table_scatter_to_xdata` — which is §5. The generalisation of
that search, and what it leaves open, is §7.6.

The other init-time table writer, `init_xdata_from_code_table_64fd` (bank0
`0xBFDE`), is the one that can write *any* address: 90 three-byte records at CODE
`0x64FD`, the first two bytes of each a big-endian XDATA destination. All 90
destinations are in `0x1600`-`0x16F0`:

```console
$ python3 -c "
d=open('ec/firmware/GMxMGxx_11.800','rb').read()
b=0x64FD
dst=[(d[b+3*i]<<8)|d[b+3*i+1] for i in range(90)]
print('records:', len(dst), ' range:', hex(min(dst)), '-', hex(max(dst)))
print('in 0x0400-0x04FF:', [hex(x) for x in dst if 0x400<=x<=0x4ff] or 'none')"
records: 90  range: 0x1600 - 0x16f0
in 0x0400-0x04FF: none
```

**Excluded:** a table walked by an unexported caller of a helper whose name does
not say it is a table copy.

### 7.4 The three common-area sites' containing routines — resolved, and the prediction refuted

The plan this work follows expected the two common-area readers to be one
coherent pair on `0x0A56`. They are not, and that is worth recording because the
expectation was reasonable.

`FUN_CODE_1ba4` (common `0x1BA4`) holds **two** of the three sites, `0x1BC1` and
`0x1BE0`, and they are the same decision read twice: `0x1BE0` sits inside the
arm `0x1BC1` opens, after the `0x074E` bit-4 and `0x0A54`-in-`[0xAD,0xB8)` tests
(whose `param_1 != 0` arm widens the window to `[0xD2,0xDD]`). Both gate the same
store, `DAT_EXTMEM_0a56 ^= 1`, on `0x0440` being non-zero.

`FUN_CODE_3da8` (common `0x3DA8`, the routine's own entry) holds the third, and
it does not touch `0x0A56` at all:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x3da8; pd 7' /tmp/bank0.bin
            0x00003da8      900440         mov dptr, #0x0440
            0x00003dab      e0             movx a, @dptr
        ┌─< 0x00003dac      7004           jnz 0x3db2
        │   0x00003dae      c204           clr 0x20.4
       ┌──< 0x00003db0      8006           sjmp 0x3db8
       │└─> 0x00003db2      90007e         mov dptr, #0x007e
       │    0x00003db5      7414           mov a, #0x14
```

`_0_4` in `ec/decompiled/common/3DA8.c` is the bit-address `0x04` of `c2 04`,
which is **internal RAM byte `0x20`, bit 4** — not `DAT_EXTMEM_0a56`, and not
XDATA. The non-zero arm writes `0x14` to `0x007E`. The `_0_4` artifact is
resolved against the bank image rather than guessed, as asked, and the answer
removes the coherence the plan predicted.

**Excluded:** nothing here — both routines are exported, both are decompiled, and
the two sites in `FUN_CODE_1ba4` are read from its own `.asm`.

### 7.5 Init and reset vectors — not found, directly

`reset_vector_forwarder_to_0070` (common `0x0000`, a single `ljmp 0x0070`) leads
to `FUN_CODE_0070`: `SP = 0xC0`, `0x1001 = 0x3F`, then four calls. It does not
write `0x0440`.

`power_on_init_and_two_hang_paths` (bank0 `0xCCFC`) writes `5` to `0x06E6` — the
mode selector of §4 — and then calls `0xCC3D`, `0x18AC`, `0xC4D1`, `0xD084` and
`0x2896`, clears six flag bits, and takes one of two hang paths. It does not
write `0x0440` itself, and no bulk-XDATA clear in the exported corpus is seeded
into the `0x04xx` page (§7.3's 34 strides). `0x06E6 = 5` at power-on and
`0x06E6 == 1` gating the `0x0440` readers is consistent with the host moving the
mode out of 5 and then setting `0x0440`; nothing found here does either.

**Excluded:** the five callees' interiors beyond what their own annotations
record, and any XDATA clear loop whose base comes from a register — seven
parameterised "zero N bytes at DPTR" helpers exist (`bank0 0xB963`, `0xEDE1`,
`0xEE58`, `0xF07C`, `0xF099`, `0xF17B`, `0xF4AD`) and a caller that hands one of
them `0x0440` would be invisible here. That is the `DPTR handoff` blind spot
`xdata-0400-045f.md` §2 describes, and it is the largest remaining one.

### 7.6 The generalisation, and the residual

Because §5 paid off, the search was widened past `0xA530` to every exported
listing that contains a `movc`, contains an XDATA store, and writes `DPH` or
`DPL` from a **non-immediate** source within the 12 instructions before one of
those stores — a register, the accumulator, or a `pop` of a value an earlier pass
left on the stack. **45 listings** match; 4 are in the `ITE8850-PD` image and so
not EC references at all, leaving **41**.

| of the 41 EC-side | count | |
|---|---:|---|
| nearest `mov DPTR,#imm` before the store is in `0x0400`-`0x04FF` | 2 | `FUN_CODE_8b14` (`#0x043E`) and `FUN_CODE_b5d3` (`#0x047F`) — in both, the non-immediate `DPH`/`DPL` write *follows* the immediate and overrides DPTR, so the store address is not that immediate |
| no `mov DPTR,#imm` in the window at all | 18 | |
| nearest immediate is outside `0x04xx` | 21 | |

So none of the 41 is pinned to `0x0440`'s page. Seven of them were traced anyway,
because their destination comes from *outside* the routine — `common 0x2ACD`,
`0x30B5` and `0x34C6` `push DPH`/`push DPL` and `pop` the caller's back, and
`common 0x3BD0`, `0x3BEF`, `0x43A5` and bank0 `0xDB8A` build `DPH`/`DPL` from a
caller-loaded register. Their 26 call sites, from
`ec/annotations/bank-call-targets.csv`:

| | count | reaching `0x0400`-`0x04FF` |
|---|---:|---:|
| call site passes a literal `mov DPTR,#imm` within 128 bytes before | 11 | **0** |
| DPTR not set by any immediate within 256 bytes before | 15 | not established |

**This is the residual, stated rather than hidden: 15 of those 26 call sites get
DPTR from a table read, a loop or a subroutine, and this method does not follow
it — and the other 34 of the 41 listings have not been traced to a reachable
address set at all.** A non-zero writer of `0x0440` in any of them is not
excluded. Narrowing it is a follow-up (§9), not something this change settles.

## 8. Cross-component

A byte the EC only ever reads may be written by whoever initialises the machine.
Four components, four bounded negatives — and one mechanism that exists with no
caller.

### 8.1 DSDT — the general write exists, nothing calls it

`evidence/acpi/dsdt.dsl:52193` declares
`OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`, and its field
list proves ECMG offsets are EC XDATA addresses with no base offset: `CPTM` at
`Offset (0x43E)` (`:52196`) is this repo's `CPU_TEMP`, `VGAT` at `Offset (0x44F)`
(`:52198`) is `GPU_TEMP`. The list steps from `0x43E` straight to `0x44F`; there
is **no field at `0x440`**, and the literals `0x440`, `0x0440` and `1088` appear
nowhere in the file.

*(The issue as filed asks about "ECMG offset `0x040`". That is off by `0x400`;
`0x040` is not the address. The address is `0x0440` and this is what was
searched.)*

`ECRW` at `:50504` is a fully general 16-bit write:

```asl
Method (ECRW, 2, NotSerialized)
{
    Local0 = (0xFE410000 + Arg0)
    MMRW (Local0, One, Zero, Arg1)
}
```

So the ASL **can** write `0x0440`, with `Arg0 = 0x0440`. It has **no call site**:
no `Call(ECRW…)`, `Store(ECRW…)` or `CondRefOf(ECRW…)` exists anywhere in the
committed DSDT. The three `ECRW` tokens in the file are the definition and a
method-local `CreateBitField` alias at `:4437` that is a buffer-bit zeroing in
`Device (PCI0)`, a different namespace. Its read counterpart `ECRR` (`:50497`) is
likewise defined and uncalled. Both are externally-invoked ACPI entry points, so
"uncalled in the DSDT" is not "unreachable" — see §8.3 for whether anything
external passes `0x440`. It does not.

### 8.2 BIOS — structurally cannot reach it

The BIOS reaches the EC through the ITE `0x62`/`0x66` index-data port pair, and
its write sequence is `0xA3` handshake → `0xA2` **address byte** → `0xA5` data
byte. The address argument is typed `undefined1` in
`bios/decompiled/OemApControlDxe.c` (`FUN_00000a14`), i.e. 8-bit. The address
bytes the BIOS actually writes across that module are `{0x3c, 0x65, 0x66, 0x6c,
0x6d, 0x6e, 0x80, 0x82}`; the highest is `0x82`. There is no 16-bit-address
helper and no page-select that would build `0x440`.

Tree-wide, `0x440` / `0x0440` / `1088` in `bios/decompiled/` are code addresses,
`[RBP+0x440]` stack offsets and one setup-variable `VarOffset: 0x440` in
`bios/ifr/Setup.en-US.ifr.txt`; none is an EC address, and `1088` appears only
inside longer hex constants. The only `0xFE41` reference in `bios/` is
`bios/decompiled/OemHooksPei.c:520`, a magic-word compare against
`0xFE410001` — base+1.

**Excluded:** anything in the raw firmware image that is not in the committed
decompiles, and a partial decompile. Per-module copies of the `0x62`/`0x66`
helper mean a name-based per-file summary is incomplete, but the tree-wide grep
covers every module.

### 8.3 Windows — can reach it, does not

`windows/decompiled/v3.1.6.0/ECSpec.cs` is a flat decimal `const ushort` table.
The battery-info cluster runs `ADDR_EC_BIF_DV_BYTE1` = 1032 through
`ADDR_EC_BST_BPV_BYTE2` = 1081 (`0x0439`, `:215`); the next declared address
jumps to `ADDR_EC_BT1CycleCount_BYTE1` = 1190 (`:217`). **1088 is not defined**,
and the whole `windows/` tree has **zero** word-boundary hits for `1088`.
`0x440` appears 114 times, all `[RSP+0x440]`/`[RBP+0x440]` stack spills or
`param+N+0x440` struct fields in `GamingCenter3_Cross.c` and friends.

This matters more than a plain zero, because
`windows/native/ACPIDriver.sys.analysis.md:279-302` records that the Windows
ACPI driver marshals a 16-bit address into the DSDT's general `ECRW` — so
Windows *could* write `0x440`, and no committed caller does.

**Excluded:** the anti-tamper-obscured `GCUService.exe` bodies that do not
decompile (`windows/antitamper/README.md`) — their address constants would be in
the managed decompiles, which are covered — and a fresh `ilspycmd` run.

### 8.4 Linux — nothing

`linux/` has zero hits for `1088` and for `0x440`/`0x0440` as an EC address; the
only related text is a generic `0xFE410000+addr` mention in
`linux/battery-trace/limit-pair-test:4`. **Excluded:** upstream
`uniwill-laptop` itself, which is pinned rather than vendored here.

## 9. What this changes, and what it leaves stale

- **`XDATA_0440` stays `present-untested`.** §5 is a static finding about bytes in
  a table; it is not a readback and not a behavioural test, and CLAUDE.md's
  readback-is-not-acting rule is the whole point.
- **The name `XDATA_0440` stays.** A hypothesis is not a rename.
  `ec/ghidra/xdata-symbols.csv` is generated from `registers.yaml` by
  `ec/tools/gen_xdata_symbols.py`, so leaving the name alone leaves that file
  byte-identical and the `ghidra tooling` gate green with no project rebuild.
- **The reference counts stay 43 / 43 / 0.** The §5 writer is a CODE-table record,
  not a `MOV DPTR,#0x0440` site, so `ec/tools/check_register_counts.py` still
  reconciles against the image. That is not a discrepancy to be explained away —
  it is the mechanism: the address is in CODE, so the direct scan cannot see it.
- **`ghidra-functions.csv` gains no new function.** Two existing comments change:
  `code_table_scatter_to_xdata` (bank1 `0xA530`) now names its seven call sites
  and the three `0x0440` records, and `zero_1510_and_clear_xdata_flag_bits`
  (bank1 `0x8418`) loses its "not decoded here" about the same table. Seeding
  `0x8354`, `0x86EE` or the `0xF326`-`0xF350` stubs as functions would need
  `--mode rebuild-project` and a 7 MB database change that cannot merge alongside
  anything else, so they stay named by address. The other two unexported
  `0xA530` call sites, `0x82C9` and `0x82FD`, are in the same gap.
- **Seven plate comments in `ec/decompiled/` are already stale** for the reason
  `xdata-0400-045f.md` §11 gives. §5's tables add a *new* class of writer for
  bytes already in the YAML: `0x0457` is seeded four different ways by four
  chunks of one table (`0x00`, `0x05`, `0x80`, `0x83`), and `0x043E`, `0x0459`,
  `0x045B`, `0x045C`, `0x045F` and eight others are zeroed or seeded by records
  the direct scan cannot see. `0x0457` is the sharpest case — its only four
  EC-side sites are read-modify-writes in code no export covers (§11 item 4 of
  the page document), and it now has a table-driven writer as well. That is the
  same gap the seven comments have, one level down.
- **Follow-ups this opens**, in rough value order:
  1. the 15 unresolved call sites of §7.6 — the largest remaining hole in the
     writer hunt, and the only one that could still turn up a non-zero writer;
  2. the seven parameterised "zero N bytes at DPTR" helpers of §7.5, whose
     callers are not searched;
  3. seed `0x8354`, `0x86EE` and the `0xF326`-`0xF350` stubs (needs a rebuild),
     which would also establish *when* the `0x0440 = 0` records are walked;
  4. the `0x070F`-`0x071F` ring has a producer and a `0x19EA` hand-off but no
     decoded consumer — if a host drains that ring, it is a second candidate
     writer path for `0x0440`;
  5. run the "many readers, one table-driven writer" test across the other 45
     bytes `xdata-0400-045f.md` §6 lists as having no EC-side site;
  6. the live read of §6, for a human at the machine.
