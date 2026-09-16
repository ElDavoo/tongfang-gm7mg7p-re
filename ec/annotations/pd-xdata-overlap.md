# Does the PD image share the EC's XDATA map? The `0x04A6` collision, decoded

Every per-image count in `registers.yaml` — and every `unknown-not-absent`
grading that came out of `static-refs-audit.md` — rests on one premise: the
`ITE8850-PD` image at file `0x20000` has its own XDATA map, so a `MOV
DPTR,#0x07E2` there is not a reference to the EC register of that number.
The premise has been stated since `lightbar-bat-flow.md` §2 and never
demonstrated; it was inferred from the two programs being separate.

`0x04A6` (`BAT_CYCLE_COUNT`) is the one address that can test it. It is the
only address in the audit split across both images (3 EC-side, 4 PD-side)
and the only one outside `0x0700`-`0x07FF` with any PD sites at all — and it
names a battery quantity in a USB-PD controller's firmware. This file decodes
those seven sites and measures both images' usage across `0x0400`-`0x07FF`
around them.

**Headline verdict.** *The maps look independent as far as this evidence
goes.* The EC image's `0x04A6`/`0x04A7` is a 16-bit counter incremented by
one, together, when a companion byte reaches `0xC8`. The PD image's `0x04A6`
is never read or written as a byte at all: all four sites load it as the
*base* of address arithmetic (`DPTR = 0x04A6 + i×0x60 + j×0x1F`) and the
`movx` lands somewhere else entirely. Those are different objects, and no
PD-image reference to `0x04A7` is found by this method at all. The hedge that
belongs on those sentences:
static code shape is not memory topology. Two programs writing the same
physical byte in incompatible ways would produce exactly these listings; only
running them would tell the difference. What this rules out is the specific
worry the issue raised — that the PD image is a *second writer of the battery
cycle count* — not shared XDATA in general. §6 is the full boundary, §7 the
step that would settle it.

## 1. Reproducing it

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x04A6 0x04A7 --counts-only
0x04A6: 7 direct MOV DPTR site(s)  bank0=1  bank1=2  pd-image=4

0x04A7: 2 direct MOV DPTR site(s)  bank0=1  bank1=1

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 --counts-only
0x07D0: 254 direct MOV DPTR site(s)  pd-image=254
```

The span survey in §5 needs a count for all 1024 addresses in
`0x0400`-`0x07FF`, and `trace_xdata_refs.py` rescans the whole 256 KiB per
address. `ec/tools/xdata_span_survey.py` does the same count for a whole span
in one pass; it imports the image map, the `ITE8850-PD` marker check and the
region lookup from `trace_xdata_refs.py` rather than re-deriving them. It has
to agree with the older tool wherever both are asked, which is this check:

```console
$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x0400 0x07FF --csv \
          > ec/annotations/pd-xdata-span-sites.csv
$ tail -n +2 ec/annotations/pd-xdata-span-sites.csv | wc -l
1024
$ python3 -c "
import csv
rows={r['addr']:r for r in csv.DictReader(open('ec/annotations/pd-xdata-span-sites.csv'))}
print('addr,total,main_ec,pd_image')
for a in ('0x04A6','0x04A7','0x07D0'):
    r=rows[a]; print(','.join([r['addr'],r['total'],r['main_ec'],r['pd_image']]))"
addr,total,main_ec,pd_image
0x04A6,7,3,4
0x04A7,2,2,0
0x07D0,254,0,254
```

7 = 3 + 4 and 254 pd-only, matching the numbers `registers.yaml`,
`static-refs-audit.md` §1 and `ec-0x07d0-sites.md` §1 all quote — so the
tables below cannot silently disagree with them.

Instruction windows come from `ec/tools/disasm8051.py`, whose opcode tables
are pinned by `--self-test`:

```console
$ python3 ec/tools/disasm8051.py --self-test
...
self-test passed: both charge-profile-flow.md windows decode identically
```

Every load-bearing window below is *also* shown as an independent `r2 -a
8051` listing. `ec-0x07d0-sites.md` §1 says radare2 is not installed on the
CI runner; **correction: it is** — `.github/actions/project-setup/action.yml`
installs it, and every `$ r2 …` block in this file was produced by running
it (radare2 5.5.0). r2's trailing `; [0x2000…]` memory-hint column is stripped
from the listings below for width; nothing else is edited. The seek lines come
from `--r2-commands`:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x04A6 --r2-commands \
  | grep '\$ r2'
      $ r2 -a 8051 -e scr.color=0 -q -c 's 0xb16c; pd 10' bank0.bin
      $ r2 -a 8051 -e scr.color=0 -q -c 's 0xd368; pd 10' bank1.bin
      $ r2 -a 8051 -e scr.color=0 -q -c 's 0xdfd0; pd 10' bank1.bin
      $ r2 -a 8051 -e scr.color=0 -q -c 's 0x7421; pd 10' pd.bin
      $ r2 -a 8051 -e scr.color=0 -q -c 's 0x9dec; pd 10' pd.bin
      $ r2 -a 8051 -e scr.color=0 -q -c 's 0xb5d3; pd 10' pd.bin
      $ r2 -a 8051 -e scr.color=0 -q -c 's 0xe9f5; pd 10' pd.bin
```

with the images built the way `trace_xdata_refs.py`'s region table says:

```console
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
1+0 records in
1+0 records out
65536 bytes (66 kB, 64 KiB) copied, 0.000124472 s, 527 MB/s
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
wrote /tmp/bank0.bin: common 0x0000-0x7FFF + bank 0 (file 0x08000) at 0x8000-0xFFFF
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
wrote /tmp/bank1.bin: common 0x0000-0x7FFF + bank 1 (file 0x10000) at 0x8000-0xFFFF
```

## 2. The EC side first, because it is the control

Three sites, and between them they settle what the EC image thinks `0x04A6`
is. The write path, in bank 1:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xd34b; pd 22' /tmp/bank1.bin
            0x0000d34b      900349         mov dptr, #0x0349
            0x0000d34e      e0             movx a, @dptr
            0x0000d34f      c3             clr c
            0x0000d350      94c8           subb a, #0xc8
        ┌─< 0x0000d352      402a           jc 0xd37e
        │   0x0000d354      e4             clr a
        │   0x0000d355      f0             movx @dptr, a
        │   0x0000d356      7900           mov r1, #0x00
        │   0x0000d358      900343         mov dptr, #0x0343
        │   0x0000d35b      e0             movx a, @dptr
        │   0x0000d35c      c3             clr c
        │   0x0000d35d      2401           add a, #0x01
       ┌──< 0x0000d35f      5002           jnc 0xd363
       ││   0x0000d361      7901           mov r1, #0x01
       └──> 0x0000d363      f0             movx @dptr, a
        │   0x0000d364      900528         mov dptr, #0x0528
        │   0x0000d367      f0             movx @dptr, a
        │   0x0000d368      9004a6         mov dptr, #0x04a6
        │   0x0000d36b      f0             movx @dptr, a
        │   0x0000d36c      900344         mov dptr, #0x0344
        │   0x0000d36f      e0             movx a, @dptr
        │   0x0000d370      c3             clr c
```

and its tail, which the linear decoder shows to the `ret`:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x15370 --runtime 0xD370 -n 8
0xd370  c3       clr  c
0xd371  29       add  a,r1
0xd372  900344   mov  dptr,#0x0344
0xd375  f0       movx @dptr,a
0xd376  900529   mov  dptr,#0x0529
0xd379  f0       movx @dptr,a
0xd37a  9004a7   mov  dptr,#0x04a7
0xd37d  f0       movx @dptr,a
```

Read it as: when the byte at `0x0349` reaches `0xC8` (200), zero it, add one
to the 16-bit value held at `0x0343`/`0x0344`, and mirror both halves to
`0x0528`/`0x0529` and to `0x04A6`/`0x04A7` — low half to `0x04A6`, high half
to `0x04A7`, `R1` carrying the carry between them. A 16-bit monotonic counter
that advances once per 200 ticks of something else, published at `0x04A6`.
That is the shape of a battery cycle count, and it is the shape the live read
of 445 cycles already told us about; the decode adds *how* it is maintained,
not *that* it works.

The read site, in bank 0, takes both halves consecutively:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb167; pd 7' /tmp/bank0.bin
            0x0000b167      9004a7         mov dptr, #0x04a7
            0x0000b16a      e0             movx a, @dptr
            0x0000b16b      fc             mov r4, a
            0x0000b16c      9004a6         mov dptr, #0x04a6
            0x0000b16f      e0             movx a, @dptr
            0x0000b170      900a4c         mov dptr, #0x0a4c
            0x0000b173      12bb90         lcall 0xbb90
```

and the third site hands DPTR to a two-byte store helper, so it too is a
16-bit access:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x15FC4 --runtime 0xDFC4 -n 6
0xdfc4  9004a8   mov  dptr,#0x04a8
0xdfc7  12888c   lcall 0x888c
0xdfca  900343   mov  dptr,#0x0343
0xdfcd  128886   lcall 0x8886
0xdfd0  9004a6   mov  dptr,#0x04a6
0xdfd3  12888c   lcall 0x888c

$ r2 -a 8051 -e scr.color=0 -q -c 's 0x888c; pd 6' /tmp/bank1.bin
            0x0000888c      e9             mov a, r1
            0x0000888d      f0             movx @dptr, a
            0x0000888e      a3             inc dptr
            0x0000888f      ea             mov a, r2
            0x00008890      f0             movx @dptr, a
            0x00008891      22             ret
```

`0x888C` writes `R1` to `[DPTR]` and `R2` to `[DPTR+1]` — `0x04A6` and
`0x04A7` as a pair again, in a routine that republishes a run of such pairs
(`0x04A8`, `0x0528`, `0x0536`, … each with the same helper). So: **all three
EC-side sites treat `0x04A6` as the low half of a 16-bit quantity paired with
`0x04A7`.**

## 3. The four PD-image sites

Same pattern in all four, and it is not a byte access. Each is immediately
preceded by `mov b, #0x60` and `mov a, <Rn>`, and immediately followed by a
call into the Keil index helper at `0x10BC`, which is `DPTR += A × B`
(`ec-0x07d0-sites.md` §4 decoded the same helper for `0x07D0`):

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x10bc; pd 7' /tmp/pd.bin
            0x000010bc      a4             mul ab
            0x000010bd      2582           add a, dpl
            0x000010bf      f582           mov dpl, a
            0x000010c1      e5f0           mov a, b
            0x000010c3      3583           addc a, dph
            0x000010c5      f583           mov dph, a
            0x000010c7      22             ret
```

`--converge` framing evidence, for what it is worth (§6): 24/24 preceding
anchors decode onto `0x27421`, `0x29DEC` and `0x2E9F5`; 22/24 onto `0x2B5D3`.

### 3.1 PD runtime `0x7421` (file `0x27421`) — write

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x27419 --runtime 0x7419 -n 12
0x7419  e0       movx a,@dptr
0x741a  ff       mov  r7,a
0x741b  ec       mov  a,r4
0x741c  fe       mov  r6,a
0x741d  75f060   mov  0xf0,#0x60
0x7420  eb       mov  a,r3
0x7421  9004a6   mov  dptr,#0x04a6
0x7424  1290cb   lcall 0x90cb
0x7427  c083     push 0x83
0x7429  c082     push 0x82
0x742b  9007cd   mov  dptr,#0x07cd
0x742e  e0       movx a,@dptr
```

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x741d; pd 8' /tmp/pd.bin
            0x0000741d      75f060         mov b, #0x60
            0x00007420      eb             mov a, r3
            0x00007421      9004a6         mov dptr, #0x04a6
            0x00007424      1290cb         lcall 0x90cb
            0x00007427      c083           push dph
            0x00007429      c082           push dpl
            0x0000742b      9007cd         mov dptr, #0x07cd
            0x0000742e      e0             movx a, @dptr
```

`0x90CB` is `0x10BC` plus one more term, `DPH += 2 × R3`:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x90cb; pd 6' /tmp/pd.bin
            0x000090cb      1210bc         lcall 0x10bc
            0x000090ce      eb             mov a, r3
            0x000090cf      25e0           add a, acc
            0x000090d1      2583           add a, dph
            0x000090d3      f583           mov dph, a
            0x000090d5      22             ret
```

The computed pointer is then saved across an unrelated read of `0x07CD`,
restored, adjusted once more, and written through as a 16-bit field:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x27433 --runtime 0x7433 -n 7
0x7433  129180   lcall 0x9180
0x7436  ee       mov  a,r6
0x7437  f0       movx @dptr,a
0x7438  a3       inc  dptr
0x7439  ef       mov  a,r7
0x743a  f0       movx @dptr,a
0x743b  12911c   lcall 0x911c
```

(`0x9180` is `mov b,#0x1f ; ljmp 0x10bc`, i.e. `DPTR += A × 0x1F`.) So the
byte written is at `0x04A6 + R3×0x60 + 2×R3×0x100 + A×0x1F`, which equals
`0x04A6` only when every index is zero. **`0x04A6` here is a base, not a
variable.**

### 3.2 PD runtime `0x9DEC` (file `0x29DEC`) — write

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x29DE3 --runtime 0x9DE3 -n 12
0x9de3  e0       movx a,@dptr
0x9de4  fa       mov  r2,a
0x9de5  a3       inc  dptr
0x9de6  e0       movx a,@dptr
0x9de7  fb       mov  r3,a
0x9de8  75f060   mov  0xf0,#0x60
0x9deb  ee       mov  a,r6
0x9dec  9004a6   mov  dptr,#0x04a6
0x9def  1210bc   lcall 0x10bc
0x9df2  ee       mov  a,r6
0x9df3  12998f   lcall 0x998f
0x9df6  ed       mov  a,r5
0x9df7  129a99   lcall 0x9a99
```

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9de8; pd 6' /tmp/pd.bin
            0x00009de8      75f060         mov b, #0x60
            0x00009deb      ee             mov a, r6
            0x00009dec      9004a6         mov dptr, #0x04a6
            0x00009def      1210bc         lcall 0x10bc
            0x00009df2      ee             mov a, r6
            0x00009df3      12998f         lcall 0x998f
```

Three index terms stacked (`×0x60`, `DPH += 2×A`, `×0x1F`), then the 16-bit
pair fetched at `0x9DE3` is stored at the result:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x29DFA --runtime 0x9DFA -n 5
0x9dfa  ea       mov  a,r2
0x9dfb  f0       movx @dptr,a
0x9dfc  a3       inc  dptr
0x9dfd  eb       mov  a,r3
0x9dfe  129a71   lcall 0x9a71
```

### 3.3 PD runtime `0xB5D3` (file `0x2B5D3`) — read

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb5d0; pd 8' /tmp/pd.bin
            0x0000b5d0      75f060         mov b, #0x60
            0x0000b5d3      9004a6         mov dptr, #0x04a6
            0x0000b5d6      12998b         lcall 0x998b
            0x0000b5d9      c083           push dph
            0x0000b5db      c082           push dpl
            0x0000b5dd      900817         mov dptr, #0x0817
            0x0000b5e0      e0             movx a, @dptr
            0x0000b5e1      d082           pop dpl
```

`0x998B` is `0x90CB`'s twin, `0x10BC` followed by `DPH += 2 × R7`. The
pointer survives the detour through `0x0817` and is read as a pair:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2B5E5 --runtime 0xB5E5 -n 6
0xb5e5  129a99   lcall 0x9a99
0xb5e8  e0       movx a,@dptr
0xb5e9  fe       mov  r6,a
0xb5ea  a3       inc  dptr
0xb5eb  e0       movx a,@dptr
0xb5ec  ff       mov  r7,a
```

### 3.4 PD runtime `0xE9F5` (file `0x2E9F5`) — read

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xe9f1; pd 8' /tmp/pd.bin
            0x0000e9f1      75f060         mov b, #0x60
            0x0000e9f4      ef             mov a, r7
            0x0000e9f5      9004a6         mov dptr, #0x04a6
            0x0000e9f8      12998b         lcall 0x998b
            0x0000e9fb      129a98         lcall 0x9a98
            0x0000e9fe      e0             movx a, @dptr
            0x0000e9ff      fe             mov r6, a
            0x0000ea00      a3             inc dptr
```

Same three terms, then a 16-bit read. Net for §3: **2 writes, 2 reads, all
four of them 16-bit accesses to `base + i×0x60 + j×0x1F` and none of them an
access to `0x04A6` itself.** All four end in `movx`, never `movc`, so none is
a CODE pointer — see §5 for why that had to be checked.

## 4. Does the PD side look like a battery cycle count?

The three tests the issue named, answered against the bytes above:

| test | PD-side answer |
|---|---|
| 16-bit pair with `0x04A7`? | **No.** The PD image references `0x04A7` zero times (`--counts-only`, §1), and the 16-bit accesses it does make are at `0x04A6 + index`, whose second byte is `0x04A6 + index + 1`. |
| monotonic-counter semantics? | **No.** No site increments anything at `0x04A6`; no `inc a`/`add a,#0x01` appears between the load and the `movx`. Compare `0x07D0`, where two of 254 sites *do* increment in place (`ec-0x07d0-sites.md` §4). |
| compared against a threshold? | **No.** No `cjne`/`subb` against a constant at any of the four sites. The only constants in sight are the strides `0x60` and `0x1F`. |

What shape it does have: the base of a strided record structure, addressed
two or three index terms deep. Naming what the records hold would be a guess
and is not made here — `ec-0x07d0-sites.md` §4 stopped at the same line for
the `0x0408`-based array, and this is the same unanswered question.

`pd-index-geometry.md` takes the *arithmetic* further without crossing that
line: it decodes all eleven helper routines named in §3 and §5.2, and finds
that where a site's two index terms both name an identified register it is the
same register, so the effective stride is `0x60 + 0x200` = `0x260` rather than
the `0x60` quoted above. It still names nothing and still states no record
count — §4's verdict here stands as written.

## 5. The structural question

### 5.1 Both images over `0x0400`-`0x07FF`

```console
$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x0400 0x07FF --page 0x40
0x0400-0x07FF: 1024 addresses
  main EC :   2173 sites over 430 addresses
  PD image:   1324 sites over 114 addresses
  both    : 40 address(es) with sites in each image

  block              main EC       PD
  0x0400-0x043F        132       98
  0x0440-0x047F        342        6
  0x0480-0x04BF        407       47
  0x04C0-0x04FF         35        0
  0x0500-0x053F        141        0
  0x0540-0x057F        112        0
  0x0580-0x05BF          3        0
  0x05C0-0x05FF         23        0
  0x0600-0x063F        112        0
  0x0640-0x067F         37       51
  0x0680-0x06BF         93       19
  0x06C0-0x06FF        246        0
  0x0700-0x073F        120        0
  0x0740-0x077F        186        0
  0x0780-0x07BF        103       12
  0x07C0-0x07FF         81     1091
```

Two things fall out. First, **`0x04A6` is not the only collision** — across
the span, 40 addresses have sites in both images, and the audit only met one
because `registers.yaml` holds 29 addresses, not 1024. Second, 40 is about
what chance predicts: the PD image touches 114 of the 1024 addresses and the
EC image 430, so independent choices would collide on roughly
114 × 430 / 1024 ≈ 48. Observing 40 is on the low side of that, i.e. the PD
image's addresses are, if anything, slightly *less* concentrated on the EC's
than coincidence would give. This is a weak test — the two images' address
choices are not independent draws, both being Keil allocations biased toward
low XDATA — and it is offered as consistency, not proof.

### 5.2 The PD image's own block structure

```console
$ python3 -c "
import csv
rows=list(csv.DictReader(open('ec/annotations/pd-xdata-span-sites.csv')))
pd=[int(r['addr'],16) for r in rows if int(r['pd_image'])]
def runs(xs):
    out=[];s=p=xs[0]
    for x in xs[1:]:
        if x==p+1: p=x
        else: out.append((s,p)); s=p=x
    out.append((s,p)); return out
print('  '.join(f'0x{a:04X}-0x{b:04X}({b-a+1})' for a,b in runs(pd)))"
0x0400-0x0400(1)  0x0404-0x0404(1)  0x0408-0x0408(1)  0x040C-0x040C(1)  0x0410-0x0410(1)  0x0418-0x0418(1)  0x041C-0x041C(1)  0x0420-0x0420(1)  0x0424-0x0424(1)  0x0426-0x0426(1)  0x0428-0x042A(3)  0x042C-0x042C(1)  0x042F-0x042F(1)  0x0432-0x0434(3)  0x0437-0x0437(1)  0x043A-0x043B(2)  0x0457-0x0458(2)  0x0474-0x0475(2)  0x0491-0x0491(1)  0x0495-0x0495(1)  0x0499-0x0499(1)  0x049D-0x049D(1)  0x049F-0x049F(1)  0x04A1-0x04A6(6)  0x04A8-0x04A8(1)  0x0660-0x0661(2)  0x0665-0x0667(3)  0x066B-0x0670(6)  0x0672-0x0672(1)  0x0675-0x0675(1)  0x0677-0x067B(5)  0x0694-0x0694(1)  0x0699-0x069B(3)  0x07A1-0x07A1(1)  0x07A3-0x07A3(1)  0x07BF-0x07C2(4)  0x07C4-0x07C4(1)  0x07C9-0x07EA(34)  0x07EC-0x07EE(3)  0x07F3-0x07F3(1)  0x07F5-0x07FC(8)  0x07FE-0x07FF(2)
```

The PD image's low-address usage is its own regular structure, not a scatter
over the EC's registers: `0x0400`, `0x0404`, `0x0408`, `0x040C`, `0x0410`,
`0x0418`, `0x041C`, `0x0420`, `0x0424` — a stride-4 run of bases — then
`0x0491`, `0x0495`, `0x0499`, `0x049D` on the same stride, then the
contiguous `0x04A1`-`0x04A6`. And `0x04A6` sits at the top of that run
rather than standing alone: every PD site for `0x04A1` through `0x04A5` has
the same shape as the four in §3, DPTR handed straight to an index helper
rather than dereferenced.

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x04A3 2>/dev/null \
  | grep -E 'pd-image|DPTR handed'
0x04A3: 6 direct MOV DPTR site(s)  bank0=1  pd-image=5
  file 0x2917A  pd-image  runtime 0x917A  [separate ITE8850-PD 8051 image; dd bs=64k skip=2]
    DPTR handed to ljmp 0x10bc -- direction unresolved here
  file 0x29DA6  pd-image  runtime 0x9DA6  [separate ITE8850-PD 8051 image; dd bs=64k skip=2]
    DPTR handed to lcall 0x998b -- direction unresolved here
  file 0x29E52  pd-image  runtime 0x9E52  [separate ITE8850-PD 8051 image; dd bs=64k skip=2]
    DPTR handed to lcall 0x9a3f -- direction unresolved here
  file 0x2EDB7  pd-image  runtime 0xEDB7  [separate ITE8850-PD 8051 image; dd bs=64k skip=2]
    DPTR handed to lcall 0x9a1b -- direction unresolved here
  file 0x2F22E  pd-image  runtime 0xF22E  [separate ITE8850-PD 8051 image; dd bs=64k skip=2]
    DPTR handed to lcall 0x9987 -- direction unresolved here
```

So `0x04A1`-`0x04A6` reads as a set of field offsets into one strided
structure, of which `0x04A6` is simply the last — a coherent object in the PD
image's own allocation that happens to end on the EC's counter byte.

### 5.3 The argument that would have to hold if the map *were* shared

Take `ec-0x07d0-sites.md` §4's reading of the `0x0408`-based array of
`0x60`-byte records at face value. Record 0 then spans `0x0408`-`0x0467`,
which contains `0x043E` (`CPU_TEMP`) and `0x044F` (`GPU_TEMP`) — two EC
registers confirmed working against `coretemp` and `nvidia-smi`
(`static-refs-audit.md` §3). A shared map would mean the PD firmware indexes
records straight through live temperature registers. That is an argument
against sharing, and it is worth exactly as much as the reading it rests on:
the `0x0408` base and `0x60` stride are themselves static inferences, and
nothing here proves the PD image in this dump is the one that executes.

### 5.4 CODE pointers

`MOV DPTR,#imm16` builds CODE pointers as well as XDATA ones — the caveat
`ec-0x07d0-sites.md` §5 raised after finding CODE `0x07D0` inside a string
table. Checked here two ways, and neither turns up a CODE pointer: all four
sites resolve to a `movx` (§3), and CODE `0x04A6` in the PD image is
mid-instruction inside ordinary code, not a string:

```console
$ xxd -s 0x20490 -l 32 ec/firmware/GMxMGxx_11.800
00020490: 7b01 7a08 793e 7f14 12c3 a522 7b01 7a08  {.z.y>....."{.z.
000204a0: 793d 7dc6 7f12 12ce 3622 7b01 7a08 793d  y=}.....6"{.z.y=
```

## 6. What this does not establish

- **Nothing observed on hardware.** No register was read, written or read
  back; nothing ran on the machine. This is static analysis of
  `ec/firmware/GMxMGxx_11.800` and that is all it is.
- **Not proof that the maps are separate.** Code shape is not memory
  topology. If the two programs did address the same physical XDATA, these
  same listings would be what a *conflict* looks like — one program keeping a
  counter where the other bases an array. The decode rules out the PD image
  being a second *maintainer* of a battery cycle count; it does not rule out
  a shared or partially mirrored region.
- **Every zero here means "not found by this method".** `0x04A7`'s zero PD
  sites, the empty blocks in §5.1, and "no threshold comparison at any site"
  all inherit the indirect-addressing blind spot that forced the `0x07B9`
  retraction (`../../docs/findings.md` §4c): a pointer built in registers, or
  a base+offset access reaching `0x04A6` from some other base, is invisible
  to a `90 hi lo` scan. Note that this cuts *against* the verdict as much as
  for it — the PD image could reach `0x04A7` indirectly and this file would
  not see it.
- **No control-flow recovery.** `disasm8051.py` stops at the first branch and
  r2 was used for listings, not analysis. What calls the four PD routines,
  what the index registers hold when they are called, and what the records
  contain are all untraced (`../README.md`, "toolchain proven, not
  attempted"), as is `#26`'s wider characterisation of the PD image.
  `pd-index-geometry.md` §4 bounds the first of those three — each of the four
  routines gets a containing entry and one anchored caller — by a byte scan
  with framing evidence, not by a call graph. It leaves the other two exactly
  where this bullet does: no caller found there loads a literal into any of the
  index registers, so no index range and no record count follows.
- **`BAT_CYCLE_COUNT` is untouched either way.** Its `confirmed-working`
  status comes from a live read of 445 cycles; a static decode can neither
  strengthen nor weaken that, and no status in `registers.yaml` changed in
  this work.
- **The `unknown-not-absent` entries are not re-graded here.** §7 says which
  would need re-reading and under what condition.

## 7. What would settle it, and what follows

The runtime step, and it needs the physical machine — **not done here, and
not doable from this pipeline** (`../../CLAUDE.md`, "Cloud agents cannot
reach the hardware"). Read EC RAM `0x04A6`/`0x04A7` over a period in which
the PD controller is active (plug and unplug a USB-C PD source, renegotiate)
and see whether the reported cycle count is disturbed. If the maps are truly
separate, PD activity cannot move it; if it moves, they overlap and this
file's verdict is wrong. A second, cheaper variant for whoever has the
machine: check whether the value at `0x04A6` ever changes other than by +1
at long intervals.

Until then, what this file supports for the audit that depends on the
premise:

- The `unknown-not-absent` gradings (`0x07B9`, `0x07D0`, `0x07E2`-`0x07E5`)
  and `0x07CC`'s `present-untested` **stand as they are**. They were never
  claims about the PD image's behaviour, and nothing found here moves them.
- If the runtime test above ever shows overlap, those six entries plus
  `static-refs-audit.md` §2's "PD refs are not EC refs" framing are what has
  to be re-read, in that order — the `0x07C0`-`0x07FF` block is where the PD
  image's usage is densest (§5.1, 1091 of its 1324 sites in the span), so a
  shared region there would be the expensive case.
